import uuid

from django.contrib.auth.models import User
from django.db import models


class ShareResource(models.Model):
    class SubjectType(models.TextChoices):
        DAILY_PLAN = "daily_plan", "Daily plan"
        FOOD = "food", "Food"
        MEAL = "meal", "Meal"
        PROGRAM = "program", "Program"

    class Visibility(models.TextChoices):
        UNLISTED = "unlisted", "Unlisted"

    class ClaimPolicy(models.TextChoices):
        NONE = "none", "No claims"
        SINGLE = "single", "Single claim"
        MULTIPLE = "multiple", "Multiple claims"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="share_resources_sent")
    subject_type = models.CharField(max_length=24, choices=SubjectType.choices)
    source_object_id = models.PositiveBigIntegerField(null=True, blank=True)
    legacy_reference = models.CharField(max_length=64, null=True, blank=True, unique=True)
    snapshot = models.JSONField(default=dict)
    snapshot_schema_version = models.CharField(max_length=48)
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.UNLISTED)
    claim_policy = models.CharField(max_length=16, choices=ClaimPolicy.choices, default=ClaimPolicy.MULTIPLE)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=("sender", "status"), name="share_res_sender_status_idx"),
            models.Index(fields=("subject_type", "source_object_id"), name="share_res_subject_idx"),
        ]


class ShareInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"
        CLAIMED = "claimed", "Claimed"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    resource = models.ForeignKey(ShareResource, on_delete=models.CASCADE, related_name="invitations")
    recipient_email = models.EmailField()
    recipient_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="share_invitations_received"
    )
    subject = models.CharField(max_length=160, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    delivered_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("resource", "recipient_email"), name="share_invite_resource_email_uniq")
        ]


class ShareClaim(models.Model):
    class Source(models.TextChoices):
        EMAIL = "email", "Email"
        LINK = "link", "Link"

    resource = models.ForeignKey(ShareResource, on_delete=models.CASCADE, related_name="claims")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="share_claims")
    invitation = models.ForeignKey(
        ShareInvitation, null=True, blank=True, on_delete=models.SET_NULL, related_name="claims"
    )
    source = models.CharField(max_length=16, choices=Source.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("resource", "user"), name="share_claim_resource_user_uniq")
        ]


class InboxItem(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sharing_inbox_items")
    resource = models.ForeignKey(ShareResource, on_delete=models.CASCADE, related_name="inbox_items")
    claim = models.OneToOneField(ShareClaim, on_delete=models.CASCADE, related_name="inbox_item")
    read_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    saved_at = models.DateTimeField(null=True, blank=True)
    saved_subject_type = models.CharField(max_length=24, blank=True)
    saved_object_id = models.PositiveBigIntegerField(null=True, blank=True)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("owner", "resource"), name="inbox_owner_resource_uniq")
        ]


class DailyPlanShare(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="dailyplan_shares_sent"
    )

    recipient_email = models.EmailField()

    dailyplan = models.ForeignKey(
        "DailyPlan",
        on_delete=models.CASCADE,
        related_name="shares"
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True)

    accepted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dailyplan_shares_received"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    
    dismissed = models.BooleanField(default=False)      # inbox
    removed = models.BooleanField(default=False)        # librería
    is_favorite = models.BooleanField(default=False)    # inbox
    is_read = models.BooleanField(default=False)        # inbox
    message = models.TextField(blank=True)              # inbox / email
    subject = models.CharField(max_length=160, blank=True)  # inbox title / email subject

    class Meta:
        unique_together = ("recipient_email", "dailyplan")

    def __str__(self):
        return f"{self.sender} shared {self.dailyplan} → {self.recipient_email}"


class ProgramShare(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="program_shares_sent"
    )

    recipient_email = models.EmailField()

    program = models.ForeignKey(
        "Program",
        on_delete=models.CASCADE,
        related_name="shares"
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True)

    accepted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="program_shares_received"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    dismissed = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    message = models.TextField(blank=True)
    subject = models.CharField(max_length=160, blank=True)

    class Meta:
        unique_together = ("recipient_email", "program")

    def __str__(self):
        return f"{self.sender} shared {self.program} → {self.recipient_email}"


class MealShare(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="meal_shares_sent"
    )

    recipient_email = models.EmailField()

    meal = models.ForeignKey(
        "Meal",
        on_delete=models.CASCADE,
        related_name="shares"
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True)

    accepted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="meal_shares_received"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    
    dismissed = models.BooleanField(default=False)      # inbox
    removed = models.BooleanField(default=False)        # librería
    is_favorite = models.BooleanField(default=False)    # inbox
    is_read = models.BooleanField(default=False)        # inbox
    message = models.TextField(blank=True)              # inbox / email
    subject = models.CharField(max_length=160, blank=True)  # inbox title / email subject

    class Meta:
        unique_together = ("recipient_email", "meal")

    def __str__(self):
        return f"{self.sender} shared {self.meal} → {self.recipient_email}"

class FoodShare(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="food_shares_sent"
    )

    recipient_email = models.EmailField()

    food = models.ForeignKey(
        "Food",
        on_delete=models.CASCADE,
        related_name="shares"
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True)

    accepted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="food_shares_received"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    dismissed = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    message = models.TextField(blank=True)
    subject = models.CharField(max_length=160, blank=True)

    class Meta:
        unique_together = ("recipient_email", "food")

    def __str__(self):
        return f"{self.sender} shared {self.food} → {self.recipient_email}"


class DailyPlanMealShare(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="dailyplanmeal_shares_sent"
    )

    recipient_email = models.EmailField()

    dailyplan_meal = models.ForeignKey(
        "DailyPlanMeal",
        on_delete=models.CASCADE,
        related_name="shares"
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True)

    accepted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dailyplanmeal_shares_received"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    dismissed = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    message = models.TextField(blank=True)
    subject = models.CharField(max_length=160, blank=True)

    class Meta:
        unique_together = ("recipient_email", "dailyplan_meal")

    def __str__(self):
        return f"{self.sender} shared {self.dailyplan_meal} → {self.recipient_email}"
