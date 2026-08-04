from __future__ import annotations

from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from admin_operations.models import AdminOperationAuditEvent
from admin_operations.services import (
    build_catalog_food_detail_vm,
    build_food_catalog_data_coverage_vm,
    build_food_catalog_inventory_vm,
    build_food_catalog_operations_vm,
)
from core.tests.builders import create_staff_user, create_test_user
from food_catalog.models import (
    CatalogCurationCandidate,
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
)
from notas.domain.models import Food


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminOperationsFoodCatalogTests(TestCase):
    def setUp(self):
        self.staff = create_staff_user("ops03-staff@example.com")
        self.member = create_test_user("ops03-member@example.com")

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
        self.assertEqual(metric_by_label["Trabajo pendiente"].value, "2")
        self.assertEqual(metric_by_label["Necesitan evidencia"].value, "0")
        self.assertEqual(metric_by_label["Listos para publicar"].value, "0")
        self.assertEqual(len(vm.candidates), 1)
        self.assertEqual(len(vm.catalog_foods), 1)
        self.assertEqual(len(vm.work_items), 2)

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
        self.assertContains(response, "Curación del Food Catalog")
        self.assertContains(response, "Bandeja curación")
        self.assertNotContains(response, "Del candidato al alimento operativo")
        self.assertContains(response, "Cereal externo")
        self.assertContains(response, "Bandeja de trabajo")
        self.assertContains(response, "Quinoa master")

        dashboard_response = self.client.get(reverse("admin_operations_food_catalog_curation_dashboard"))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, "Dash curación")
        self.assertContains(dashboard_response, "Del candidato al alimento operativo")

    def test_food_catalog_stage_filter_separates_blocked_work(self):
        CatalogCurationCandidate.objects.create(
            provider=CatalogFood.SOURCE_FATSECRET,
            display_name="Sin respaldo",
            status=CatalogCurationCandidate.STATUS_NEEDS_MORE_EVIDENCE,
        )
        _create_catalog_food(status=CatalogFood.STATUS_PENDING_REVIEW, display_name="Listo para revisar")
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_operations_food_catalog"), {"stage": "blocked"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sin respaldo")
        self.assertNotContains(response, "Listo para revisar")
        self.assertContains(response, "Resolver evidencia")

    def test_non_publishable_food_explains_requirements_and_hides_publish_action(self):
        _create_catalog_food(
            status=CatalogFood.STATUS_REVIEWED,
            display_name="Avena incompleta",
            canonical_name="avena-incompleta",
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_operations_food_catalog"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Falta una fuente trazable")
        self.assertContains(response, "Ver ficha")
        self.assertNotContains(response, 'value="published"')

    def test_food_catalog_page_renders_only_valid_food_actions(self):
        _create_catalog_food(status=CatalogFood.STATUS_MANUAL_CANDIDATE, display_name="Manual pendiente")
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_operations_food_catalog"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manual pendiente")
        self.assertContains(response, "Enviar a revisión")
        self.assertNotContains(response, 'value="reviewed">Marcar revisado</button>')

    def test_food_catalog_can_sort_review_queue_by_information_quality(self):
        _create_catalog_food(
            status=CatalogFood.STATUS_PENDING_REVIEW,
            display_name="Calidad alta",
            data_quality_score=95,
        )
        _create_catalog_food(
            status=CatalogFood.STATUS_PENDING_REVIEW,
            display_name="Calidad baja",
            data_quality_score=35,
        )

        vm = build_food_catalog_operations_vm(stage="review", sort="quality_asc")

        self.assertEqual(vm.selected_sort, "quality_asc")
        self.assertEqual([item.title for item in vm.work_items], ["Calidad baja", "Calidad alta"])

    def test_bulk_review_moves_legacy_preparation_foods_and_audits_each_one(self):
        first = _create_catalog_food(
            status=CatalogFood.STATUS_EXTERNAL_CANDIDATE,
            display_name="Importado anterior",
        )
        second = _create_catalog_food(
            status=CatalogFood.STATUS_MANUAL_CANDIDATE,
            display_name="Manual anterior",
        )
        untouched = _create_catalog_food(
            status=CatalogFood.STATUS_PENDING_REVIEW,
            display_name="Ya estaba en revisión",
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("admin_operations_food_catalog_bulk_review"),
            {"reason": "Adoptar revisión directa."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        untouched.refresh_from_db()
        self.assertEqual(first.status, CatalogFood.STATUS_PENDING_REVIEW)
        self.assertEqual(second.status, CatalogFood.STATUS_PENDING_REVIEW)
        self.assertEqual(untouched.status, CatalogFood.STATUS_PENDING_REVIEW)
        self.assertContains(response, "2 alimentos enviados a pendiente de revisión")
        self.assertEqual(
            AdminOperationAuditEvent.objects.filter(
                action="food_catalog.catalog_food.pending_review",
                reason="Adoptar revisión directa.",
            ).count(),
            2,
        )

    def test_catalog_food_detail_is_the_primary_review_surface(self):
        catalog_food = _create_catalog_food(
            status=CatalogFood.STATUS_PENDING_REVIEW,
            display_name="Quinoa detalle",
            canonical_name="quinoa-detalle",
            food_group="cereals",
            preparation_state=CatalogFood.PREPARATION_COOKED,
            food_form=CatalogFood.FOOD_FORM_INGREDIENT,
        )
        CatalogFoodSource.objects.create(
            catalog_food=catalog_food,
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            source_name="Ficha técnica",
            source_food_id="Q-1",
            license_status=CatalogFoodSource.LICENSE_ALLOWED,
        )
        CatalogFoodPortion.objects.create(
            catalog_food=catalog_food,
            label="1 taza",
            grams=Decimal("185"),
            is_default=True,
        )
        CatalogFoodAlias.objects.create(
            catalog_food=catalog_food,
            name="Quinoa cocida",
            normalized_name="quinoa cocida",
            is_primary=True,
        )
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("admin_operations_food_catalog_food", args=[catalog_food.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quinoa detalle")
        self.assertContains(response, "Aprobar revisión")
        self.assertContains(response, "Valores por 100 gramos")
        self.assertContains(response, "Cocido")
        self.assertContains(response, "Ingrediente")
        self.assertContains(response, "Ficha técnica")
        self.assertContains(response, "1 taza")
        self.assertContains(response, "Quinoa cocida")
        self.assertContains(response, 'role="tablist"')
        self.assertContains(response, 'data-detail-tab="nutricion"')
        self.assertContains(response, 'data-detail-panel="nutricion" hidden')
        self.assertContains(response, "admin_operations_food_detail.js")

    def test_catalog_food_links_open_detail_in_a_new_browser_tab(self):
        catalog_food = _create_catalog_food(
            status=CatalogFood.STATUS_PENDING_REVIEW,
            display_name="Ficha en pestaña nueva",
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin_operations_food_catalog"))
        detail_url = reverse("admin_operations_food_catalog_food", args=[catalog_food.pk])

        self.assertContains(response, "Ver ficha")
        self.assertContains(
            response,
            f'href="{detail_url}" target="_blank" rel="noopener noreferrer"',
            count=2,
        )

    def test_catalog_food_detail_explains_publication_blockers(self):
        catalog_food = _create_catalog_food(
            status=CatalogFood.STATUS_REVIEWED,
            display_name="Arroz sin respaldo",
            canonical_name="arroz-sin-respaldo",
        )
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("admin_operations_food_catalog_food", args=[catalog_food.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Completar requisitos")
        self.assertContains(response, "Falta una fuente trazable")
        self.assertContains(response, "Falta una porción")
        self.assertNotContains(response, 'value="published"')

    def test_catalog_food_detail_marks_materialized_food_as_operational(self):
        catalog_food = _create_catalog_food(
            status=CatalogFood.STATUS_PUBLISHED,
            display_name="Avena operativa",
        )
        Food.objects.create(
            name="Avena operativa",
            protein=Decimal("13"),
            carbs=Decimal("60"),
            fat=Decimal("7"),
            catalog_food_id=catalog_food.pk,
            catalog_food_ref=catalog_food.catalog_ref,
            catalog_sync_status=Food.CATALOG_SYNC_SNAPSHOT,
            is_global=True,
        )

        vm = build_catalog_food_detail_vm(catalog_food.pk)

        self.assertTrue(vm.is_operational)
        self.assertEqual(vm.primary_action_kind, "none")
        self.assertIn("Food #", vm.operational_label)

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

    def test_catalog_food_action_allows_empty_optional_comment(self):
        catalog_food = _create_catalog_food(status=CatalogFood.STATUS_PENDING_REVIEW)
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("admin_operations_food_catalog_food_action", args=[catalog_food.pk]),
            {"action": "reviewed", "reason": ""},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        catalog_food.refresh_from_db()
        self.assertEqual(catalog_food.status, CatalogFood.STATUS_REVIEWED)

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

    def test_data_coverage_counts_existing_values_over_total_catalog(self):
        _create_catalog_food(
            status=CatalogFood.STATUS_PENDING_REVIEW,
            display_name="Sin país",
            country="",
            calories_kcal_per_100g=None,
        )
        _create_catalog_food(
            status=CatalogFood.STATUS_PENDING_REVIEW,
            display_name="Con país",
            country="CL",
            calories_kcal_per_100g=Decimal("120"),
        )

        identity_vm = build_food_catalog_data_coverage_vm(section="identity")
        identity_rows = {row.label: row for row in identity_vm.rows}
        nutrition_vm = build_food_catalog_data_coverage_vm(section="nutrition")
        nutrition_rows = {row.label: row for row in nutrition_vm.rows}

        self.assertEqual(identity_vm.total_foods, "2")
        self.assertEqual(identity_rows["País"].existing_total, "1")
        self.assertEqual(identity_rows["País"].share_label, "50.0% del catálogo")
        self.assertEqual(nutrition_rows["Calorías"].existing_total, "1")
        self.assertEqual(nutrition_rows["Calorías"].share_label, "50.0% del catálogo")

    def test_data_coverage_page_uses_catalog_sections_and_new_tab_names(self):
        _create_catalog_food(status=CatalogFood.STATUS_PENDING_REVIEW, display_name="Avena cobertura")
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("admin_operations_food_catalog_data_coverage"),
            {"section": "nutrition"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cobertura de datos del catálogo persistido")
        self.assertContains(response, "Datos existentes")
        self.assertContains(response, "Porcentaje del catálogo")
        self.assertContains(response, "Nutrición / 100 g")
        self.assertContains(response, "Cobertura Alimentos")
        self.assertContains(response, "Catálogo Alimentos")
        self.assertContains(response, "Cobertura datos")

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

    def test_inventory_vm_reconciles_versioned_targets_with_persisted_sources(self):
        food = _create_catalog_food(
            status=CatalogFood.STATUS_VERIFIED,
            display_name="Espinaca cruda",
            source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
        )
        CatalogFoodSource.objects.create(
            catalog_food=food,
            source_type=CatalogFood.SOURCE_NATURAL_VERIFIED,
            source_name="My Scoope Core Natural Foods",
            source_food_id="core-spinach-raw",
        )

        vm = build_food_catalog_inventory_vm()

        funnel = {metric.label: metric.value for metric in vm.target_funnel}
        categories = {item.label: item.total for item in vm.target_category_coverage}
        self.assertEqual(funnel["Definidos"], "282")
        self.assertEqual(funnel["Mapeados a fuente"], "209")
        self.assertEqual(funnel["Importados"], "1")
        self.assertEqual(funnel["Revisados"], "1")
        self.assertEqual(funnel["Publicados"], "0")
        self.assertEqual(categories["Verduras"], "1 / 87")
        self.assertTrue(vm.target_version_label.startswith("gfc.v1 · SHA "))

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

        response = self.client.get(reverse("admin_operations_food_catalog_inventory_master"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inventario y calidad del Food Catalog")
        self.assertContains(response, "Avena integral")
        self.assertContains(response, "Marca prueba")

        classification_response = self.client.get(reverse("admin_operations_food_catalog_inventory_master"), {"section": "classification"})
        self.assertContains(classification_response, "cereals")
        self.assertContains(classification_response, "whole_grains")

        governance_response = self.client.get(reverse("admin_operations_food_catalog_inventory_master"), {"section": "governance"})
        self.assertContains(governance_response, "Dataset curado")
        self.assertContains(governance_response, "FOOD-001")

        functionality_response = self.client.get(reverse("admin_operations_food_catalog_inventory_master"), {"section": "functionality"})
        self.assertContains(functionality_response, "primary_carb")

        solver_response = self.client.get(reverse("admin_operations_food_catalog_inventory_master"), {"section": "solver"})
        self.assertContains(solver_response, "20 g")
        self.assertContains(solver_response, "100 g")

        nutrition_response = self.client.get(reverse("admin_operations_food_catalog_inventory_master"), {"section": "nutrition"})
        self.assertContains(nutrition_response, "10 g")

        relation_response = self.client.get(reverse("admin_operations_food_catalog_inventory_master"), {"section": "relations"})
        self.assertContains(relation_response, "1 taza")
        self.assertContains(relation_response, "Oatmeal")

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
            reverse("admin_operations_food_catalog_inventory_master"),
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
