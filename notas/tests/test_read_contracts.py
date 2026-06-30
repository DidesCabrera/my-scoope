import json
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.queries.dailyplan_queries import (
    get_dailyplan_detail,
    list_available_dailyplans,
    list_user_dailyplans,
    search_dailyplans,
)
from notas.application.queries.food_queries import (
    get_food_detail,
    list_available_foods,
    list_user_foods,
    search_foods,
)
from notas.application.queries.meal_queries import (
    get_meal_detail,
    list_available_meals,
    list_user_meals,
    search_meals,
)
from notas.application.queries.nutrition_context_queries import (
    get_user_nutrition_context,
)
from notas.application.queries.validation_queries import (
    compare_dailyplan_to_targets,
)
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    Meal,
    MealFood,
    WeightLog,
    NutritionProposal,
)

from notas.application.queries.proposal_queries import (
    get_proposal_detail,
    list_dailyplan_proposals,
    list_user_proposals,
    search_proposals,
)


def assert_json_serializable(test_case, value):
    try:
        json.dumps(value)
    except TypeError as exc:
        test_case.fail(f"Value is not JSON serializable: {exc}")


class ReadContractTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@example.com",
            password="pass123",
        )

        WeightLog.objects.create(
            user=self.user,
            date=date.today(),
            weight_kg=100,
        )

        self.food = Food.objects.create(
            name="Arroz",
            protein=2.7,
            carbs=28,
            fat=0.3,
            created_by=self.user,
        )

        self.meal = Meal.objects.create(
            name="Almuerzo Base",
            created_by=self.user,
            is_public=False,
            is_draft=False,
        )

        self.meal_food = MealFood.objects.create(
            meal=self.meal,
            food=self.food,
            quantity=100,
            order=1,
        )

        self.dailyplan = DailyPlan.objects.create(
            name="Día Entrenamiento",
            created_by=self.user,
            is_public=False,
            is_draft=False,
        )

        self.dailyplan_meal = DailyPlanMeal.objects.create(
            dailyplan=self.dailyplan,
            meal=self.meal,
            order=1,
        )

        self.proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Adjust DailyPlan",
            summary="Adjust plan to match protein target.",
            targets={
                "protein": 190,
            },
            current_snapshot={
                "dailyplan_id": self.dailyplan.id,
                "protein": 170,
            },
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [],
            },
            validation_summary={
                "within_tolerance": False,
            },
        )

    def test_food_detail_contract_is_json_serializable(self):
        dto = get_food_detail(
            self.user,
            self.food.id,
        )

        data = dto.as_dict()

        self.assertEqual(
            set(data.keys()),
            {
                "id",
                "name",
                "category",
                "created_by_id",
                "macros",
            },
        )

        self.assertEqual(
            set(data["macros"].keys()),
            {
                "protein",
                "carbs",
                "fat",
                "total_kcal",
                "kcal_protein",
                "kcal_carbs",
                "kcal_fat",
                "alloc_protein",
                "alloc_carbs",
                "alloc_fat",
            },
        )

        assert_json_serializable(self, data)

    def test_food_list_contracts_are_json_serializable(self):
        query_results = [
            list_user_foods(self.user),
            list_available_foods(self.user),
            search_foods(self.user, "arroz"),
        ]

        for result in query_results:
            data = [
                item.as_dict()
                for item in result
            ]

            self.assertIsInstance(data, list)
            self.assertGreaterEqual(len(data), 1)

            for item in data:
                self.assertEqual(
                    set(item.keys()),
                    {
                        "id",
                        "name",
                        "category",
                        "created_by_id",
                        "macros",
                    },
                )
                self.assertIsInstance(item["macros"], dict)

            assert_json_serializable(self, data)

    def test_meal_detail_contract_is_json_serializable(self):
        dto = get_meal_detail(
            self.user,
            self.meal.id,
        )

        data = dto.as_dict()

        self.assertEqual(
            set(data.keys()),
            {
                "id",
                "name",
                "category",
                "created_by_id",
                "original_author_id",
                "foods_count",
                "is_public",
                "is_forkable",
                "is_copiable",
                "is_draft",
                "kpis",
                "foods",
            },
        )

        self.assertEqual(
            set(data["kpis"].keys()),
            {
                "ppk",
                "total_kcal",
                "protein",
                "carbs",
                "fat",
                "kcal_protein",
                "kcal_carbs",
                "kcal_fat",
                "alloc_protein",
                "alloc_carbs",
                "alloc_fat",
            },
        )

        self.assertIsInstance(data["foods"], list)
        self.assertEqual(len(data["foods"]), 1)

        self.assertEqual(
            set(data["foods"][0].keys()),
            {
                "mealfood_id",
                "food_id",
                "food_name",
                "quantity",
                "protein",
                "carbs",
                "fat",
                "total_kcal",
                "kcal_protein",
                "kcal_carbs",
                "kcal_fat",
                "alloc_protein",
                "alloc_carbs",
                "alloc_fat",
            },
        )

        assert_json_serializable(self, data)

    def test_meal_list_contracts_are_json_serializable(self):
        query_results = [
            list_user_meals(self.user),
            list_available_meals(self.user),
            search_meals(self.user, "almuerzo"),
        ]

        for result in query_results:
            data = [
                item.as_dict()
                for item in result
            ]

            self.assertIsInstance(data, list)
            self.assertGreaterEqual(len(data), 1)

            for item in data:
                self.assertEqual(
                    set(item.keys()),
                    {
                        "id",
                        "name",
                        "category",
                        "created_by_id",
                        "original_author_id",
                        "foods_count",
                        "is_public",
                        "is_forkable",
                        "is_copiable",
                        "is_draft",
                        "kpis",
                    },
                )
                self.assertIsInstance(item["kpis"], dict)

            assert_json_serializable(self, data)

    def test_dailyplan_detail_contract_is_json_serializable(self):
        dto = get_dailyplan_detail(
            self.user,
            self.dailyplan.id,
        )

        data = dto.as_dict()

        self.assertEqual(
            set(data.keys()),
            {
                "id",
                "name",
                "category",
                "created_by_id",
                "original_author_id",
                "meals_count",
                "foods_count",
                "is_public",
                "is_forkable",
                "is_copiable",
                "is_draft",
                "kpis",
                "meals",
                "foods_aggregation",
            },
        )

        self.assertEqual(
            set(data["kpis"].keys()),
            {
                "ppk",
                "total_kcal",
                "protein",
                "carbs",
                "fat",
                "kcal_protein",
                "kcal_carbs",
                "kcal_fat",
                "alloc_protein",
                "alloc_carbs",
                "alloc_fat",
            },
        )

        self.assertIsInstance(data["meals"], list)
        self.assertEqual(len(data["meals"]), 1)

        self.assertEqual(
            set(data["meals"][0].keys()),
            {
                "dailyplanmeal_id",
                "meal_id",
                "meal_name",
                "hour",
                "note",
                "order",
                "foods_count",
                "kpis",
                "foods",
            },
        )

        self.assertIsInstance(data["meals"][0]["kpis"], dict)
        self.assertIsInstance(data["meals"][0]["foods"], list)

        self.assertIsInstance(data["foods_aggregation"], list)
        self.assertEqual(len(data["foods_aggregation"]), 1)

        self.assertEqual(
            set(data["foods_aggregation"][0].keys()),
            {
                "food_id",
                "food_name",
                "quantity",
                "protein",
                "carbs",
                "fat",
                "total_kcal",
            },
        )

        assert_json_serializable(self, data)

    def test_dailyplan_list_contracts_are_json_serializable(self):
        query_results = [
            list_user_dailyplans(self.user),
            list_available_dailyplans(self.user),
            search_dailyplans(self.user, "entrenamiento"),
        ]

        for result in query_results:
            data = [
                item.as_dict()
                for item in result
            ]

            self.assertIsInstance(data, list)
            self.assertGreaterEqual(len(data), 1)

            for item in data:
                self.assertEqual(
                    set(item.keys()),
                    {
                        "id",
                        "name",
                        "category",
                        "created_by_id",
                        "original_author_id",
                        "meals_count",
                        "foods_count",
                        "is_public",
                        "is_forkable",
                        "is_copiable",
                        "is_draft",
                        "kpis",
                    },
                )
                self.assertIsInstance(item["kpis"], dict)

            assert_json_serializable(self, data)

    def test_user_nutrition_context_contract_is_json_serializable(self):
        dto = get_user_nutrition_context(self.user)

        data = dto.as_dict()

        self.assertEqual(
            set(data.keys()),
            {
                "user_id",
                "username",
                "current_weight",
                "has_current_weight",
            },
        )

        self.assertEqual(data["user_id"], self.user.id)
        self.assertEqual(data["username"], self.user.username)
        self.assertEqual(data["current_weight"], 100)
        self.assertTrue(data["has_current_weight"])

        assert_json_serializable(self, data)

    def test_dailyplan_validation_summary_contract_is_json_serializable(self):
        dto = compare_dailyplan_to_targets(
            user=self.user,
            dailyplan_id=self.dailyplan.id,
            targets={
                "total_kcal": 124.3,
                "protein": 2.7,
                "carbs": 28,
                "fat": 0.3,
                "ppk": 0.027,
            },
            tolerances={
                "total_kcal": 1,
                "protein": 1,
                "carbs": 1,
                "fat": 1,
                "ppk": 0.01,
            },
        )

        data = dto.as_dict()

        self.assertEqual(
            set(data.keys()),
            {
                "dailyplan_id",
                "dailyplan_name",
                "targets",
                "actual",
                "delta",
                "tolerances",
                "within_tolerance",
                "metrics",
            },
        )

        self.assertEqual(data["dailyplan_id"], self.dailyplan.id)
        self.assertEqual(data["dailyplan_name"], self.dailyplan.name)

        self.assertIsInstance(data["targets"], dict)
        self.assertIsInstance(data["actual"], dict)
        self.assertIsInstance(data["delta"], dict)
        self.assertIsInstance(data["tolerances"], dict)
        self.assertIsInstance(data["metrics"], list)

        self.assertGreaterEqual(len(data["metrics"]), 1)

        for metric in data["metrics"]:
            self.assertEqual(
                set(metric.keys()),
                {
                    "metric",
                    "target",
                    "actual",
                    "delta",
                    "tolerance",
                    "within_tolerance",
                    "status",
                },
            )

        assert_json_serializable(self, data)

    def test_nutrition_proposal_contracts_are_json_serializable(self):
        detail = get_proposal_detail(
            self.user,
            self.proposal.id,
        )

        detail_data = detail.as_dict()

        self.assertEqual(
            set(detail_data.keys()),
            {
                "id",
                "dailyplan_id",
                "dailyplan_name",
                "created_by_id",
                "created_by_username",
                "reviewed_by_id",
                "reviewed_by_username",
                "status",
                "status_label",
                "source",
                "title",
                "summary",
                "targets",
                "current_snapshot",
                "proposed_payload",
                "validation_summary",
                "is_reviewable",
                "is_read",
                "is_final",
                "created_at",
                "received_at_label",
                "reviewed_at",
                "audit_events",
                "applied_at",
                "iteration_trace",
            },
        )

        self.assertIsInstance(detail_data["targets"], dict)
        self.assertIsInstance(detail_data["current_snapshot"], dict)
        self.assertIsInstance(detail_data["proposed_payload"], dict)
        self.assertIsInstance(detail_data["validation_summary"], dict)

        assert_json_serializable(self, detail_data)

        query_results = [
            list_user_proposals(self.user),
            list_dailyplan_proposals(
                self.user,
                self.dailyplan.id,
            ),
            search_proposals(
                self.user,
                "adjust",
            ),
        ]

        for result in query_results:
            data = [
                item.as_dict()
                for item in result
            ]

            self.assertGreaterEqual(len(data), 1)

            for item in data:
                self.assertEqual(
                    set(item.keys()),
                    {
                        "id",
                        "dailyplan_id",
                        "dailyplan_name",
                        "created_by_id",
                        "created_by_username",
                        "reviewed_by_id",
                        "reviewed_by_username",
                        "status",
                        "status_label",
                        "source",
                        "title",
                        "summary",
                        "attachment_kind",
                        "attachment_label",
                        "attachment_name",
                        "attachment_icon",
                        "actions",
                        "is_reviewable",
                        "is_read",
                        "is_final",
                        "created_at",
                        "received_at_label",
                        "reviewed_at",
                        "iteration_trace",
                    },
                )

            assert_json_serializable(self, data)