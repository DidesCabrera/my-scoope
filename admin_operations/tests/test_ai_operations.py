from __future__ import annotations

from django.test import TestCase, override_settings
from django.urls import reverse

from ai_assistant.models import AICreditLedger, AIUsageEvent, AIUserCreditQuota
from admin_operations.services import build_ai_operations_vm
from core.tests.builders import create_staff_user, create_test_user
from notas.domain.model_modules.proposals import NutritionProposal, NutritionProposalAuditEvent


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminOperationsAITests(TestCase):
    def setUp(self):
        self.staff = create_staff_user("ops05-staff@example.com")
        self.member = create_test_user("ops05-member@example.com")

    def test_ai_operations_page_requires_staff(self):
        response = self.client.get(reverse("admin_operations_ai_assistant"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

        self.client.force_login(self.member)
        response = self.client.get(reverse("admin_operations_ai_assistant"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_ai_operations_vm_counts_events_proposals_and_quotas(self):
        AIUsageEvent.objects.create(
            user=self.member,
            period="2026-07",
            action_type="chat_turn",
            status=AIUsageEvent.Status.ERROR,
            error_type="ProviderTimeout",
        )
        NutritionProposal.objects.create(
            created_by=self.member,
            title="Propuesta AI pendiente",
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            source=NutritionProposal.SOURCE_AI,
        )
        AIUserCreditQuota.objects.create(
            user=self.member,
            period="2026-07",
            plan_code="starter",
            monthly_credit_limit=10,
            daily_credit_limit=3,
            credits_used=10,
        )

        vm = build_ai_operations_vm()

        metric_by_label = {metric.label: metric for metric in vm.metrics}
        self.assertEqual(metric_by_label["Trabajo AI"].value, "3")
        self.assertEqual(metric_by_label["Eventos IA"].value, "1")
        self.assertEqual(metric_by_label["Propuestas"].value, "1")
        self.assertEqual(metric_by_label["Cuotas"].value, "1")

    def test_ai_operations_page_renders_queues(self):
        AIUsageEvent.objects.create(
            user=self.member,
            period="2026-07",
            action_type="nutrition_solver_preview",
            status=AIUsageEvent.Status.BLOCKED,
            error_type="CreditLimit",
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_operations_ai_assistant"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OPS05 · AI Assistant operations")
        self.assertContains(response, "Operaciones de AI Assistant")
        self.assertContains(response, "Errores y bloqueos recientes")
        self.assertContains(response, "nutrition_solver_preview")
        self.assertContains(response, "Reconocer")
        self.assertContains(response, "Escalar")

    def test_ai_event_action_requires_reason(self):
        event = AIUsageEvent.objects.create(
            user=self.member,
            period="2026-07",
            action_type="chat_turn",
            status=AIUsageEvent.Status.ERROR,
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("admin_operations_ai_event_action", args=[event.pk]),
            {"action": "acknowledge", "reason": ""},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        event.refresh_from_db()
        self.assertNotIn("admin_operations", event.metadata)
        self.assertContains(response, "La razón es obligatoria")

    def test_ai_event_action_records_metadata(self):
        event = AIUsageEvent.objects.create(
            user=self.member,
            period="2026-07",
            action_type="chat_turn",
            status=AIUsageEvent.Status.ERROR,
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("admin_operations_ai_event_action", args=[event.pk]),
            {"action": "escalate", "reason": "Error repetido en provider."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        event.refresh_from_db()
        self.assertEqual(event.metadata["admin_operations"]["state"], "escalated")
        self.assertIn("Error repetido", event.metadata["admin_operations"]["reason"])
        self.assertContains(response, "Evento IA escalado")

    def test_quota_operation_toggles_hard_block_and_logs_ledger(self):
        quota = AIUserCreditQuota.objects.create(
            user=self.member,
            period="2026-07",
            plan_code="starter",
            monthly_credit_limit=10,
            daily_credit_limit=3,
            credits_used=8,
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("admin_operations_ai_quota_action", args=[quota.pk]),
            {"action": "block", "reason": "Abuso de herramientas."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        quota.refresh_from_db()
        self.assertTrue(quota.hard_blocked)
        self.assertEqual(AICreditLedger.objects.filter(user=self.member, credits=0).count(), 1)
        self.assertContains(response, "Acceso IA bloqueado")

    def test_ai_proposal_action_rejects_and_writes_audit_event(self):
        proposal = NutritionProposal.objects.create(
            created_by=self.member,
            title="Propuesta a revisar",
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            source=NutritionProposal.SOURCE_MCP,
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("admin_operations_ai_proposal_action", args=[proposal.pk]),
            {"action": "reject", "reason": "No respeta restricciones del usuario."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, NutritionProposal.STATUS_REJECTED)
        self.assertEqual(proposal.reviewed_by, self.staff)
        audit = NutritionProposalAuditEvent.objects.get(proposal=proposal)
        self.assertEqual(audit.action, NutritionProposalAuditEvent.ACTION_REJECTED)
        self.assertEqual(audit.metadata["source"], "OPS05")
        self.assertContains(response, "Propuesta IA rechazada")
