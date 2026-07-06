from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from admin_analytics.selectors.nutrition_solver import get_nutrition_solver_metrics
from food_catalog.models import CatalogFood
from notas.domain.model_modules.proposals import NutritionProposal
from notas.domain.models import Food


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminAnalyticsNutritionSolverMetricsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="password123",
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username="member@example.com",
            email="member@example.com",
            password="password123",
        )

    def _create_solver_data(self):
        NutritionProposal.objects.create(
            created_by=self.member,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            source=NutritionProposal.SOURCE_AI,
            title="Solver proposal",
            validation_summary={
                "payload_validation": {
                    "is_valid": True,
                    "intent": "create_dailyplan",
                },
                "nutrition_solver": {
                    "version": "solver_meal_proposal_v1",
                    "status": "acceptable",
                    "candidate_preview": {
                        "count": 6,
                        "limit": 12,
                    },
                    "result": {
                        "status": "acceptable",
                        "score": 12.3456,
                        "diagnostics": {
                            "score": 12.3456,
                            "issue_counts": {
                                "warnings": 1,
                                "errors": 0,
                            },
                            "metadata": {
                                "iterations": 80,
                            },
                            "assessment": {
                                "reason_code": "within_acceptable_tolerance",
                                "worst_macro": "protein",
                                "worst_deviation_percent": 11.5,
                            },
                        },
                    },
                },
                "engine_validation": {
                    "kind": "strict_dailyplan_nutrition_validation",
                    "status": "warning",
                    "is_valid": True,
                    "has_warnings": True,
                    "has_errors": False,
                    "issues": [
                        {
                            "severity": "warning",
                            "code": "protein_outside_warning_tolerance",
                            "metric": "protein",
                        }
                    ],
                },
                "target_comparison": {
                    "protein": {
                        "diff_percent": -11.5,
                    },
                    "carbs": {
                        "diff_percent": 3.0,
                    },
                },
            },
        )
        NutritionProposal.objects.create(
            created_by=self.member,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            source=NutritionProposal.SOURCE_AI,
            title="Invalid validation proposal",
            validation_summary={
                "engine_validation": {
                    "status": "error",
                    "is_valid": False,
                    "has_warnings": True,
                    "has_errors": True,
                    "issues": [
                        {
                            "severity": "error",
                            "code": "kcal_outside_error_tolerance",
                            "metric": "kcal",
                        }
                    ],
                }
            },
        )
        Food.objects.create(
            name="Avena operacional",
            protein=13,
            carbs=60,
            fat=7,
            created_by=self.member,
            solver_enabled=True,
            is_verified=True,
            food_group="cereals",
            preparation_state=Food.PREPARATION_DRY,
        )
        Food.objects.create(
            name="Food sin grupo",
            protein=5,
            carbs=10,
            fat=3,
            created_by=self.member,
            solver_enabled=True,
            is_verified=False,
        )
        CatalogFood.objects.create(
            display_name="Avena catálogo",
            canonical_name="avena catalogo",
            country="CL",
            protein_g_per_100g=Decimal("13.000"),
            carbs_g_per_100g=Decimal("60.000"),
            fat_g_per_100g=Decimal("7.000"),
            calories_kcal_per_100g=Decimal("355.000"),
            status=CatalogFood.STATUS_PUBLISHED,
            source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
            data_quality_score=90,
            solver_enabled=True,
            solver_min_portion_g=Decimal("30.000"),
            solver_max_portion_g=Decimal("120.000"),
            solver_portion_step_g=Decimal("5.000"),
            created_by=self.member,
        )

    def test_selector_returns_solver_quality_validation_and_readiness_metrics(self):
        self._create_solver_data()

        metrics = get_nutrition_solver_metrics()

        self.assertEqual(metrics["proposals"]["total"], 2)
        self.assertEqual(metrics["proposals"]["with_solver_summary_total"], 1)
        self.assertEqual(metrics["proposals"]["with_engine_validation_total"], 2)
        self.assertEqual(metrics["solver_quality"]["avg_candidate_count"], 6)
        self.assertEqual(metrics["solver_quality"]["warning_count"], 1)
        self.assertEqual(metrics["solver_quality"]["status_rows"][0]["status"], "acceptable")
        self.assertEqual(metrics["engine_validation"]["valid_total"], 1)
        self.assertEqual(metrics["engine_validation"]["invalid_total"], 1)
        self.assertEqual(metrics["candidate_readiness"]["operational_solver_enabled"], 2)
        self.assertEqual(metrics["candidate_readiness"]["operational_verified_solver_enabled"], 1)
        self.assertEqual(metrics["candidate_readiness"]["catalog_solver_candidates"], 1)
        self.assertEqual(metrics["candidate_readiness"]["catalog_solver_with_bounds"], 1)
        self.assertIn("portion_solver", metrics["config"])

    def test_nutrition_solver_dashboard_is_staff_only_and_renders_metrics(self):
        self._create_solver_data()

        response = self.client.get(reverse("admin_analytics_nutrition_solver"))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin_analytics_nutrition_solver"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nutrition Solver Analytics")
        self.assertContains(response, "Cobertura de validación")
        self.assertContains(response, "Calidad del resultado solver")
        self.assertContains(response, "Validación estricta")
        self.assertContains(response, "Candidate readiness")
        self.assertContains(response, "within_acceptable_tolerance")
        self.assertContains(response, "protein_outside_warning_tolerance")
