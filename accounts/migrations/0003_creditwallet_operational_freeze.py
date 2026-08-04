from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_creditwallet_creditledger"),
    ]

    operations = [
        migrations.AddField(
            model_name="creditwallet",
            name="is_frozen",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Operational account-level block for commercial credit consumption.",
            ),
        ),
        migrations.AddField(
            model_name="creditwallet",
            name="frozen_reason",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="creditwallet",
            name="frozen_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
