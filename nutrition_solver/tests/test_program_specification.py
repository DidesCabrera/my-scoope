from copy import deepcopy
from dataclasses import replace

from django.test import SimpleTestCase

from nutrition_solver.application.contracts import SolverConstraint
from nutrition_solver.application.optimizer_v2 import solve_optimization_problem
from nutrition_solver.application.problem_v2 import NutrientRange
from nutrition_solver.application.program_specification import linear_week_targets, parse_program_specification
from nutrition_solver.application.quality import assess_optimization_quality
from nutrition_solver.tests.test_nso08_daily_optimization import _daily_problem


def example_spec(weeks=8):
    return {"version": 1, "duration_weeks": weeks, "meals_per_day": 4, "weight_basis": "projected",
            "measured_weight_kg": 85, "protein_min_ppk": 2, "protein_max_ppk": 2.2,
            "fat_max_percent": 25, "calorie_tolerance_percent": 3,
            "fruit_min_g": 200, "vegetable_min_g": 250, "weekly_fruit_species": 3,
            "weekly_vegetable_species": 3, "max_family_per_week_per_slot": 3, "energy_source": "manual",
            "weeks": linear_week_targets(duration_weeks=weeks, start_kcal=2500, end_kcal=1700 if weeks > 1 else 2500,
                                         start_weight=85, end_weight=80 if weeks > 1 else 85)}


class ProgramSpecificationTests(SimpleTestCase):
    def test_roundtrip_and_weekly_protein(self):
        spec = parse_program_specification(example_spec())
        self.assertEqual(spec.weeks[0].protein_min_g, 170)
        self.assertEqual(spec.weeks[-1].protein_max_g, 176)
        self.assertEqual(spec, parse_program_specification(spec.as_dict()))

    def test_measured_weight_does_not_follow_projection(self):
        data = example_spec()
        data["weight_basis"] = "measured"
        spec = parse_program_specification(data)
        self.assertEqual(spec.weeks[-1].protein_min_g, 170)
        self.assertEqual(spec.weeks[-1].projected_weight_kg, 80)

    def test_nullable_optional_provider_fields_preserve_default_contract(self):
        data = example_spec()
        data.update(macro_distribution=None, macro_tolerance_percent=None)
        self.assertEqual(parse_program_specification(data), parse_program_specification(example_spec()))
        data["macro_tolerance_percent"] = 0
        self.assertEqual(parse_program_specification(data).macro_tolerance_percent, 0)

    def test_unknown_nonfinite_and_incomplete_rejected(self):
        for key, value in (("unknown", 1), ("fat_max_percent", float("nan")), ("protein_min_ppk", 3),
                           ("duration_weeks", True), ("weight_basis", "guess"), ("weeks", [])):
            data = example_spec()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_program_specification(data)
        data = parse_program_specification(example_spec()).as_dict()
        data["weeks"][0]["protein_min_g"] = 1
        with self.assertRaisesMessage(ValueError, "derived_target_mismatch"):
            parse_program_specification(data)

    def test_unknown_hard_requirement_is_not_silently_ignored(self):
        problem = _daily_problem(constraints=(SolverConstraint("unsupported", "hard", {}),))
        with self.assertRaisesMessage(ValueError, "unsupported_hard_constraint"):
            solve_optimization_problem(problem, backend="cp_sat_v1")

    def test_heuristic_result_does_not_certify_violated_daily_range(self):
        problem = replace(_daily_problem(), daily_nutrient_ranges=(NutrientRange("protein", 1000, 999, 1001),))
        result = solve_optimization_problem(problem)
        quality = assess_optimization_quality(problem, result)
        self.assertFalse(quality.hard_constraints_satisfied)
