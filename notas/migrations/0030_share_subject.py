# Generated manually for My Scoope share inbox subject.

from django.db import migrations, models


def backfill_share_subjects(apps, schema_editor):
    DailyPlanShare = apps.get_model("notas", "DailyPlanShare")
    MealShare = apps.get_model("notas", "MealShare")

    for share in DailyPlanShare.objects.select_related("dailyplan").filter(subject=""):
        if share.dailyplan_id and share.dailyplan:
            share.subject = share.dailyplan.name
            share.save(update_fields=["subject"])

    for share in MealShare.objects.select_related("meal").filter(subject=""):
        if share.meal_id and share.meal:
            share.subject = share.meal.name
            share.save(update_fields=["subject"])


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0029_share_messages_read_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailyplanshare",
            name="subject",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="mealshare",
            name="subject",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.RunPython(backfill_share_subjects, migrations.RunPython.noop),
    ]
