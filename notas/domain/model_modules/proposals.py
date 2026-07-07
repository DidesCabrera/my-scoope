from django.db import models
from django.contrib.auth.models import User


# ==================================================
# AI NUTRITION CHATS
# ==================================================

class AiNutritionChat(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_PROPOSAL_CREATED = "proposal_created"

    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Activo"),
        (STATUS_PROPOSAL_CREATED, "Propuesta creada"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ai_nutrition_chats",
    )

    title = models.CharField(max_length=140)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )

    brief_payload = models.JSONField(default=dict, blank=True)
    conversation_payload = models.JSONField(default=dict, blank=True)
    last_message_preview = models.CharField(max_length=220, blank=True)

    proposal = models.ForeignKey(
        "NutritionProposal",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_ai_chats",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return self.title


# ==================================================
# NUTRITION PROPOSALS
# ==================================================

class NutritionProposal(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PENDING_REVIEW = "pending_review"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELLED = "cancelled"
    STATUS_APPLIED = "applied"

    STATUS_CHOICES = (
        (STATUS_PENDING_REVIEW, "Pendiente"),
        (STATUS_REJECTED, "Rechazada"),
        (STATUS_APPLIED, "Aplicada"),
    )

    SOURCE_MANUAL = "manual"
    SOURCE_AI = "ai"
    SOURCE_SYSTEM = "system"
    SOURCE_MCP = "mcp"

    SOURCE_CHOICES = (
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_AI, "AI"),
        (SOURCE_SYSTEM, "System"),
        (SOURCE_MCP, "MCP"),
    )

    dailyplan = models.ForeignKey(
        "DailyPlan",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="nutrition_proposals",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="nutrition_proposals_created",
    )

    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="nutrition_proposals_reviewed",
    )

    applied_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="nutrition_proposals_applied",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING_REVIEW,
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
    )

    title = models.CharField(max_length=160)
    summary = models.TextField(blank=True)
    list_order = models.PositiveIntegerField(default=0)
    is_read = models.BooleanField(default=False)

    targets = models.JSONField(default=dict, blank=True)
    current_snapshot = models.JSONField(default=dict, blank=True)
    proposed_payload = models.JSONField(default=dict, blank=True)
    validation_summary = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.title} ({self.status})"

    @property
    def is_reviewable(self):
        return self.status == self.STATUS_PENDING_REVIEW

    @property
    def is_final(self):
        return self.status in {
            self.STATUS_REJECTED,
            self.STATUS_CANCELLED,
            self.STATUS_APPLIED,
        }



class NutritionProposalAuditEvent(models.Model):
    ACTION_CREATED = "created"
    ACTION_SUBMITTED_FOR_REVIEW = "submitted_for_review"
    ACTION_APPROVED = "approved"
    ACTION_REJECTED = "rejected"
    ACTION_CANCELLED = "cancelled"
    ACTION_APPLIED = "applied"

    ACTION_CHOICES = (
        (ACTION_CREATED, "Created"),
        (ACTION_SUBMITTED_FOR_REVIEW, "Submitted for review"),
        (ACTION_APPROVED, "Approved"),
        (ACTION_REJECTED, "Rejected"),
        (ACTION_CANCELLED, "Cancelled"),
        (ACTION_APPLIED, "Applied"),
    )

    proposal = models.ForeignKey(
        "NutritionProposal",
        on_delete=models.CASCADE,
        related_name="audit_events",
    )

    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="nutrition_proposal_audit_events",
    )

    action = models.CharField(
        max_length=40,
        choices=ACTION_CHOICES,
    )

    status_before = models.CharField(
        max_length=30,
        blank=True,
    )

    status_after = models.CharField(
        max_length=30,
        blank=True,
    )

    message = models.TextField(blank=True)

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.proposal_id} - {self.action}"
