from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_accountdeletionrecord")]

    operations = [
        migrations.AddField(
            model_name="creditwallet",
            name="purchased_balance",
            field=models.PositiveIntegerField(default=0, help_text="Non-expiring purchased credits included in balance."),
        ),
        migrations.AddField(
            model_name="creditwallet",
            name="purchased_reserved_balance",
            field=models.PositiveIntegerField(default=0, help_text="Reserved portion drawn from purchased credits."),
        ),
    ]
