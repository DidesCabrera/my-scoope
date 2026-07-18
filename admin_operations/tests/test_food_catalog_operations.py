from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from admin_operations.services import build_food_catalog_inventory_vm, build_food_catalog_operations_vm
from food_catalog.models import CatalogCurationCandidate, CatalogFood, CatalogFoodAlias, CatalogFoodPortion, CatalogFoodSource
from notas.domain.models import Food
from admin_operations.models import AdminOperationAuditEvent


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

    def test_publication_and_snapshot_are_separate_audited_actions(self):
        catalog_food = _create_catalog_food(
            status=CatalogFood.STATUS_REVIEWED,
            display_name="Avena publicable",
            canonical_name="avena-publicable",
            data_quality_score=90,
        )
        CatalogFoodSource.objects.create(
            catalog_food=catalog_food,
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="Evidence",
            source_food_id="E-1",
            license_status=CatalogFoodSource.LICENSE_ALLOWED,
        )
        CatalogFoodPortion.objects.create(
            catalog_food=catalog_food,
            label="100 g",
            grams=Decimal("100"),
            is_default=True,
        )
        self.client.force_login(self.staff)

        publish_response = self.client.post(
            reverse("admin_operations_food_catalog_food_action", args=[catalog_food.pk]),
            {"action": "published", "reason": "Evidence and macros reviewed."},
            follow=True,
        )
        catalog_food.refresh_from_db()
        self.assertEqual(publish_response.status_code, 200)
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_PUBLISHED)
        self.assertEqual(Food.objects.count(), 0)

        snapshot_response = self.client.post(
            reverse("admin_operations_food_catalog_food_snapshot", args=[catalog_food.pk]),
            {"reason": "Make reviewed food operational."},
            follow=True,
        )
        operational = Food.objects.get()
        self.assertEqual(snapshot_response.status_code, 200)
        self.assertEqual(operational.catalog_food_id, catalog_food.pk)
        self.assertEqual(
            AdminOperationAuditEvent.objects.filter(
                action__in=[
                    "food_catalog.catalog_food.published",
                    "food_catalog.catalog_food.snapshot_create",
                ]
            ).count(),
            2,
        )

    def test_snapshot_rejects_unpublished_catalog_food(self):
        catalog_food = _create_catalog_food(status=CatalogFood.STATUS_REVIEWED)
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("admin_operations_food_catalog_food_snapshot", args=[catalog_food.pk]),
            {"reason": "Attempt premature snapshot."},
            follow=True,
        )
        self.assertContains(response, "Only published CatalogFood")
        self.assertEqual(Food.objects.count(), 0)

    def test_inventory_page_requires_staff(self):
        response = self.client.get(reverse("admin_operations_food_catalog_inventory"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

        self.client.force_login(self.member)
        response = self.client.get(reverse("admin_operations_food_catalog_inventory"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_inventory_vm_exposes_catalog_coverage_and_quality_gaps(self):
        _create_catalog_food(
            status=CatalogFood.STATUS_PUBLISHED,
            display_name="Espinaca cocida",
            food_group="vegetables",
            food_form=CatalogFood.FOOD_FORM_INGREDIENT,
            preparation_state=CatalogFood.PREPARATION_COOKED,
            solver_enabled=True,
            data_quality_score=90,
            fiber_g_per_100g=Decimal("2.400"),
        )
        _create_catalog_food(
            status=CatalogFood.STATUS_REVIEWED,
            display_name="Pechuga de pollo",
            food_group="protein",
            data_quality_score=70,
        )

        vm = build_food_catalog_inventory_vm()

        metrics = {metric.label: metric.value for metric in vm.metrics}
        gaps = {metric.label: metric.value for metric in vm.gap_metrics}
        categories = {item.label: item.total for item in vm.category_coverage}
        self.assertEqual(metrics["Alimentos persistidos"], "2")
        self.assertEqual(metrics["Publicados"], "1")
        self.assertEqual(metrics["Habilitados para solver"], "1")
        self.assertEqual(metrics["Calidad promedio"], "80.0/100")
        self.assertEqual(categories["Verduras"], "1")
        self.assertEqual(categories["Proteínas"], "1")
        self.assertEqual(gaps["Sin evidencia asociada"], "2")
        self.assertEqual(gaps["Nutrición extendida incompleta"], "2")

    def test_inventory_page_renders_all_catalog_food_fields_and_relations(self):
        food = _create_catalog_food(
            status=CatalogFood.STATUS_PUBLISHED,
            display_name="Avena integral",
            brand_name="Marca prueba",
            is_branded=True,
            country="CL",
            food_group="cereals",
            food_subgroup="whole_grains",
            food_form=CatalogFood.FOOD_FORM_INGREDIENT,
            preparation_state=CatalogFood.PREPARATION_DRY,
            functional_roles=["primary_carb"],
            meal_affinities=["breakfast"],
            dietary_tags=["vegetarian"],
            allergens=["gluten"],
            solver_enabled=True,
            solver_min_portion_g=Decimal("20"),
            solver_max_portion_g=Decimal("100"),
            solver_portion_step_g=Decimal("5"),
            calories_kcal_per_100g=Decimal("380"),
            fiber_g_per_100g=Decimal("10"),
            sugar_g_per_100g=Decimal("1"),
            saturated_fat_g_per_100g=Decimal("1.2"),
            sodium_mg_per_100g=Decimal("5"),
            confidence_score=Decimal("92"),
        )
        CatalogFoodSource.objects.create(
            catalog_food=food,
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="Dataset curado",
            source_food_id="FOOD-001",
            license_status=CatalogFoodSource.LICENSE_ALLOWED,
        )
        CatalogFoodPortion.objects.create(catalog_food=food, label="1 taza", grams=Decimal("80"), is_default=True)
        CatalogFoodAlias.objects.create(catalog_food=food, name="Oatmeal", alias_type=CatalogFoodAlias.ALIAS_SEARCH)
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_operations_food_catalog_inventory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inventario y calidad del Food Catalog")
        self.assertContains(response, "Avena integral")
        self.assertContains(response, "Marca prueba")
        self.assertContains(response, "grupo: cereals")
        self.assertContains(response, "subgrupo: whole_grains")
        self.assertContains(response, "Dataset curado")
        self.assertContains(response, "ID FOOD-001")
        self.assertContains(response, "roles: primary_carb")
        self.assertContains(response, "rango: 20 g – 100 g")
        self.assertContains(response, "fibra 10 g")
        self.assertContains(response, "1 taza: 80 g (default)")
        self.assertContains(response, "Oatmeal (search, es)")

    def test_inventory_filters_are_combined(self):
        _create_catalog_food(
            status=CatalogFood.STATUS_PUBLISHED,
            display_name="Espinaca",
            food_group="vegetables",
            source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
            solver_enabled=True,
        )
        _create_catalog_food(
            status=CatalogFood.STATUS_REVIEWED,
            display_name="Arroz",
            food_group="cereals",
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            solver_enabled=False,
        )
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("admin_operations_food_catalog_inventory"),
            {
                "q": "espinaca",
                "status": CatalogFood.STATUS_PUBLISHED,
                "source": CatalogFood.SOURCE_NATURAL_VERIFIED,
                "group": "vegetables",
                "solver": "enabled",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Espinaca")
        self.assertNotContains(response, "Arroz")
        self.assertContains(response, "1 resultados")

    def test_inventory_is_paginated_without_hiding_total(self):
        for index in range(51):
            _create_catalog_food(
                status=CatalogFood.STATUS_REVIEWED,
                display_name=f"Food {index:02d}",
            )

        vm = build_food_catalog_inventory_vm(page=2)

        self.assertEqual(vm.filtered_total, "51")
        self.assertEqual(vm.page_label, "Página 2 de 2")
        self.assertEqual(len(vm.foods), 1)
        self.assertTrue(vm.previous_url)
        self.assertFalse(vm.next_url)


def _create_catalog_food(*, status: str, display_name: str = "Avena", **overrides) -> CatalogFood:
    values = {
        "display_name": display_name,
        "canonical_name": display_name.lower().replace(" ", "-"),
        "protein_g_per_100g": Decimal("13.000"),
        "carbs_g_per_100g": Decimal("60.000"),
        "fat_g_per_100g": Decimal("7.000"),
        "status": status,
        "source_type": CatalogFood.SOURCE_ADMIN_IMPORT,
        "data_quality_score": 80,
    }
    values.update(overrides)
    return CatalogFood.objects.create(**values)
