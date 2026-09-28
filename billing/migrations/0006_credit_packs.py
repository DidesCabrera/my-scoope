import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_credit_packs(apps, schema_editor):
    Offer = apps.get_model("billing", "CreditPackOffer")
    for code, credits, amount, order in (
        ("credits-500", 500, 2990, 10),
        ("credits-1000", 1000, 5990, 20),
        ("credits-2000", 2000, 9990, 30),
    ):
        Offer.objects.get_or_create(
            code=code,
            defaults={"credits": credits, "amount_minor": amount, "currency": "CLP", "display_order": order},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0005_commercial_launch_prices"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CreditPackOffer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=80, unique=True)),
                ("credits", models.PositiveIntegerField()),
                ("amount_minor", models.PositiveBigIntegerField()),
                ("currency", models.CharField(default="CLP", max_length=3)),
                ("active", models.BooleanField(db_index=True, default=True)),
                ("public", models.BooleanField(db_index=True, default=True)),
                ("display_order", models.PositiveSmallIntegerField(default=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["display_order", "credits"],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(credits__gt=0), name="credit_pack_credits_positive"),
                    models.CheckConstraint(condition=models.Q(amount_minor__gt=0), name="credit_pack_price_positive"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ProviderCreditPack",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[("paddle", "Paddle"), ("mercado_pago", "Mercado Pago"), ("apple_app_store", "Apple App Store"), ("google_play", "Google Play")], db_index=True, max_length=32)),
                ("environment", models.CharField(choices=[("sandbox", "Sandbox"), ("live", "Live")], max_length=16)),
                ("external_product_id", models.CharField(max_length=160)),
                ("external_price_id", models.CharField(blank=True, max_length=160)),
                ("credits_snapshot", models.PositiveIntegerField()),
                ("amount_minor", models.PositiveBigIntegerField()),
                ("currency", models.CharField(default="CLP", max_length=3)),
                ("active", models.BooleanField(db_index=True, default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("offer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="provider_products", to="billing.creditpackoffer")),
            ],
        ),
        migrations.CreateModel(
            name="CreditPackPurchase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[("paddle", "Paddle"), ("mercado_pago", "Mercado Pago"), ("apple_app_store", "Apple App Store"), ("google_play", "Google Play")], max_length=32)),
                ("external_purchase_id", models.CharField(max_length=160)),
                ("status", models.CharField(choices=[("approved", "Approved"), ("refunded", "Refunded")], default="approved", max_length=16)),
                ("credits_granted", models.PositiveIntegerField()),
                ("evidence", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="credit_pack_purchases", to=settings.AUTH_USER_MODEL)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="purchases", to="billing.providercreditpack")),
            ],
        ),
        migrations.AddConstraint(
            model_name="providercreditpack",
            constraint=models.UniqueConstraint(fields=("provider", "environment", "external_product_id", "external_price_id"), name="pack_product_provider_external_uq"),
        ),
        migrations.AddConstraint(
            model_name="providercreditpack",
            constraint=models.UniqueConstraint(condition=models.Q(active=True), fields=("provider", "environment", "offer"), name="pack_product_active_offer_uq"),
        ),
        migrations.AddConstraint(
            model_name="creditpackpurchase",
            constraint=models.UniqueConstraint(fields=("provider", "external_purchase_id"), name="pack_purchase_provider_id_uq"),
        ),
        migrations.RunPython(seed_credit_packs, migrations.RunPython.noop),
    ]
