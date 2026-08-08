from django.urls import path

from .views import delete_account, nutrition_onboarding

app_name = "accounts"

urlpatterns = [
    path("onboarding/", nutrition_onboarding, name="nutrition_onboarding"),
    path("delete/", delete_account, name="delete_account"),
]
