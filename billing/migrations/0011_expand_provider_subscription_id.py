from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0010_googleplayaccounttoken"),
    ]

    operations = [
        migrations.AlterField(
            model_name="providersubscription",
            name="external_subscription_id",
            field=models.CharField(max_length=2048),
        ),
    ]
