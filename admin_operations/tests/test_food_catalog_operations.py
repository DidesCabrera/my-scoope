from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from admin_operations.services import build_food_catalog_operations_vm
from food_catalog.models import CatalogCurationCandidate, CatalogFood


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminOperationsFoodCatalogTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="ops03-staff@example.com",
            email="ops03-staff@example.com",
            password="password123",
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username="ops03-member@example.com",
            email="ops03-member@example.com",
            password="password123",
        )

    def test_food_catalog_page_requires_staff(self):
        response = self.client.get(reverse("admin_operations_food_catalog"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

        self.client.force_login(self.member)
        response = self.client.get(reverse("admin_operations_food_catalog"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_food_catalog_vm_counts_candidates_and_foods(self):
        CatalogCurationCandidate.objects.create(
            provider=CatalogFood.SOURCE_OPEN_FOOD_FACTS,
            display_name="Yogur externo",
            status=CatalogCurationCandidate.STATUS_QUEUED,
            priority=90,
        )
        _create_catalog_food(status=CatalogFood.STATUS_PENDING_REVIEW, display_name="Avena master")

        vm = build_food_catalog_operations_vm()

        metric_by_label = {metric.label: metric for metric in vm.metrics}
        self.assertEqual(metric_by_label["Trabajo Food Catalog"].value, "2")
        self.assertEqual(metric_by_label["Candidatos"].value, "1")
        self.assertEqual(metric_by_label["Foods por revisar"].value, "1")
        self.assertEqual(len(vm.candidates), 1)
        self.assertEqual(len(vm.catalog_foods), 1)

    def test_food_catalog_page_renders_queues(self):
        CatalogCurationCandidate.objects.create(
            provider=CatalogFood.SOURCE_FATSECRET,
            display_name="Cereal externo",
            status=CatalogCurationCandidate.STATUS_QUEUED,
            priority=95,
        )
        _create_catalog_food(status=CatalogFood.STATUS_PENDING_REVIEW, display_name="Quinoa master")
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_operations_food_catalog"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OPS03 · Food Catalog operations")
        self.assertContains(response, "Curación operacional del Food Catalog")
        self.assertContains(response, "Candidatos de curación")
        self.assertContains(response, "Cereal externo")
        self.assertContains(response, "Alimentos master por revisar")
        self.assertContains(response, "Quinoa master")

    def test_candidate_detail_renders_actions(self):
        candidate = CatalogCurationCandidate.objects.create(
            provider=CatalogFood.SOURCE_FATSECRET,
            display_name="Candidato detalle",
            status=CatalogCurationCandidate.STATUS_QUEUED,
            priority=80,
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_operations_food_catalog_candidate", args=[candidate.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Candidato detalle")
        self.assertContains(response, "Razón obligatoria")
        self.assertContains(response, "Aprobar para curación")
        self.assertContains(response, "Pedir más evidencia")
        self.assertContains(response, "Rechazar")

    def test_candidate_action_requires_reason(self):
        candidate = CatalogCurationCandidate.objects.create(
            provider=CatalogFood.SOURCE_FATSECRET,
            display_name="Sin razón",
            status=CatalogCurationCandidate.STATUS_QUEUED,
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("admin_operations_food_catalog_candidate_action", args=[candidate.pk]),
            {"action": "approve", "reason": ""},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, CatalogCurationCandidate.STATUS_QUEUED)
        self.assertContains(response, "La razón es obligatoria")

    def test_candidate_action_approves_and_records_operational_note(self):
        candidate = CatalogCurationCandidate.objects.create(
            provider=CatalogFood.SOURCE_FATSECRET,
            display_name="Aprobar candidato",
            status=CatalogCurationCandidate.STATUS_QUEUED,
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("admin_operations_food_catalog_candidate_action", args=[candidate.pk]),
            {"action": "approve", "reason": "Fuente suficiente y alta demanda."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, CatalogCurationCandidate.STATUS_APPROVED_FOR_CURATION)
        self.assertEqual(candidate.reviewed_by, self.staff)
        self.assertIsNotNone(candidate.reviewed_at)
        self.assertIn("queued → approved_for_curation", candidate.notes)
        self.assertIn("Fuente suficiente", candidate.notes)
        self.assertContains(response, "Candidate approved for curation")

    def test_catalog_food_action_uses_existing_transition_service(self):
        catalog_food = _create_catalog_food(status=CatalogFood.STATUS_PENDING_REVIEW)
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("admin_operations_food_catalog_food_action", args=[catalog_food.pk]),
            {"action": "reviewed", "reason": "Macros coherentes."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        catalog_food.refresh_from_db()
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_REVIEWED)
        self.assertEqual(catalog_food.reviewed_by, self.staff)
        self.assertIsNotNone(catalog_food.reviewed_at)
        self.assertContains(response, "Marcar revisado")


def _create_catalog_food(*, status: str, display_name: str = "Avena") -> CatalogFood:
    return CatalogFood.objects.create(
        display_name=display_name,
        canonical_name=display_name.lower().replace(" ", "-"),
        protein_g_per_100g=Decimal("13.000"),
        carbs_g_per_100g=Decimal("60.000"),
        fat_g_per_100g=Decimal("7.000"),
        status=status,
        source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        data_quality_score=80,
    )
