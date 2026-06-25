from django.urls import path

from notas.interface.views.comparators import (
    comparator_index,
    dailyplan_comparator,
    food_comparator,
    meal_comparator,
    saved_comparison_detail,
    saved_comparison_rename,
    saved_comparisons_index,
    saved_comparisons_list,
)

urlpatterns = [
    path("comparators/", comparator_index, name="comparator_index"),
    path("comparators/saved/", saved_comparisons_index, name="saved_comparisons_index"),
    path("comparators/saved/<slug:kind>/", saved_comparisons_list, name="saved_comparisons_list"),
    path("comparators/saved/<slug:kind>/<int:pk>/rename/", saved_comparison_rename, name="saved_comparison_rename"),
    path("comparators/saved/<slug:kind>/<int:pk>/", saved_comparison_detail, name="saved_comparison_detail"),
    path("comparators/foods/", food_comparator, name="food_comparator"),
    path("comparators/meals/", meal_comparator, name="meal_comparator"),
    path("comparators/dailyplans/", dailyplan_comparator, name="dailyplan_comparator"),
]
