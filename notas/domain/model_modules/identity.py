from django.contrib.auth.models import User
from django.db import models


class Plan(models.Model):
    """Historical entitlement snapshot; commercial plans live in accounts."""

    ROLE_CHOICES = (
        ("member", "Member"),
        ("nutritionist", "Nutritionist"),
    )

    name = models.CharField(max_length=50)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    can_create_meal = models.BooleanField(default=False)
    can_create_dailyplan = models.BooleanField(default=False)
    can_create_program = models.BooleanField(default=False)
    can_publish = models.BooleanField(default=False)

    can_fork = models.BooleanField(default=True)
    can_copy = models.BooleanField(default=False)



    max_program_duration_days = models.PositiveIntegerField(null=True, blank=True)
    max_active_subscriptions = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.role})"


class Profile(models.Model):
    ROLE_CHOICES = (
        ("member", "Member"),
        ("nutritionist", "Nutritionist"),
    )

    SEX_FEMALE = "female"
    SEX_MALE = "male"
    SEX_CHOICES = (
        (SEX_FEMALE, "Female"),
        (SEX_MALE, "Male"),
    )

    ONBOARDING_VERSION_UNSET = 0
    ONBOARDING_VERSION_NUTRITION_V1 = 1

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_verified = models.BooleanField(default=False)

    birth_date = models.DateField(
        null=True,
        blank=True,
        help_text="Birth date used to calculate nutritional age dynamically.",
    )
    sex = models.CharField(
        max_length=20,
        choices=SEX_CHOICES,
        blank=True,
        default="",
        help_text="Sex value used by nutritional energy-estimation formulas.",
    )
    height_cm = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Height in centimeters captured by the nutrition onboarding.",
    )
    onboarding_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the required onboarding flow was completed.",
    )
    onboarding_version = models.PositiveSmallIntegerField(
        default=ONBOARDING_VERSION_UNSET,
        help_text="Latest onboarding version completed by the user.",
    )
    timezone_name = models.CharField(
        max_length=64,
        default="UTC",
        help_text="IANA timezone used as the default for user-local scheduling.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Subscription(models.Model):
    """Legacy name for a nutritionist/member care relationship.

    New code should use ``NutritionistMemberRelationship``. The concrete model
    remains temporarily for migration and import compatibility.
    """

    nutritionist = models.ForeignKey(
        User, related_name="subscriptions_received", on_delete=models.CASCADE
    )
    member = models.ForeignKey(
        User, related_name="subscriptions_made", on_delete=models.CASCADE
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("nutritionist", "member")

    def __str__(self):
        return f"{self.member} → {self.nutritionist}"


class NutritionistMemberRelationship(Subscription):
    """Unambiguous public façade over the historical Subscription table."""

    class Meta:
        proxy = True
        verbose_name = "nutritionist/member relationship"
        verbose_name_plural = "nutritionist/member relationships"







class WeightLog(models.Model):
    SOURCE_MANUAL = "manual"
    SOURCE_ONBOARDING = "onboarding"
    SOURCE_IMPORT = "import"
    SOURCE_CHOICES = (
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_ONBOARDING, "Onboarding"),
        (SOURCE_IMPORT, "Import"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="weight_logs"
    )

    date = models.DateField()
    weight_kg = models.FloatField()
    source = models.CharField(
        max_length=30,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
        blank=True,
        help_text="Origin of this body-weight metric entry.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        unique_together = ("user", "date")   # opcional: un registro por día

    def __str__(self):
        return f"{self.user.username} - {self.weight_kg} kg ({self.date})"
