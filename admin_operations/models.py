from __future__ import annotations

from django.conf import settings
from django.db import models


class AdminOperationAuditEvent(models.Model):
    """Append-only audit event for staff actions executed from Admin Operations.

    The model intentionally stores target identifiers as plain fields instead of
    using a generic relation. Admin Operations spans several domains and the
    audit trail must survive future model moves or app-boundary refactors.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="admin_operation_audit_events",
    )
    actor_label = models.CharField(max_length=160, blank=True)
    action = models.CharField(max_length=120, db_index=True)
    source = models.CharField(max_length=20, default="OPS06", db_index=True)

    target_app = models.CharField(max_length=80, db_index=True)
    target_model = models.CharField(max_length=120, db_index=True)
    target_id = models.CharField(max_length=120, db_index=True)
    target_label = models.CharField(max_length=220, blank=True)

    status_before = models.CharField(max_length=120, blank=True)
    status_after = models.CharField(max_length=120, blank=True)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["target_app", "target_model", "target_id"], name="adm_ops_audit_target_idx"),
            models.Index(fields=["actor", "created_at"], name="adm_ops_audit_actor_idx"),
            models.Index(fields=["action", "created_at"], name="adm_ops_audit_action_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.action} · {self.target_app}.{self.target_model}#{self.target_id}"

    def save(self, *args, **kwargs):
        if self.pk and AdminOperationAuditEvent.objects.filter(pk=self.pk).exists():
            from django.core.exceptions import ValidationError

            raise ValidationError("AdminOperationAuditEvent entries are append-only and cannot be updated.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError

        raise ValidationError("AdminOperationAuditEvent entries are append-only and cannot be deleted.")
