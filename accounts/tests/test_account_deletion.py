from datetime import date

from django.apps import apps
from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountDeletionRecord, AccountSubscription
from accounts.seed_plans import seed_account_plans
from accounts.services.deletion import MODEL_RETENTION_POLICY, POLICY_VERSION
from ai_assistant.models import AIUsageEvent
from billing.models import BillingPayment, BillingProduct, PaymentProvider, ProviderSubscription, TaxDocument
from email_delivery.models import EmailDeliveryAttempt
from food_catalog.models import (
    CatalogCapabilityDefinition,
    CatalogEnrichmentBatch,
    CatalogEnrichmentChange,
    CatalogFieldProposal,
    CatalogFood,
    CatalogFoodCapability,
)
from notas.domain.models import Food, Profile, WeightLog


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AccountDeletionViewTests(TestCase):
    password = "correct-horse-battery-staple"

    def setUp(self):
        seed_account_plans()
        self.user = get_user_model().objects.create_user(
            username="lifterscoope",
            email="lifter@example.com",
            password=self.password,
            first_name="Felipe",
            last_name="Test",
        )

    def test_account_deletion_requires_authentication(self):
        response = self.client.get(reverse("accounts:delete_account"))

        self.assertEqual(response.status_code, 302)

    def test_profile_exposes_account_deletion_entry_point(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("profile_detail"))

        self.assertContains(response, reverse("accounts:delete_account"))
        self.assertContains(response, "Eliminar cuenta")

    def test_confirmation_and_current_password_are_required(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:delete_account"),
            {"confirmation": "eliminar", "password": "incorrect"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Escribe exactamente &quot;ELIMINAR&quot;')
        self.assertContains(response, "La contraseña no es correcta")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_deletion_erases_personal_data_and_retains_financial_evidence(self):
        original_username = self.user.username
        private_food = Food.objects.create(
            name="Mi mezcla privada",
            protein=30,
            carbs=20,
            fat=10,
            created_by=self.user,
            is_global=False,
        )
        global_food = Food.objects.create(
            name="Alimento compartido",
            protein=10,
            carbs=70,
            fat=2,
            created_by=self.user,
            is_global=True,
        )
        WeightLog.objects.create(user=self.user, date=date(2026, 8, 5), weight_kg=82.5)
        usage = AIUsageEvent.objects.create(
            user=self.user,
            period="2026-08",
            conversation_id="private-conversation",
            turn_id="private-turn",
            action_type="chat",
            usage_payload={"private": "payload"},
            metadata={"private": "metadata"},
        )
        EmailDeliveryAttempt.objects.create(
            category=EmailDeliveryAttempt.CATEGORY_ACCOUNT,
            actor=self.user,
            recipient_email=self.user.email,
            subject="Private subject",
        )
        catalog_food = CatalogFood.objects.create(
            display_name="Lentejas cocidas",
            protein_g_per_100g=9,
            carbs_g_per_100g=20,
            fat_g_per_100g=0.4,
        )
        capability_definition = CatalogCapabilityDefinition.objects.create(
            key="test-portion-policy",
            label="Test portion policy",
            data_type="decimal",
            nature=CatalogCapabilityDefinition.NATURE_OPERATIONAL,
            authority_requirement=CatalogCapabilityDefinition.AUTHORITY_INTERNAL,
        )
        food_capability = CatalogFoodCapability.objects.create(
            catalog_food=catalog_food,
            definition=capability_definition,
            value={"grams": 100},
            assessment_status=CatalogFoodCapability.STATUS_CONFIRMED_VALUE,
            decided_by=self.user,
        )
        enrichment_batch = CatalogEnrichmentBatch.objects.create(
            environment="test",
            reason="Verify account-deletion retention",
            input_sha256="0" * 64,
            requested_by=self.user,
            applied_by=self.user,
        )
        field_proposal = CatalogFieldProposal.objects.create(
            batch=enrichment_batch,
            catalog_food=catalog_food,
            field_name="solver_min_portion_g",
            expected_food_updated_at=catalog_food.updated_at,
            current_value=None,
            proposed_value="50.000",
            nature=CatalogCapabilityDefinition.NATURE_OPERATIONAL,
            provenance=["internal_policy"],
            consumers=["solver"],
            maturity=CatalogCapabilityDefinition.MATURITY_CANDIDATE,
            authority_requirement=CatalogCapabilityDefinition.AUTHORITY_INTERNAL,
            risk_level=CatalogCapabilityDefinition.RISK_MEDIUM,
            assessment_status=CatalogFoodCapability.STATUS_PROPOSED,
            rationale="Representative retained proposal",
            confidence=90,
            reviewed_by=self.user,
        )
        enrichment_change = CatalogEnrichmentChange.objects.create(
            batch=enrichment_batch,
            proposal=field_proposal,
            catalog_food=catalog_food,
            field_name="solver_min_portion_g",
            action=CatalogEnrichmentChange.ACTION_APPLY,
            value_before=None,
            value_after="50.000",
            food_updated_at_before=catalog_food.updated_at,
            food_updated_at_after=timezone.now(),
            actor=self.user,
            reason="Representative retained change",
        )

        account_subscription = AccountSubscription.objects.get(user=self.user)
        product = BillingProduct.objects.create(
            provider=PaymentProvider.MERCADO_PAGO,
            external_product_id="delete-test-product",
            account_plan=account_subscription.plan,
            amount_minor=9990,
        )
        provider_subscription = ProviderSubscription.objects.create(
            user=self.user,
            product=product,
            provider=PaymentProvider.MERCADO_PAGO,
            external_subscription_id="delete-test-subscription",
        )
        payment = BillingPayment.objects.create(
            user=self.user,
            subscription=provider_subscription,
            provider=PaymentProvider.MERCADO_PAGO,
            external_payment_id="delete-test-payment",
            amount_minor=9990,
        )
        tax_document = TaxDocument.objects.create(payment=payment)

        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:delete_account"),
            {"confirmation": "ELIMINAR", "password": self.password},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tu cuenta fue eliminada")

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(self.user.username.startswith("deleted-"))
        self.assertEqual(self.user.email, "")
        self.assertEqual(self.user.first_name, "")
        self.assertFalse(self.user.has_usable_password())
        self.assertFalse(Profile.objects.filter(user=self.user).exists())
        self.assertFalse(WeightLog.objects.filter(user=self.user).exists())
        self.assertFalse(Food.objects.filter(pk=private_food.pk).exists())

        global_food.refresh_from_db()
        self.assertIsNone(global_food.created_by_id)
        usage.refresh_from_db()
        self.assertIsNone(usage.user_id)
        self.assertEqual(usage.conversation_id, "")
        self.assertEqual(usage.usage_payload, {})
        food_capability.refresh_from_db()
        enrichment_batch.refresh_from_db()
        field_proposal.refresh_from_db()
        enrichment_change.refresh_from_db()
        self.assertIsNone(food_capability.decided_by_id)
        self.assertIsNone(enrichment_batch.requested_by_id)
        self.assertIsNone(enrichment_batch.applied_by_id)
        self.assertIsNone(field_proposal.reviewed_by_id)
        self.assertIsNone(enrichment_change.actor_id)

        self.assertTrue(ProviderSubscription.objects.filter(pk=provider_subscription.pk, user=self.user).exists())
        self.assertTrue(BillingPayment.objects.filter(pk=payment.pk, user=self.user).exists())
        self.assertTrue(TaxDocument.objects.filter(pk=tax_document.pk).exists())
        self.assertFalse(AccountSubscription.objects.filter(user=self.user).exists())

        record = AccountDeletionRecord.objects.get()
        self.assertEqual(record.policy_version, POLICY_VERSION)
        self.assertEqual(record.retained_counts["billing.BillingPayment"], 1)
        self.assertNotContains(self.client.get(reverse("accounts:delete_account"), follow=True), "Mi mezcla privada")
        self.assertIsNone(authenticate(username=original_username, password=self.password))


class AccountDeletionPolicyCoverageTests(TestCase):
    def test_every_concrete_installed_model_has_an_explicit_retention_policy(self):
        installed_labels = {
            model._meta.label
            for model in apps.get_models()
            if not model._meta.proxy
        }

        self.assertEqual(set(MODEL_RETENTION_POLICY), installed_labels)
