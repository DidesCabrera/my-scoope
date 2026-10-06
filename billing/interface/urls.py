from django.urls import path

from billing.interface.views import (
    apple_app_store_webhook,
    billing_overview,
    cancel_subscription,
    checkout_return,
    create_checkout,
    create_credit_pack_mercado_pago_checkout,
    google_play_webhook,
    mercado_pago_webhook,
    paddle_customer_portal,
    paddle_webhook,
)

app_name = "billing"

urlpatterns = [
    path("", billing_overview, name="overview"),
    path("checkout/<int:product_id>/", create_checkout, name="create_checkout"),
    path("credit-packs/mercado-pago/<int:product_id>/", create_credit_pack_mercado_pago_checkout, name="credit_pack_mercado_pago_checkout"),
    path("checkout/return/", checkout_return, name="checkout_return"),
    path("subscriptions/<int:subscription_id>/cancel/", cancel_subscription, name="cancel_subscription"),
    path("subscriptions/<int:subscription_id>/paddle/", paddle_customer_portal, name="paddle_customer_portal"),
    path("webhooks/mercado-pago/", mercado_pago_webhook, name="mercado_pago_webhook"),
    path("webhooks/paddle/", paddle_webhook, name="paddle_webhook"),
    path("webhooks/apple-app-store/", apple_app_store_webhook, name="apple_app_store_webhook"),
    path("webhooks/google-play/", google_play_webhook, name="google_play_webhook"),
    path(
        "webhooks/apple-app-store/production/",
        apple_app_store_webhook,
        {"environment": "production"},
        name="apple_app_store_production_webhook",
    ),
    path(
        "webhooks/apple-app-store/sandbox/",
        apple_app_store_webhook,
        {"environment": "sandbox"},
        name="apple_app_store_sandbox_webhook",
    ),
]
