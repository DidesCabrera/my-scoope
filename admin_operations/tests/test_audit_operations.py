from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import CreditWallet
from admin_operations.models import AdminOperationAuditEvent
from admin_operations.services import build_audit_log_vm
from ai_assistant.models import AIUsageEvent
from core.tests.builders import create_staff_user, create_test_user
from food_catalog.models import CatalogCurationCandidate, CatalogFood
from notas.domain.model_modules.proposals import NutritionProposal


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminOperationsAuditLogTests(TestCase):
    def setUp(self):
        self.staff = create_staff_user("ops06-staff@example.com")
        self.member = create_test_user("ops06-member@example.com")

    def test_audit_log_page_requires_staff(self):
        response = self.client.get(reverse("admin_operations_audit_log"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

        self.client.force_login(self.member)
        response = self.client.get(reverse("admin_operations_audit_log"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_audit_log_page_renders_events(self):
        AdminOperationAuditEvent.objects.create(
            actor=self.staff,
            actor_label=self.staff.email,
            action="food_catalog.candidate.approve",
            target_app="food_catalog",
            target_model="catalogcurationcandidate",
            target_id="10",
            target_label="Avena externa",
            status_before="queued",
            status_after="approved_for_curation",
            reason="Fuente suficiente.",
            metadata={"source_patch": "OPS03"},
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_operations_audit_log"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OPS06 · Audit Log")
        self.assertContains(response, "Audit log operacional")
        self.assertContains(response, "food_catalog.candidate.approve")
        self.assertContains(response, "Fuente suficiente")

    def test_build_audit_log_vm_counts_events(self):
        AdminOperationAuditEvent.objects.create(
            actor=self.staff,
            actor_label=self.staff.email,
            action="accounts.credit.adjustment",
            target_app="accounts",
            target_model="creditwallet",
            target_id="1",
            target_label="wallet",
            status_before="balance=0",
            status_after="balance=10",
            reason="Compensación.",
        )

        vm = build_audit_log_vm()

        metric_by_label = {metric.label: metric for metric in vm.metrics}
        self.assertEqual(metric_by_label["Eventos auditados"].value, "1")
        self.assertEqual(metric_by_label["Accounts"].value, "1")
        self.assertEqual(len(vm.events), 1)
        self.assertEqual(vm.events[0].action, "accounts.credit.adjustment")

    def test_audit_events_are_append_only(self):
        event = AdminOperationAuditEvent.objects.create(
            actor=self.staff,
            actor_label=self.staff.email,
            action="test.action",
            target_app="admin_operations",
            target_model="fixture",
            target_id="1",
            reason="Fixture.",
        )
        event.reason = "Changed"

        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()

    def test_candidate_action_writes_admin_operation_audit(self):
        candidate = CatalogCurationCandidate.objects.create(
            provider=CatalogFood.SOURCE_FATSECRET,
            display_name="Candidato audit",
            status=CatalogCurationCandidate.STATUS_QUEUED,
        )
        self.client.force_login(self.staff)

        self.client.post(
            reverse("admin_operations_food_catalog_candidate_action", args=[candidate.pk]),
            {"action": "approve", "reason": "Fuente suficiente."},
            follow=True,
        )

        audit = AdminOperationAuditEvent.objects.get(target_app="food_catalog", target_id=str(candidate.pk))
        self.assertEqual(audit.action, "food_catalog.candidate.approve")
        self.assertEqual(audit.status_before, CatalogCurationCandidate.STATUS_QUEUED)
        self.assertEqual(audit.status_after, CatalogCurationCandidate.STATUS_APPROVED_FOR_CURATION)
        self.assertEqual(audit.reason, "Fuente suficiente.")

    def test_catalog_food_action_writes_admin_operation_audit(self):
        catalog_food = CatalogFood.objects.create(
            display_name="Avena audit",
            canonical_name="avena-audit",
            protein_g_per_100g=Decimal("13.0"),
            carbs_g_per_100g=Decimal("60.0"),
            fat_g_per_100g=Decimal("7.0"),
            status=CatalogFood.STATUS_PENDING_REVIEW,
        )
        self.client.force_login(self.staff)

        self.client.post(
            reverse("admin_operations_food_catalog_food_action", args=[catalog_food.pk]),
            {"action": "reviewed", "reason": "Macros coherentes."},
            follow=True,
        )

        audit = AdminOperationAuditEvent.objects.get(target_app="food_catalog", target_model="catalogfood")
        self.assertEqual(audit.action, "food_catalog.catalog_food.reviewed")
        self.assertEqual(audit.status_before, CatalogFood.STATUS_PENDING_REVIEW)
        self.assertEqual(audit.status_after, CatalogFood.STATUS_REVIEWED)

    def test_credit_adjustment_writes_admin_operation_audit(self):
        CreditWallet.objects.create(user=self.member, balance=10, reserved_balance=0, period="2026-07")
        self.client.force_login(self.staff)

        self.client.post(
            reverse("admin_operations_account_credit_adjustment", args=[self.member.pk]),
            {"credits_delta": "5", "reason": "Compensación soporte."},
            follow=True,
        )

        audit = AdminOperationAuditEvent.objects.get(action="accounts.credit.adjustment")
        self.assertEqual(audit.target_app, "accounts")
        self.assertIn("balance=10", audit.status_before)
        self.assertIn("balance=15", audit.status_after)
        self.assertEqual(audit.metadata["credits_delta"], 5)

    def test_ai_event_action_writes_admin_operation_audit(self):
        event = AIUsageEvent.objects.create(
            user=self.member,
            period="2026-07",
            action_type="chat_turn",
            status=AIUsageEvent.Status.ERROR,
        )
        self.client.force_login(self.staff)

        self.client.post(
            reverse("admin_operations_ai_event_action", args=[event.pk]),
            {"action": "acknowledge", "reason": "Error aislado."},
            follow=True,
        )

        audit = AdminOperationAuditEvent.objects.get(target_app="ai_assistant", target_model="aiusageevent")
        self.assertEqual(audit.action, "ai_assistant.usage_event.acknowledge")
        self.assertEqual(audit.status_after, "acknowledged")

    def test_ai_quota_action_writes_admin_operation_audit(self):
        wallet = CreditWallet.objects.create(
            user=self.member,
            period="2026-07",
            plan_snapshot_code="starter",
            balance=10,
        )
        self.client.force_login(self.staff)

        self.client.post(
            reverse("admin_operations_ai_quota_action", args=[wallet.pk]),
            {"action": "block", "reason": "Uso anómalo."},
            follow=True,
        )

        audit = AdminOperationAuditEvent.objects.get(target_app="accounts", target_model="creditwallet")
        self.assertEqual(audit.action, "accounts.credit_wallet.freeze")
        self.assertIn("hard_blocked=False", audit.status_before)
        self.assertIn("hard_blocked=True", audit.status_after)

    def test_ai_proposal_action_writes_admin_operation_audit(self):
        proposal = NutritionProposal.objects.create(
            created_by=self.member,
            title="Propuesta audit",
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            source=NutritionProposal.SOURCE_AI,
        )
        self.client.force_login(self.staff)

        self.client.post(
            reverse("admin_operations_ai_proposal_action", args=[proposal.pk]),
            {"action": "reject", "reason": "No respeta restricciones."},
            follow=True,
        )

        audit = AdminOperationAuditEvent.objects.get(target_app="notas", target_model="nutritionproposal")
        self.assertEqual(audit.action, "notas.nutrition_proposal.reject")
        self.assertEqual(audit.status_before, NutritionProposal.STATUS_PENDING_REVIEW)
        self.assertEqual(audit.status_after, NutritionProposal.STATUS_REJECTED)
