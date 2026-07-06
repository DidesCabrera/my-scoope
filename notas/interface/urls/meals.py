from django.urls import path

from notas.interface.views.meals import (
    meal_fork,
    meal_save,
    meal_copy,
    meal_detail,
    meal_list,
    meal_list_reorder,
    meal_list_bulk_delete,
    meal_create,
    meal_configure,
    meal_rename,
    meal_explore_list,
    meal_explore_detail,
    meal_draft_list,
    meal_shared_list,
    meal_remove,
    meal_unshare,
    meal_draft_delete,
    meal_share,
    meal_share_accept,
    meal_share_dismiss,
    meal_share_detail,
)
from notas.interface.views.meal_foods import (
    mealfood_remove,
    mealfood_update,
    add_food_to_meal,
    mealfood_reorder,
)
from notas.interface.views.dailyplans import add_meal_from_list

urlpatterns = [
    path("meals/<int:pk>/share/", meal_share, name="meal_share"),
    # Specific share actions must stay before the shared-detail context route.
    # Otherwise /meals/shared/<share_id>/dismiss/ is interpreted as
    # meal_share_detail_context(pk=<share_id>, dailyplan_id="dismiss").
    path("meals/shared/<int:share_id>/dismiss/", meal_share_dismiss, name="meal_share_dismiss"),
    path("meals/shared/<uuid:token>/", meal_share_accept, name="meal_share_accept"),
    path("meals/shared/<int:pk>/<str:dailyplan_id>/", meal_share_detail, name="meal_share_detail_context"),
    path("meals/shared/<int:pk>/", meal_share_detail, name="meal_share_detail"),
    path("meals/draft/<int:pk>/delete/", meal_draft_delete, name="meal_draft_delete"),
    path("meals/draft/", meal_draft_list, name="meal_draft_list"),
    path("meals/shared/", meal_shared_list, name="meal_shared_list"),
    path("meals/<int:pk>/remove/", meal_remove, name="meal_remove"),
    path("meals/shares/<int:share_id>/unshare/", meal_unshare, name="meal_unshare"),
    path("meals/", meal_list, name="meal_list"),
    path("meals/reorder/", meal_list_reorder, name="meal_list_reorder"),
    path("meals/bulk-delete/", meal_list_bulk_delete, name="meal_list_bulk_delete"),
    path("meals/explore/", meal_explore_list, name="meal_explore_list"),
    path("meals/<int:pk>/", meal_detail, name="meal_detail"),
    path("meals/explore/<int:pk>/", meal_explore_detail, name="meal_explore_detail"),
    path("meals/create/", meal_create, name="meal_create"),
    path("meals/<int:pk>/rename/", meal_rename, name="meal_rename"),
    path("meals/<int:pk>/configure/", meal_configure, name="meal_configure"),
    path("meals/<int:meal_id>/fork/", meal_fork, name="meal_fork"),
    path("meals/<int:meal_id>/save/", meal_save, name="meal_save"),
    path("meals/<int:pk>/copy/", meal_copy, name="meal_copy"),
    path("meals/<int:pk>/add-food/", add_food_to_meal, name="add_food_to_meal"),
    path("meal-foods/<int:pk>/remove/", mealfood_remove, name="mealfood_remove"),
    path("meals/<int:meal_id>/mealfoods/<int:mealfood_id>/update/", mealfood_update, name="mealfood_update"),
    path("meals/<int:meal_id>/add-to-dailyplan/", add_meal_from_list, name="add_meal_from_list"),
    path("meals/<int:meal_id>/foods/reorder/", mealfood_reorder, name="mealfood_reorder"),
]
