# Generated manually for AI nutrition onboarding proposal flow.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0037_savedcomparison_snapshot_payload"),
    ]

    operations = [
        migrations.AlterField(
            model_name="nutritionproposal",
            name="dailyplan",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="nutrition_proposals",
                to="notas.dailyplan",
            ),
        ),
    ]
