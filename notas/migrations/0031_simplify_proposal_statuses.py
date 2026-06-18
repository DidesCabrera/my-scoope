from django.db import migrations, models


def simplify_existing_statuses(apps, schema_editor):
    NutritionProposal = apps.get_model("notas", "NutritionProposal")
    NutritionProposal.objects.filter(status="approved", applied_at__isnull=True).update(status="pending_review")
    NutritionProposal.objects.filter(status="cancelled").update(status="rejected")


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0030_share_subject"),
    ]

    operations = [
        migrations.RunPython(simplify_existing_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="nutritionproposal",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending_review", "Pendiente"),
                    ("rejected", "Rechazada"),
                    ("applied", "Aplicada"),
                ],
                default="pending_review",
                max_length=30,
            ),
        ),
    ]
