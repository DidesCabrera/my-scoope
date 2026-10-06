from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0066_mobile_library_read_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="activity_level",
            field=models.CharField(blank=True, choices=[("sedentary", "Sedentaria"), ("light", "Ligera"), ("moderate", "Moderada"), ("high", "Alta"), ("very_high", "Muy alta")], default="", help_text="Habitual activity level used by the maintenance estimator.", max_length=24),
        ),
        migrations.AddField(
            model_name="profile",
            name="nutrition_goal",
            field=models.CharField(blank=True, choices=[("fat_loss", "Bajar grasa"), ("muscle_gain", "Ganar masa muscular"), ("maintenance", "Mantención"), ("performance", "Rendimiento deportivo"), ("healthy_eating", "Comer mejor")], default="", help_text="Persistent nutrition goal used as the default for planning.", max_length=32),
        ),
        migrations.AddField(
            model_name="profile",
            name="onboarding_plan_proposal_id",
            field=models.PositiveBigIntegerField(blank=True, help_text="Owned proposal identifier used to resume first-plan review without a cross-domain relation.", null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="onboarding_stage",
            field=models.CharField(choices=[("intro", "Introducción"), ("profile", "Ficha"), ("summary", "Resumen"), ("plan", "Primer plan"), ("plans", "Planes comerciales"), ("completed", "Completado")], default="intro", max_length=24),
        ),
        migrations.AddField(
            model_name="profile",
            name="training_frequency",
            field=models.PositiveSmallIntegerField(blank=True, help_text="Declared training sessions per week; persisted as planning context.", null=True, validators=[MinValueValidator(0), MaxValueValidator(7)]),
        ),
    ]
