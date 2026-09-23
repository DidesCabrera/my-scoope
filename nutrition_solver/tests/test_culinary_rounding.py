from dataclasses import replace

from django.test import SimpleTestCase

from nutrition_solver.application.culinary_planner import (
    CulinaryCandidate,
    CulinaryPlanningError,
    Ingredient,
    solve_culinary_week,
)
from nutrition_solver.application.program_specification import parse_program_specification
from nutrition_solver.tests.test_program_specification import example_spec


class CulinaryRoundingTests(SimpleTestCase):
    def test_accumulated_rounding_cannot_certify_out_of_range_protein(self):
        spec = parse_program_specification(example_spec(1))
        spec = replace(spec, meals_per_day=1, fruit_min_g=0, vegetable_min_g=0,
                       weekly_fruit_species=0, weekly_vegetable_species=0, max_family_per_week_per_slot=7)
        # Integer rounding formerly claimed 170g, actual protein is 170.149g.
        week = replace(spec.weeks[0], protein_min_g=169.9, protein_max_g=170.08)
        food = Ingredient(1, "Precision fixture", "base", "protein", "fixture", 1000, 1000, 1, 17.0149, 45, 0)
        candidate = CulinaryCandidate(1, 1, "fixture", "Fixture", ("lunch",), "Cook", (food,), (), "digest", "rule_validated")
        with self.assertRaises(CulinaryPlanningError) as caught:
            solve_culinary_week(spec, week, ({"kind": "lunch", "allocation": 1},), (candidate,), time_limit_seconds=1)
        self.assertEqual(caught.exception.code, "culinary_candidate_pool_infeasible")
