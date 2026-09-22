from types import SimpleNamespace

from django.test import SimpleTestCase

from notas.application.ai_intake.evaluation_quality import (
    QUALITY_ANNOTATIONS_VERSION,
    build_quality_annotation_template,
    evaluate_semantic_repetition,
    grade_validation_reports,
)


def _check(key, passed=True, severity="hard"):
    return SimpleNamespace(
        key=key,
        passed=passed,
        severity=severity,
        detail=f"{key}:{passed}",
    )


def _result(key="scenario", *, checks=()):
    return SimpleNamespace(
        scenario=SimpleNamespace(key=key, expected_outcome="workspace_advanced"),
        checks=tuple(checks),
    )


def _report(run_id, result):
    return SimpleNamespace(run_id=run_id, scenarios=(result,))


class AIAssistantEvaluationQualityTests(SimpleTestCase):
    def test_annotation_template_creates_one_pending_review_per_run(self):
        reports = (
            _report("run-1", _result(key="scenario")),
            _report("run-2", _result(key="scenario")),
        )

        template = build_quality_annotation_template(reports)

        self.assertEqual(template["version"], QUALITY_ANNOTATIONS_VERSION)
        self.assertEqual(
            set(template["reviews"]),
            {"run-1/scenario", "run-2/scenario"},
        )
        self.assertEqual(
            set(template["reviews"]["run-1/scenario"]["criteria"].values()),
            {"pending"},
        )
    def test_semantic_repetition_catches_repeated_non_opening_clause(self):
        turns = (
            SimpleNamespace(
                index=1,
                assistant_message=(
                    "Registré el primer objetivo. Para seguir, cuéntame si quieres usar "
                    "tu ficha personal como base."
                ),
            ),
            SimpleNamespace(
                index=2,
                assistant_message=(
                    "Registré el nuevo objetivo. Para seguir, cuéntame si quieres usar "
                    "tu ficha personal como base."
                ),
            ),
        )

        passed, detail = evaluate_semantic_repetition(turns)

        self.assertFalse(passed)
        self.assertIn("para seguir", detail)
        self.assertIn("[1, 2]", detail)

    def test_healthy_automated_run_stays_pending_without_human_review(self):
        checks = (
            _check("tool_contract"),
            _check("state_mutation_boundary"),
            _check("visible_facts"),
            _check("tool_result_grounding"),
            _check("stable_captured_facts"),
            _check("known_facts_not_reasked"),
            _check("brief_transitions"),
            _check("response_repetition"),
            _check("response_semantic_repetition", severity="quality"),
            _check("card_pacing"),
        )

        grade = grade_validation_reports((_report("run-1", _result(checks=checks)),))

        self.assertEqual(grade["status"], "awaiting_human_review")
        self.assertFalse(grade["passed"])
        self.assertEqual(grade["human_review"]["pending_runs"], 1)

    def test_complete_human_review_can_pass_and_reports_pass_all_reliability(self):
        checks = tuple(_check(key) for key in (
            "tool_contract",
            "state_mutation_boundary",
            "visible_facts",
            "tool_result_grounding",
            "stable_captured_facts",
            "known_facts_not_reasked",
            "brief_transitions",
            "response_repetition",
            "response_semantic_repetition",
            "card_pacing",
        ))
        review = {
            "criteria": {
                "helpfulness": "pass",
                "naturalness": "pass",
                "clarity": "pass",
                "appropriate_next_step": "pass",
            },
            "reviewer": "product",
        }
        annotations = {
            "version": QUALITY_ANNOTATIONS_VERSION,
            "reviews": {"scenario": review},
        }

        grade = grade_validation_reports(
            (
                _report("run-1", _result(checks=checks)),
                _report("run-2", _result(checks=checks)),
            ),
            annotations=annotations,
        )

        self.assertEqual(grade["status"], "passed")
        self.assertTrue(grade["passed"])
        self.assertEqual(grade["reliability"]["scenario"]["passed_runs"], 2)
        self.assertTrue(grade["reliability"]["scenario"]["pass_all"])

    def test_one_failed_quality_dimension_blocks_the_run(self):
        checks = (
            _check("tool_contract"),
            _check("response_semantic_repetition", passed=False, severity="quality"),
        )
        annotations = {
            "reviews": {
                "scenario": {
                    "criteria": {
                        "helpfulness": "pass",
                        "naturalness": "pass",
                        "clarity": "pass",
                        "appropriate_next_step": "pass",
                    }
                }
            }
        }

        grade = grade_validation_reports(
            (_report("run-1", _result(checks=checks)),),
            annotations=annotations,
        )

        self.assertEqual(grade["status"], "quality_regression")
        self.assertIn(
            "interaction_efficiency",
            grade["runs"][0]["automated_quality_failures"],
        )
