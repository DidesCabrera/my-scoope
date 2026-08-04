from django.urls import path

from notas.interface.views.authors import (
    author_dailyplans,
    author_meals,
    author_profile,
    author_programs,
)
from notas.interface.views.profile import (
    profile_credits,
    profile_detail,
    profile_nutrition,
    profile_nutrition_update,
)
from notas.interface.views.weight import register_weight

urlpatterns = [
    path("profile/", profile_detail, name="profile_detail"),
    path("profile/personal/", profile_nutrition, name="profile_nutrition"),
    path("profile/credits/", profile_credits, name="profile_credits"),
    path("profile/nutrition/update/", profile_nutrition_update, name="profile_nutrition_update"),
    path("authors/<str:username>/", author_profile, name="author_profile"),
    path("authors/<str:username>/programs/", author_programs, name="author_programs"),
    path("authors/<str:username>/dailyplans/", author_dailyplans, name="author_dailyplans"),
    path("authors/<str:username>/meals/", author_meals, name="author_meals"),
    path("weight/register/", register_weight, name="weight_register"),
]
