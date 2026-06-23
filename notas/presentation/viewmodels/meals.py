"""Public Meal viewmodel boundary.

Views and use cases should import Meal presentation builders from here instead
of depending directly on composition implementation modules.
"""

from notas.presentation.composition.viewmodel.meal.configure_meal_builder import (
    build_meal_configure_vm,
)
from notas.presentation.composition.viewmodel.meal.detail_meal_builder import (
    build_meal_detail_vm,
)
from notas.presentation.composition.viewmodel.meal.list_meal_builder import (
    build_meal_list_vm,
)
from notas.presentation.composition.viewmodel.meal.meal_content import (
    MealDetailContentData,
    MealListContentData,
    build_meal_detail_content_data,
    build_meal_list_content_data,
)

__all__ = [
    "MealDetailContentData",
    "MealListContentData",
    "build_meal_configure_vm",
    "build_meal_detail_content_data",
    "build_meal_detail_vm",
    "build_meal_list_content_data",
    "build_meal_list_vm",
]
