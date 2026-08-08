from django.urls import path

from billing.interface.views import (
    apple_app_store_webhook,
    billing_overview,
    cancel_subscription,
    checkout_return,
    create_checkout,
    mercado_pago_webhook,
)

app_name = "billing"

urlpatterns = [
    path("", billing_overview, name="overview"),
    path("checkout/<int:product_id>/", create_checkout, name="create_checkout"),
    path("checkout/return/", checkout_return, name="checkout_return"),
    path("subscriptions/<int:subscription_id>/cancel/", cancel_subscription, name="cancel_subscription"),
    path("webhooks/mercado-pago/", mercado_pago_webhook, name="mercado_pago_webhook"),
    path("webhooks/apple-app-store/", apple_app_store_webhook, name="apple_app_store_webhook"),
]
