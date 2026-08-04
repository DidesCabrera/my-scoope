# Generated manually for Proposal Layer MVP.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0013_backfill_mealfood_order"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NutritionProposal",
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
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("pending_review", "Pending review"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending_review",
                        max_length=30,
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("manual", "Manual"),
                            ("ai", "AI"),
                            ("system", "System"),
                            ("mcp", "MCP"),
                        ],
                        default="manual",
                        max_length=20,
                    ),
                ),
                (
                    "title",
                    models.CharField(max_length=160),
                ),
                (
                    "summary",
                    models.TextField(blank=True),
                ),
                (
                    "targets",
                    models.JSONField(
                        blank=True,
                        default=dict,
                    ),
                ),
                (
                    "current_snapshot",
                    models.JSONField(
                        blank=True,
                        default=dict,
                    ),
                ),
                (
                    "proposed_payload",
                    models.JSONField(
                        blank=True,
                        default=dict,
                    ),
                ),
                (
                    "validation_summary",
                    models.JSONField(
                        blank=True,
                        default=dict,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "reviewed_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nutrition_proposals_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "dailyplan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nutrition_proposals",
                        to="notas.dailyplan",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="nutrition_proposals_reviewed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]