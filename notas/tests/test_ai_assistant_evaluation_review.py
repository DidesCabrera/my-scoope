from copy import deepcopy

from django.test import SimpleTestCase

from notas.application.ai_intake.evaluation_review import review_saved_report, saved_review_template


def evidence():
    return {
        "version": "ai_assistant.evaluation_lab.v2", "run_id": "lab-one", "mode": "live_provider",
        "status": "awaiting_quality_review", "passed": False,
        "live_validations": [{"run_id": "one-r1", "provider": "openai", "model": "test",
            "scenarios": [{"key": "create", "expected_outcome": "prepared_patch",
                "checks": [{"key": "prepared_patch_exact", "passed": True, "severity": "hard", "detail": "exact"}],
                "turns": [{"user": "Crea una comida", "assistant": "Preparada para revisión"}]}]}],
    }


class SavedEvaluationReviewTests(SimpleTestCase):
    def reviews(self, payload, kind="human"):
        annotations = saved_review_template(payload)
        for review in annotations["reviews"].values():
            review.update(reviewer="test-reviewer", reviewer_kind=kind)
            review["criteria"] = dict.fromkeys(review["criteria"], "pass")
        return annotations

    def test_review_preserves_trajectory_and_does_not_mutate_source(self):
        payload = evidence()
        original = deepcopy(payload)
        result = review_saved_report(payload, self.reviews(payload))
        self.assertEqual(result["status"], "passed")
        self.assertEqual(payload, original)
        self.assertEqual(result["live_validations"], original["live_validations"])
        self.assertEqual(result["review_provenance"]["provider_calls"], 0)

    def test_agent_review_cannot_satisfy_human_gate(self):
        payload = evidence()
        self.assertEqual(review_saved_report(payload, self.reviews(payload, "agent"))["status"], "awaiting_quality_review")

    def test_annotations_cannot_be_replayed_on_changed_evidence(self):
        payload = evidence()
        annotations = self.reviews(payload)
        payload["live_validations"][0]["scenarios"][0]["turns"][0]["assistant"] = "Otro resultado"
        with self.assertRaisesMessage(ValueError, "Evidence changed"):
            review_saved_report(payload, annotations)

    def test_review_does_not_erase_fixture_failure(self):
        payload = evidence()
        payload["status"] = "blocked_by_fixture"
        self.assertEqual(review_saved_report(payload, self.reviews(payload))["status"], "blocked_by_fixture")

    def test_human_approval_cannot_hide_incorrect_operation(self):
        payload = evidence()
        payload["live_validations"][0]["scenarios"][0]["checks"][0]["passed"] = False
        self.assertEqual(review_saved_report(payload, self.reviews(payload))["status"], "hard_regression")

    def test_unknown_or_scenario_wide_review_is_rejected(self):
        payload = evidence()
        annotations = self.reviews(payload)
        annotations["reviews"]["create"] = annotations["reviews"].pop("one-r1/create")
        with self.assertRaisesMessage(ValueError, "unknown trajectories"):
            review_saved_report(payload, annotations)
