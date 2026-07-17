from django.test import SimpleTestCase

from nutrition_solver.application.candidate_portfolio import build_candidate_portfolio
from nutrition_solver.domain.capabilities import SolverFeatureKey
from nutrition_solver.domain.food_profiles import SolverFeatureValue, SolverFoodProfile
from nutrition_solver.domain.meal_grammar import MAIN_PLATE
from nutrition_solver.domain.models import PortionBounds, SolverFood


def _profile(food_id, roles, *, affinity=(), confidence=90):
    return SolverFoodProfile(
        food=SolverFood(food_id, f"food-{food_id}", "balanced", 10, 10, 5, 125, PortionBounds(10, 200, 5), False),
        features=(
            SolverFeatureValue(SolverFeatureKey.FUNCTIONAL_ROLES, tuple(roles), confidence, "test"),
            SolverFeatureValue(SolverFeatureKey.MEAL_AFFINITIES, tuple(affinity), 90, "test"),
        ),
    )


class NutritionSolverNSO06CandidatePortfolioTests(SimpleTestCase):
    def setUp(self):
        self.profiles = (
            _profile(1, ("primary_protein",), confidence=80),
            _profile(2, ("primary_protein",), affinity=("main",), confidence=90),
            _profile(3, ("starch_or_carbohydrate",), confidence=85),
            _profile(4, ("starch_or_carbohydrate",), confidence=95),
        )

    def test_compares_multiple_complete_combinations(self):
        portfolio = build_candidate_portfolio(self.profiles, MAIN_PLATE, meal_kind="main")

        self.assertEqual(len(portfolio.combinations), 4)
        self.assertEqual(portfolio.combinations[0].food_ids, (2, 4))

    def test_exclusions_and_preferences_change_portfolio_deterministically(self):
        first = build_candidate_portfolio(
            self.profiles,
            MAIN_PLATE,
            excluded_food_ids=(2,),
            preferred_food_ids=(3,),
        )
        second = build_candidate_portfolio(
            self.profiles,
            MAIN_PLATE,
            excluded_food_ids=(2,),
            preferred_food_ids=(3,),
        )

        self.assertEqual(first.as_dict(), second.as_dict())
        self.assertEqual(first.combinations[0].food_ids, (1, 3))

    def test_same_food_is_not_used_twice_for_two_required_groups(self):
        mixed = _profile(10, ("primary_protein", "starch_or_carbohydrate"), confidence=100)

        portfolio = build_candidate_portfolio((mixed,), MAIN_PLATE)

        self.assertFalse(portfolio.combinations)
        self.assertIn("candidate_portfolio_has_no_complete_combination", portfolio.diagnostics)
