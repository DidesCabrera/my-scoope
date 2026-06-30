from django.test import SimpleTestCase

from notas.application.nutrition_engine.meal_templates import (
    build_dailyplan_meal_templates,
    classify_meal_kind,
    normalized_meal_allocations,
    roles_for_meal_kind,
)


class NutritionEngineMealTemplateTests(SimpleTestCase):
    def test_builds_four_meal_day_with_distinct_kinds_and_allocations(self):
        templates = build_dailyplan_meal_templates(4)

        self.assertEqual([template.label for template in templates], ["Desayuno", "Almuerzo", "Snack", "Cena"])
        self.assertEqual([template.kind for template in templates], ["breakfast", "main", "snack", "dinner"])
        self.assertEqual([template.hour for template in templates], ["09:00", "13:00", "17:00", "21:00"])
        self.assertAlmostEqual(sum(template.kcal_allocation for template in templates), 1.0)

    def test_snack_template_does_not_include_vegetable_role(self):
        snack_roles = roles_for_meal_kind("snack")

        self.assertNotIn("vegetable", [role.role for role in snack_roles])
        self.assertEqual([role.role for role in snack_roles if role.required], ["protein", "carb"])

    def test_main_and_dinner_templates_include_optional_vegetable(self):
        main_roles = roles_for_meal_kind("main")
        dinner_roles = roles_for_meal_kind("dinner")

        self.assertIn("vegetable", [role.role for role in main_roles])
        self.assertIn("vegetable", [role.role for role in dinner_roles])
        self.assertFalse(next(role for role in main_roles if role.role == "vegetable").required)

    def test_classifies_labels_independently_from_accents(self):
        self.assertEqual(classify_meal_kind("Media mañana", index=1, meals_per_day=5), "snack")
        self.assertEqual(classify_meal_kind("Colación", index=5, meals_per_day=6), "snack")
        self.assertEqual(classify_meal_kind("Cena", index=3, meals_per_day=4), "dinner")

    def test_normalized_allocations_fallback_sum_to_one(self):
        allocations = normalized_meal_allocations(7)

        self.assertEqual(len(allocations), 7)
        self.assertAlmostEqual(sum(allocations), 1.0)
