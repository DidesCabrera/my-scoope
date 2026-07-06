from django.urls import path

from .views import nutrition_onboarding


app_name = "accounts"

urlpatterns = [
    path("onboarding/", nutrition_onboarding, name="nutrition_onboarding"),
]
