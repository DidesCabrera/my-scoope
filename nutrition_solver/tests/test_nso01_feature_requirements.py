import json

from django.test import SimpleTestCase

from nutrition_solver.domain.capabilities import (
    DEFAULT_MEAL_OPTIMIZATION_FEATURES,
    MissingFeatureBehavior,
    SolverFeatureAvailability,
    SolverFeatureKey,
    SolverFeatureRequirement,
    SolverFeatureRequirements,
    assess_solver_feature_requirements,
)


class NutritionSolverNSO01FeatureRequirementsTests(SimpleTestCase):
    def test_requirements_are_pure_serializable_and_versioned(self):
        payload = DEFAULT_MEAL_OPTIMIZATION_FEATURES.as_dict()

        json.dumps(payload)
        self.assertEqual(payload["schema_version"], "solver_food_capabilities.v1")
        self.assertIn("nutrients", [item["feature"] for item in payload["requirements"]])

    def test_missing_required_feature_excludes_candidate(self):
        assessment = assess_solver_feature_requirements(
            DEFAULT_MEAL_OPTIMIZATION_FEATURES,
            {
                SolverFeatureKey.NUTRIENTS: SolverFeatureAvailability(True, 90, "operational_snapshot"),
                SolverFeatureKey.PORTION_BOUNDS: SolverFeatureAvailability(True, 90, "operational_snapshot"),
            },
        )

        self.assertFalse(assessment.is_eligible)
        self.assertEqual(assessment.missing_required, ("preparation_state",))

    def test_optional_feature_can_warn_without_blocking(self):
        requirements = SolverFeatureRequirements(
            profile="test",
            requirements=(
                SolverFeatureRequirement(
                    SolverFeatureKey.COST_BAND,
                    missing_behavior=MissingFeatureBehavior.WARN_AND_CONTINUE,
                ),
            ),
        )

        assessment = assess_solver_feature_requirements(requirements, {})

        self.assertTrue(assessment.is_eligible)
        self.assertEqual(assessment.warnings, ("optional_feature_unavailable:cost_band",))

    def test_low_confidence_required_feature_is_distinct_from_missing(self):
        requirements = SolverFeatureRequirements(
            profile="test",
            requirements=(
                SolverFeatureRequirement(SolverFeatureKey.NUTRIENTS, required=True, minimum_confidence=80),
            ),
        )

        assessment = assess_solver_feature_requirements(
            requirements,
            {SolverFeatureKey.NUTRIENTS: SolverFeatureAvailability(True, 60, "derived")},
        )

        self.assertFalse(assessment.is_eligible)
        self.assertEqual(assessment.low_confidence_required, ("nutrients",))
