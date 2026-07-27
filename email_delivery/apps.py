from django.apps import AppConfig


class EmailDeliveryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "email_delivery"
    verbose_name = "Email delivery"

    def ready(self):
        from email_delivery import checks  # noqa: F401
