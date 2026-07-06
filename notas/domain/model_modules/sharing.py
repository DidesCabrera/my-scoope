import uuid

from django.db import models
from django.contrib.auth.models import User


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
