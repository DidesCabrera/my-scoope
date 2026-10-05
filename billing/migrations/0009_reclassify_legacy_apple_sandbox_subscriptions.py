from django.db import migrations

APPLE_PROVIDER = "apple_app_store"
LIVE = "live"
SANDBOX = "sandbox"


def reclassify_legacy_sandbox_subscriptions(apps, schema_editor):
    BillingProduct = apps.get_model("billing", "BillingProduct")
    ProviderSubscription = apps.get_model("billing", "ProviderSubscription")

    subscriptions = ProviderSubscription.objects.filter(
        provider=APPLE_PROVIDER,
        product__environment=LIVE,
    ).select_related("product")
    for subscription in subscriptions.iterator():
        metadata = subscription.metadata or {}
        if str(metadata.get("apple_environment", "")).strip().lower() != "sandbox":
            continue

        live_product = subscription.product
        sandbox_product, _ = BillingProduct.objects.get_or_create(
            provider=APPLE_PROVIDER,
            environment=SANDBOX,
            external_product_id=live_product.external_product_id,
            external_price_id=live_product.external_price_id,
            defaults={
                "offer_id": live_product.offer_id,
                "account_plan_id": live_product.account_plan_id,
                "kind": live_product.kind,
                "currency": live_product.currency,
                "amount_minor": live_product.amount_minor,
                "interval": live_product.interval,
                "interval_count": live_product.interval_count,
                "active": False,
                "metadata": {
                    **(live_product.metadata or {}),
                    "legacy_apple_environment_reclassified": True,
                },
            },
        )
        subscription.product_id = sandbox_product.pk
        subscription.save(update_fields=["product_id", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0008_applesandboxaccess"),
    ]

    operations = [
        migrations.RunPython(reclassify_legacy_sandbox_subscriptions, migrations.RunPython.noop),
    ]
