from django.test import SimpleTestCase

from notas.application.ai_intake.evaluation_dataset import (
    EVALUATION_DATASET_VERSION,
    assistant_task_dataset,
    evaluate_assistant_task_dataset,
)


class AIAssistantEvaluationDatasetTests(SimpleTestCase):
    def test_dataset_has_balanced_versioned_cases(self):
        cases = assistant_task_dataset()

        self.assertEqual(EVALUATION_DATASET_VERSION, "ai_assistant.task_dataset.v2")
        self.assertEqual(len(cases), 72)
        self.assertEqual(len({case.key for case in cases}), 72)
        self.assertEqual(sum(case.partition == "holdout" for case in cases), 18)
        self.assertTrue(all(case.as_dict()["data_classification"] == "synthetic_no_user_data" for case in cases))
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
                "supplements",
            },
        )

    def test_all_dataset_cases_match_the_objective_contract(self):
        report = evaluate_assistant_task_dataset()

        self.assertTrue(report["passed"], report["failures"])
        self.assertEqual(report["passed_count"], 72)
        self.assertEqual(report["failure_count"], 0)
        self.assertEqual(report["partition_counts"], {"development": 54, "holdout": 18})
        self.assertTrue(report["live_trajectory_layer_is_separate"])

    def test_holdout_can_be_run_separately_after_candidate_freeze(self):
        report = evaluate_assistant_task_dataset(partition="holdout")

        self.assertTrue(report["passed"])
        self.assertEqual(report["case_count"], 18)
        self.assertEqual(report["partition_counts"], {"development": 0, "holdout": 18})
