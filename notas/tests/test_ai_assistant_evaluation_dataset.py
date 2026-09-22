from django.test import SimpleTestCase

from notas.application.ai_intake.evaluation_dataset import (
    EVALUATION_DATASET_VERSION,
    assistant_task_dataset,
    evaluate_assistant_task_dataset,
)


class AIAssistantEvaluationDatasetTests(SimpleTestCase):
    def test_dataset_has_64_balanced_versioned_cases(self):
        cases = assistant_task_dataset()

        self.assertEqual(EVALUATION_DATASET_VERSION, "ai_assistant.task_dataset.v1")
        self.assertEqual(len(cases), 64)
        self.assertEqual(len({case.key for case in cases}), 64)
        self.assertEqual(
            {case.family for case in cases},
            {
                "dailyplan_create",
                "meal_create",
                "program_create",
                "workspace_mutation",
                "workspace_query",
                "profile_fact",
                "preference_fact",
                "response_only",
            },
        )

    def test_all_dataset_cases_match_the_objective_contract(self):
        report = evaluate_assistant_task_dataset()

        self.assertTrue(report["passed"], report["failures"])
        self.assertEqual(report["passed_count"], 64)
        self.assertEqual(report["failure_count"], 0)
        self.assertTrue(report["live_trajectory_layer_is_separate"])
