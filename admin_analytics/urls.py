from django.urls import path

from admin_analytics.views import accounts, ai_assistant, alerts, food_catalog, nutrition_solver, overview, product_activity


urlpatterns = [
    path("", overview, name="admin_analytics_overview"),
    path("accounts/", accounts, name="admin_analytics_accounts"),
    path("ai-assistant/", ai_assistant, name="admin_analytics_ai_assistant"),
    path("product-activity/", product_activity, name="admin_analytics_product_activity"),
    path("food-catalog/", food_catalog, name="admin_analytics_food_catalog"),
    path("nutrition-solver/", nutrition_solver, name="admin_analytics_nutrition_solver"),
    path("alerts/", alerts, name="admin_analytics_alerts"),
]
