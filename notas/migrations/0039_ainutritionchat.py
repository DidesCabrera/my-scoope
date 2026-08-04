# Generated manually for AI nutrition chat history.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("notas", "0038_alter_nutritionproposal_dailyplan_nullable"),
    ]

    operations = [
        migrations.CreateModel(
            name="AiNutritionChat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=140)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Activo"), ("proposal_created", "Propuesta creada")],
                        default="active",
                        max_length=30,
                    ),
                ),
                ("brief_payload", models.JSONField(blank=True, default=dict)),
                ("conversation_payload", models.JSONField(blank=True, default=dict)),
                ("last_message_preview", models.CharField(blank=True, max_length=220)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "proposal",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="source_ai_chats",
                        to="notas.nutritionproposal",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_nutrition_chats",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at", "-id"],
            },
        ),
    ]
