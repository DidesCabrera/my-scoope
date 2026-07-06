"""Saved comparison domain models.

This module is imported by ``notas.domain.models`` to keep the public Django
model import contract stable while reducing the size of the legacy model file.
"""

from django.contrib.auth.models import User
from django.db import models


class SavedComparison(models.Model):
    KIND_FOODS = "foods"
    KIND_MEALS = "meals"
    KIND_DAILYPLANS = "dailyplans"

    KIND_CHOICES = (
        (KIND_FOODS, "Alimentos"),
        (KIND_MEALS, "Comidas"),
        (KIND_DAILYPLANS, "Planes diarios"),
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="saved_comparisons",
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    name = models.CharField(max_length=160)
    payload = models.JSONField(default=list, blank=True)
    snapshot_payload = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["owner", "kind", "-updated_at"], name="savedcomp_owner_kind_idx"),
        ]

    def __str__(self):
        return self.name


__all__ = ["SavedComparison"]
