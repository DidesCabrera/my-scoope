from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notas", "0042_profile_body_basics_and_weight_source")]

    operations = [
        migrations.AddField(
            model_name="food",
            name="solver_capabilities_version",
            field=models.CharField(
                default="solver_food_capabilities.v1",
                help_text="Version of the solver capability projection copied into this operational snapshot.",
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="food",
            name="solver_capabilities",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Operational, auditable capability values and confidence; never a live CatalogFood read.",
            ),
        ),
    ]
