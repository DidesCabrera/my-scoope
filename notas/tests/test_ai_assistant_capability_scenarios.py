from copy import deepcopy
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import TestCase

from ai_assistant.models import AIPreparedAction
from notas.application.ai_intake.capability_scenarios import build_capability_scenarios, prepared_patch_check, specialize_capability_scenario
from notas.application.ai_intake.evaluation_artifacts import capture_review_artifacts
from notas.application.ai_intake.evaluation_lab import _cleanup_new_review_artifacts
from notas.application.ai_intake.real_provider_lab_extensions import RealProviderValidationScenario, state_mutation_check_values, validation_state_snapshot
from notas.application.ai_tools.prepared_actions import prepare_workspace_patch
from notas.domain.models import DailyPlan, Food, Meal, MealFood, NutritionProposal, Program


class CapabilityScenarioTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="capability-lab")
        self.food = Food.objects.create(name="Food", protein=10, carbs=20, fat=5, created_by=self.user)
        Food.objects.create(name="Other", protein=10, carbs=20, fat=5, created_by=self.user)
        self.meal = Meal.objects.create(name="Meal", created_by=self.user, is_draft=False)
        MealFood.objects.create(meal=self.meal, food=self.food, quantity=100)
        DailyPlan.objects.create(name="Plan", created_by=self.user, is_draft=False)
        Program.objects.create(name="Program", created_by=self.user, is_draft=False)

    def test_all_exact_oracles_match_real_patch_preparation(self):
        for original in build_capability_scenarios(RealProviderValidationScenario).values():
            with self.subTest(scenario=original.key):
                scenario = specialize_capability_scenario(original, user=self.user)
                before = set(AIPreparedAction.objects.values_list("pk", flat=True))
                wanted = deepcopy(scenario.ground_truth["expected_operations"][0])
                resource, action = wanted.pop("action_key").split(".", 1)
                if action == "remove_food":
                    wanted["target_id"] = self.meal.pk
                prepare_workspace_patch(user=self.user, title="Test", summary="Test", operations=[{"resource": resource, "action": action, **wanted}])
                passed, detail = prepared_patch_check(scenario, user=self.user, previous_ids=before)
                self.assertTrue(passed, detail)

    def test_content_mutation_detected_even_when_counts_match(self):
        before = validation_state_snapshot(self.user)
        self.food.protein = 30
        self.food.save()
        after = validation_state_snapshot(self.user)
        self.assertEqual(before["foods"], after["foods"])
        passed, _, _ = state_mutation_check_values(SimpleNamespace(mutation_policy="read_only"), state_before=before, state_after=after)
        self.assertFalse(passed)

    def test_cleanup_never_removes_artifacts_outside_capture(self):
        existing = NutritionProposal.objects.create(created_by=self.user, title="Existing", status="pending_review")
        with capture_review_artifacts(self.user) as created:
            captured = NutritionProposal.objects.create(created_by=self.user, title="Lab", status="pending_review")
        later = NutritionProposal.objects.create(created_by=self.user, title="Other request", status="pending_review")
        _cleanup_new_review_artifacts(user=self.user, created=created)
        self.assertFalse(NutritionProposal.objects.filter(pk=captured.pk).exists())
        self.assertTrue(NutritionProposal.objects.filter(pk=existing.pk).exists())
        self.assertTrue(NutritionProposal.objects.filter(pk=later.pk).exists())
