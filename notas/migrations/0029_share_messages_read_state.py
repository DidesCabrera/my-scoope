# Generated manually for My Scoope share/inbox read state.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0028_share_favorites"),
    ]

    operations = [
        migrations.AddField(
            model_name="nutritionproposal",
            name="is_read",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="dailyplanshare",
            name="is_read",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="dailyplanshare",
            name="message",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="mealshare",
            name="is_read",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="mealshare",
            name="message",
            field=models.TextField(blank=True),
        ),
    ]
