import unittest

from nutrition_solver.evaluation_lab.__main__ import gate
from nutrition_solver.evaluation_lab.metrics import assess_human_review, compare_runs
from nutrition_solver.evaluation_lab.runner import run_suite


class NutritionSolverEvaluationLabTests(unittest.TestCase):
    # These assertions validate fixture outcomes; solver latency has a separate gate.
    def test_fixed_fixture_replays_feasible_and_explained_infeasible_cases(self):
        run = run_suite(case_ids={"S02", "S16"}, alternatives=1, time_limit_ms=1500, stability=False)
        by_id = {case["id"]: case for case in run["cases"]}
        self.assertEqual(run["summary"]["case_count"], 2)
        self.assertTrue(by_id["S02"]["feasible"])
        self.assertEqual(by_id["S02"]["candidate_count"], 157)
        self.assertEqual(by_id["S02"]["metrics"]["hard_violations"], [])
        self.assertFalse(by_id["S16"]["feasible"])
        self.assertEqual(by_id["S16"]["candidate_count"], 19)
        self.assertTrue(by_id["S16"]["reason_code"])
        self.assertEqual(gate(run)["automatic_gate"], "failed")

    def test_comparison_rejects_changed_catalog_or_configuration(self):
        run = run_suite(case_ids={"S16"}, alternatives=1, time_limit_ms=100, stability=False)
        other = {**run, "food_digest": "different"}
        with self.assertRaisesRegex(ValueError, "incomparable_food_digest"):
            compare_runs(run, other)
        other = {**run, "config": {**run["config"], "time_limit_ms": 200}}
        with self.assertRaisesRegex(ValueError, "incomparable_config"):
            compare_runs(run, other)

    def test_human_review_cannot_pass_with_missing_or_severe_ratings(self):
        run = run_suite(case_ids={"S02"}, alternatives=1, time_limit_ms=1500, stability=False)
        review = {"run_id": run["run_id"], "reviewer": "Reviewer", "reviewed_at": "2026-11-12",
                  "cases": [{"id": "S02", "coherence": 2, "portion_realism": 4,
                             "preparation": 4, "practicality": 4, "local_relevance": 4}]}
        self.assertIn("severe_quality_defect:S02", assess_human_review(run, review)["errors"])
        review["cases"][0]["coherence"] = 5
        self.assertEqual(assess_human_review(run, review)["status"], "passed")

    def test_comparison_names_new_infeasibility(self):
        run = run_suite(case_ids={"S02"}, alternatives=1, time_limit_ms=1500, stability=False)
        candidate = {**run, "run_id": "changed",
                     "cases": [{**run["cases"][0], "feasible": False, "reason_code": "cp_sat_infeasible"}]}
        comparison = compare_runs(run, candidate)
        self.assertEqual(comparison["new_infeasible"], ["S02"])
        self.assertIn({"id": "S02", "reason": "new_infeasibility"}, comparison["regressions"])
