from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("billing", "0006_credit_packs")]

    operations = [
        migrations.RemoveConstraint(model_name="billingproduct", name="billprod_provider_env_price_uq"),
        migrations.AddConstraint(
            model_name="billingproduct",
            constraint=models.UniqueConstraint(
                fields=("provider", "environment", "external_product_id", "external_price_id"),
                condition=~models.Q(external_price_id=""),
                name="billprod_provider_env_price_uq",
            ),
        ),
    ]
