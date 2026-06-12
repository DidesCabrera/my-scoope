from notas.application.services.food_imports.localized_names import (
    resolve_food_display_name,
)
from notas.presentation.viewmodels.content.dailyplan.list_vm import MenuUI, MenuMealUI


def _format_quantity(value):
    if value is None:
        return "0"

    numeric_value = float(value)

    if numeric_value.is_integer():
        return str(int(numeric_value))

    return f"{numeric_value:.1f}".rstrip("0").rstrip(".")


def build_dailyplan_menu(dailyplan_meals):

    meals_menu = []

    for dpm in dailyplan_meals:

        meal = dpm.meal

        foods = [
            f"{resolve_food_display_name(mf.food)} ({_format_quantity(mf.quantity)}g)"
            for mf in meal.meal_food_set.all()
        ]

        meals_menu.append(
            MenuMealUI(
                meal_name=meal.name,
                foods=foods
            )
        )

    return MenuUI(meals=meals_menu)
