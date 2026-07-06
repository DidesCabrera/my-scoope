from django.apps import AppConfig


class FoodCatalogConfig(AppConfig):
    """Django app boundary for the master food catalog subsystem."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "food_catalog"
    verbose_name = "Food Catalog"
