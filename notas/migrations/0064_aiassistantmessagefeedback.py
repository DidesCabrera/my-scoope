import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("notas", "0063_nutrition_preference_profile"),
    ]

    operations = [
        migrations.CreateModel(
            name="AiAssistantMessageFeedback",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("message_index", models.PositiveIntegerField()),
                (
                    "rating",
                    models.CharField(
                        choices=[("helpful", "Útil"), ("not_helpful", "No útil")],
                        max_length=20,
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("inaccurate", "Información incorrecta"),
                            ("ignored_context", "Ignoró el contexto"),
                            ("wrong_action", "Acción incorrecta"),
                            ("unclear", "Respuesta poco clara"),
                            ("too_verbose", "Respuesta demasiado extensa"),
                            ("other", "Otro"),
                        ],
                        max_length=30,
                    ),
                ),
                ("comment", models.CharField(blank=True, max_length=500)),
                ("response_fingerprint", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "chat",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="message_feedback",
                        to="notas.ainutritionchat",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_assistant_message_feedback",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-updated_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="aiassistantmessagefeedback",
            constraint=models.UniqueConstraint(
                fields=("user", "chat", "message_index"),
                name="unique_ai_message_feedback_per_user",
            ),
        ),
        migrations.AddIndex(
            model_name="aiassistantmessagefeedback",
            index=models.Index(
                fields=["rating", "created_at"],
                name="ai_feedback_rating_created_idx",
            ),
        ),
    ]
