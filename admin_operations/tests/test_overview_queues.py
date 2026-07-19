from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import CreditWallet
from ai_assistant.models import AIUsageEvent
from admin_operations.services import build_operations_overview_vm
from food_catalog.models import CatalogCurationCandidate, CatalogFood
from notas.domain.model_modules.proposals import NutritionProposal


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminOperationsOverviewQueueTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="ops02-staff@example.com",
            email="ops02-staff@example.com",
            password="password123",
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username="ops02-member@example.com",
            email="ops02-member@example.com",
            password="password123",
        )

    def test_overview_vm_counts_detectable_operational_queues(self):
        CatalogCurationCandidate.objects.create(
            provider=CatalogFood.SOURCE_OPEN_FOOD_FACTS,
            display_name="Yogur candidato",
            status=CatalogCurationCandidate.STATUS_QUEUED,
            priority=90,
        )
        CatalogFood.objects.create(
            display_name="Avena master",
            canonical_name="avena-master",
            protein_g_per_100g=Decimal("13.0"),
            carbs_g_per_100g=Decimal("60.0"),
            fat_g_per_100g=Decimal("7.0"),
            status=CatalogFood.STATUS_PENDING_REVIEW,
        )
        AIUsageEvent.objects.create(
            user=self.member,
            period="2026-07",
            action_type="chat_turn",
            status=AIUsageEvent.Status.ERROR,
            error_type="ProviderTimeout",
        )
        NutritionProposal.objects.create(
            created_by=self.member,
            title="Propuesta IA pendiente",
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            source=NutritionProposal.SOURCE_AI,
        )
        CreditWallet.objects.create(
            user=self.member,
            balance=20,
            reserved_balance=5,
            period="2026-07",
        )

        vm = build_operations_overview_vm()

        queue_by_title = {queue.title: queue for queue in vm.queues}
        self.assertEqual(queue_by_title["Food Catalog"].count, "2")
        self.assertEqual(queue_by_title["AI Assistant"].count, "2")
        self.assertEqual(queue_by_title["Accounts & Credits"].count, "1")
        self.assertEqual(queue_by_title["Billing"].count, "0")
        self.assertEqual(vm.metrics[0].label, "Trabajo operacional")
        self.assertEqual(vm.metrics[0].value, "5")
        self.assertTrue(any(warning.title == "Candidatos de alta prioridad" for warning in vm.warnings))
        self.assertTrue(any(warning.title == "Errores IA recientes" for warning in vm.warnings))
        self.assertTrue(any(warning.title == "Wallets con créditos reservados" for warning in vm.warnings))

    def test_overview_page_renders_action_queues_and_empty_state(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_operations_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OPS08 · V1 closure")
        self.assertContains(response, "Colas operacionales detectables")
        self.assertNotContains(response, "admin-operations-hero")
        self.assertContains(response, "Trabajo operacional")
        self.assertContains(response, "Action queues")
        self.assertContains(response, "Warnings operacionales")
        self.assertContains(response, "Sin warnings operacionales activos")
        self.assertContains(response, "OPS03 workflow activo")
        self.assertContains(response, "OPS04 workflow activo")
        self.assertContains(response, "OPS05 workflow activo")
        self.assertContains(response, "OPS06 workflow activo")

    def test_overview_page_renders_live_warning_values(self):
        CatalogCurationCandidate.objects.create(
            provider=CatalogFood.SOURCE_FATSECRET,
            display_name="Cereal externo",
            status=CatalogCurationCandidate.STATUS_QUEUED,
            priority=95,
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_operations_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Candidatos de alta prioridad")
        self.assertContains(response, "1 candidatos · 0 foods por revisar")
        self.assertContains(response, "Abrir curación")
