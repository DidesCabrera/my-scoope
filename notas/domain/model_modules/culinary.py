"""Operational culinary library. Public curation never exposes client proposals."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class CulinaryTemplate(models.Model):
    key = models.SlugField(max_length=100)
    version = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=150)
    family = models.SlugField(max_length=100)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    meal_kinds = models.JSONField(default=list)
    # Components define bounded ingredient substitutions, not unrestricted macro roles.
    rules = models.JSONField(default=dict)
    preparation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["key", "version"], name="culinary_template_version_unique")]

    def __str__(self):
        return f"{self.name} · v{self.version}"


class CulinaryVariant(models.Model):
    CANDIDATE = "candidate"
    RULE_VALIDATED = "rule_validated"
    HUMAN_VALIDATED = "human_validated"
    STATUS_CHOICES = [(CANDIDATE, "Candidata"), (RULE_VALIDATED, "Validada por reglas; revisión humana pendiente"),
                      (HUMAN_VALIDATED, "Validada por una persona")]
    template = models.ForeignKey(CulinaryTemplate, on_delete=models.PROTECT, related_name="variants")
    key = models.SlugField(max_length=120)
    version = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=150)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT)
    ingredients = models.JSONField(default=list)
    preparation = models.TextField()
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=CANDIDATE)
    rubric = models.JSONField(default=dict)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    evidence_digest = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["template", "key", "version"], name="culinary_variant_version_unique")]

    def clean(self):
        if self.status == self.HUMAN_VALIDATED and not (self.reviewed_by_id and self.reviewed_at):
            raise ValidationError("La validación humana requiere autor y fecha.")
        if self.pk:
            previous = type(self).objects.get(pk=self.pk)
            if previous.status != self.CANDIDATE:
                immutable = ("template_id", "ingredients", "preparation", "key", "version", "name")
                if any(getattr(previous, field) != getattr(self, field) for field in immutable):
                    raise ValidationError("Crea una nueva versión para modificar una variante validada.")

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} · v{self.version}"
