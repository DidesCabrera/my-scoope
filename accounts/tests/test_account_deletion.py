from datetime import date

from django.apps import apps
from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import AccountDeletionRecord, AccountSubscription
from accounts.seed_plans import seed_account_plans
from accounts.services.deletion import MODEL_RETENTION_POLICY, POLICY_VERSION
from ai_assistant.models import AIUsageEvent
from billing.models import BillingPayment, BillingProduct, PaymentProvider, ProviderSubscription, TaxDocument
from email_delivery.models import EmailDeliveryAttempt
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
