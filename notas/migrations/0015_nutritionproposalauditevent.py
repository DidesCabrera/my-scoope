# Generated manually for Proposal Layer audit trail.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notas", "0014_nutritionproposal"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NutritionProposalAuditEvent",
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
                    "action",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            (
                                "submitted_for_review",
                                "Submitted for review",
                            ),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("cancelled", "Cancelled"),
                        ],
                        max_length=40,
                    ),
                ),
                (
                    "status_before",
                    models.CharField(
                        blank=True,
                        max_length=30,
                    ),
                ),
                (
                    "status_after",
                    models.CharField(
                        blank=True,
                        max_length=30,
                    ),
                ),
                (
                    "message",
                    models.TextField(
                        blank=True,
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                    ),
                ),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="nutrition_proposal_audit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "proposal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_events",
                        to="notas.nutritionproposal",
                    ),
                ),
            ],
            options={
                "ordering": [
                    "created_at",
                    "id",
                ],
            },
        ),
    ]