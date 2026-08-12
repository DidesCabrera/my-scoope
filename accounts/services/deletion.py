from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from accounts.models import AccountDeletionRecord

POLICY_VERSION = "account-deletion.v1"


class RetentionAction(StrEnum):
    ERASE = "erase"
    ANONYMIZE = "anonymize"
    RETAIN_LEGAL = "retain_legal"
    RETAIN_OPERATIONAL = "retain_operational"
    RETAIN_SYSTEM = "retain_system"
    FOLLOW_PARENT = "follow_parent"


MODEL_RETENTION_POLICY = {
    "account.EmailAddress": RetentionAction.ERASE,
    "account.EmailConfirmation": RetentionAction.ERASE,
    "accounts.AccountDeletionRecord": RetentionAction.RETAIN_OPERATIONAL,
    "accounts.AccountPlan": RetentionAction.RETAIN_SYSTEM,
    "accounts.AccountSubscription": RetentionAction.ERASE,
    "accounts.CreditLedger": RetentionAction.ERASE,
    "accounts.CreditWallet": RetentionAction.ERASE,
    "admin.LogEntry": RetentionAction.ANONYMIZE,
    "admin_operations.AdminOperationAuditEvent": RetentionAction.ANONYMIZE,
    "ai_assistant.AIAsyncJob": RetentionAction.ERASE,
    "ai_assistant.AICreditLedger": RetentionAction.ERASE,
    "ai_assistant.AIPreparedAction": RetentionAction.ERASE,
    "ai_assistant.AIUsageEvent": RetentionAction.ANONYMIZE,
    "ai_assistant.AIUserCreditQuota": RetentionAction.ERASE,
    "auth.Group": RetentionAction.RETAIN_SYSTEM,
    "auth.Permission": RetentionAction.RETAIN_SYSTEM,
    "auth.User": RetentionAction.ANONYMIZE,
    "billing.BillingEvent": RetentionAction.RETAIN_LEGAL,
    "billing.BillingPayment": RetentionAction.RETAIN_LEGAL,
    "billing.BillingProduct": RetentionAction.RETAIN_SYSTEM,
    "billing.AppleAppAccountToken": RetentionAction.RETAIN_LEGAL,
    "billing.ProviderSubscription": RetentionAction.RETAIN_LEGAL,
    "billing.TaxDocument": RetentionAction.RETAIN_LEGAL,
    "contenttypes.ContentType": RetentionAction.RETAIN_SYSTEM,
    "email_delivery.EmailDeliveryAttempt": RetentionAction.ANONYMIZE,
    "food_catalog.CatalogCurationCandidate": RetentionAction.ANONYMIZE,
    "food_catalog.CatalogCapabilityDefinition": RetentionAction.RETAIN_SYSTEM,
    "food_catalog.CatalogClientRequirement": RetentionAction.RETAIN_SYSTEM,
    "food_catalog.CatalogEnrichmentBatch": RetentionAction.RETAIN_OPERATIONAL,
    "food_catalog.CatalogEnrichmentChange": RetentionAction.RETAIN_OPERATIONAL,
    "food_catalog.CatalogFieldProposal": RetentionAction.RETAIN_OPERATIONAL,
    "food_catalog.CatalogFood": RetentionAction.ANONYMIZE,
    "food_catalog.CatalogFoodAlias": RetentionAction.FOLLOW_PARENT,
    "food_catalog.CatalogFoodCapability": RetentionAction.RETAIN_OPERATIONAL,
    "food_catalog.CatalogFoodPortion": RetentionAction.FOLLOW_PARENT,
    "food_catalog.CatalogFoodSource": RetentionAction.FOLLOW_PARENT,
    "food_catalog.CatalogImportBatch": RetentionAction.ANONYMIZE,
    "food_catalog.CatalogImportSourcePolicy": RetentionAction.ANONYMIZE,
    "food_catalog.ExternalFoodReference": RetentionAction.FOLLOW_PARENT,
    "food_catalog.ExternalProviderFetchLog": RetentionAction.RETAIN_OPERATIONAL,
    "notas.AiNutritionChat": RetentionAction.ERASE,
    "notas.ApplePushSubscription": RetentionAction.ERASE,
    "notas.CalendarizedDay": RetentionAction.FOLLOW_PARENT,
    "notas.CalendarizedMealExecution": RetentionAction.FOLLOW_PARENT,
    "notas.CalendarizationMeasurementContext": RetentionAction.FOLLOW_PARENT,
    "notas.CalendarizationReview": RetentionAction.FOLLOW_PARENT,
    "notas.CalendarizationRevision": RetentionAction.FOLLOW_PARENT,
    "notas.DailyPlan": RetentionAction.ERASE,
    "notas.DailyPlanMeal": RetentionAction.FOLLOW_PARENT,
    "notas.DailyPlanMealShare": RetentionAction.ERASE,
    "notas.DailyPlanShare": RetentionAction.ERASE,
    "notas.Food": RetentionAction.ERASE,
    "notas.FoodAlias": RetentionAction.FOLLOW_PARENT,
    "notas.FoodImportBatch": RetentionAction.RETAIN_OPERATIONAL,
    "notas.FoodLabelCaptureReceipt": RetentionAction.FOLLOW_PARENT,
    "notas.FoodLocalizedName": RetentionAction.FOLLOW_PARENT,
    "notas.FoodPortion": RetentionAction.FOLLOW_PARENT,
    "notas.FoodShare": RetentionAction.ERASE,
    "notas.FoodSourceMetadata": RetentionAction.FOLLOW_PARENT,
    "notas.MCPUserToken": RetentionAction.ERASE,
    "notas.Meal": RetentionAction.ERASE,
    "notas.MealAccess": RetentionAction.ERASE,
    "notas.MealFood": RetentionAction.FOLLOW_PARENT,
    "notas.MealShare": RetentionAction.ERASE,
    "notas.NotificationDelivery": RetentionAction.FOLLOW_PARENT,
    "notas.NutritionProposal": RetentionAction.ERASE,
    "notas.NutritionProposalAuditEvent": RetentionAction.FOLLOW_PARENT,
    "notas.OAuthAuthorizationCode": RetentionAction.ERASE,
    "notas.OAuthClient": RetentionAction.RETAIN_SYSTEM,
    "notas.OAuthDeviceSession": RetentionAction.ERASE,
    "notas.OAuthRefreshToken": RetentionAction.FOLLOW_PARENT,
    "notas.Plan": RetentionAction.RETAIN_SYSTEM,
    "notas.Profile": RetentionAction.ERASE,
    "notas.Program": RetentionAction.ERASE,
    "notas.ProgramCalendarization": RetentionAction.ERASE,
    "notas.ProgramDay": RetentionAction.FOLLOW_PARENT,
    "notas.ProgramShare": RetentionAction.ERASE,
    "notas.SavedComparison": RetentionAction.ERASE,
    "notas.ScheduledNotificationEvent": RetentionAction.FOLLOW_PARENT,
    "notas.Subscription": RetentionAction.ERASE,
    "notas.WebPushSubscription": RetentionAction.ERASE,
    "notas.WeightLog": RetentionAction.ERASE,
    "sessions.Session": RetentionAction.ERASE,
    "sites.Site": RetentionAction.RETAIN_SYSTEM,
    "socialaccount.SocialAccount": RetentionAction.ERASE,
    "socialaccount.SocialApp": RetentionAction.RETAIN_SYSTEM,
    "socialaccount.SocialToken": RetentionAction.FOLLOW_PARENT,
}


@dataclass(frozen=True)
class AccountDeletionResult:
    receipt_id: uuid.UUID
    deleted_counts: dict[str, int]
    retained_counts: dict[str, int]


def _model(label: str):
    app_label, model_name = label.split(".", 1)
    return apps.get_model(app_label, model_name)


def _merge_deleted_counts(target: dict[str, int], details: dict[str, int]) -> None:
    for label, count in details.items():
        target[label] = target.get(label, 0) + count


def _delete_queryset(queryset, deleted_counts: dict[str, int]) -> None:
    _total, details = queryset.delete()
    _merge_deleted_counts(deleted_counts, details)


def _delete_user_sessions(user_id: int, deleted_counts: dict[str, int]) -> None:
    Session = _model("sessions.Session")
    session_keys = []
    for session in Session.objects.all().iterator():
        try:
            if str(session.get_decoded().get("_auth_user_id")) == str(user_id):
                session_keys.append(session.session_key)
        except Exception:
            continue
    if session_keys:
        _delete_queryset(Session.objects.filter(session_key__in=session_keys), deleted_counts)


@transaction.atomic
def delete_user_account(*, user, source: str) -> AccountDeletionResult:
    """Erase an account's personal data while retaining minimal financial evidence."""

    User = get_user_model()
    user = User.objects.select_for_update().get(pk=user.pk)
    receipt_id = uuid.uuid4()
    original_email = (user.email or "").strip()
    anonymous_email = f"deleted-{receipt_id.hex}@invalid.local"
    deleted_counts: dict[str, int] = {}

    ProviderSubscription = _model("billing.ProviderSubscription")
    BillingPayment = _model("billing.BillingPayment")
    TaxDocument = _model("billing.TaxDocument")
    retained_counts = {
        "billing.AppleAppAccountToken": _model("billing.AppleAppAccountToken").objects.filter(user=user).count(),
        "billing.ProviderSubscription": ProviderSubscription.objects.filter(user=user).count(),
        "billing.BillingPayment": BillingPayment.objects.filter(user=user).count(),
        "billing.TaxDocument": TaxDocument.objects.filter(payment__user=user).count(),
    }

    for label, fields in {
        "food_catalog.CatalogFood": ("created_by", "reviewed_by"),
        "food_catalog.CatalogCurationCandidate": ("created_by", "reviewed_by"),
        "food_catalog.CatalogImportBatch": ("requested_by",),
        "food_catalog.CatalogImportSourcePolicy": ("approved_by",),
        "food_catalog.CatalogFoodCapability": ("decided_by",),
        "food_catalog.CatalogEnrichmentBatch": ("requested_by", "applied_by"),
        "food_catalog.CatalogFieldProposal": ("reviewed_by",),
        "food_catalog.CatalogEnrichmentChange": ("actor",),
    }.items():
        model = _model(label)
        for field in fields:
            model.objects.filter(**{field: user}).update(**{field: None})

    _model("ai_assistant.AIUsageEvent").objects.filter(user=user).update(
        user=None,
        conversation_id="",
        turn_id="",
        usage_payload={},
        metadata={},
    )
    _model("admin.LogEntry").objects.filter(user=user).update(
        object_repr="[deleted account]",
        change_message="",
    )

    AdminAudit = _model("admin_operations.AdminOperationAuditEvent")
    AdminAudit.objects.filter(actor=user).update(actor=None, actor_label="[deleted account]", reason="", metadata={})
    AdminAudit.objects.filter(
        target_app="auth",
        target_model__iexact="user",
        target_id=str(user.pk),
    ).update(target_label="[deleted account]", reason="", metadata={})

    EmailAttempt = _model("email_delivery.EmailDeliveryAttempt")
    email_filter = Q(actor=user)
    if original_email:
        email_filter |= Q(recipient_email__iexact=original_email)
    EmailAttempt.objects.filter(email_filter).update(
        actor=None,
        recipient_email=anonymous_email,
        subject="",
        source_id="",
        idempotency_key=None,
        provider_message_id="",
    )

    for label, field in {
        "notas.Meal": "original_author",
        "notas.DailyPlan": "original_author",
        "notas.Program": "original_author",
        "notas.MealAccess": "granted_by",
        "notas.NutritionProposal": "reviewed_by",
        "notas.NutritionProposalAuditEvent": "actor",
    }.items():
        _model(label).objects.filter(**{field: user}).update(**{field: None})
    _model("notas.NutritionProposal").objects.filter(applied_by=user).update(applied_by=None)

    share_labels = (
        "notas.DailyPlanShare",
        "notas.ProgramShare",
        "notas.MealShare",
        "notas.FoodShare",
        "notas.DailyPlanMealShare",
    )
    for label in share_labels:
        share_model = _model(label)
        share_model.objects.filter(accepted_by=user).update(accepted_by=None)
        if original_email:
            share_model.objects.filter(recipient_email__iexact=original_email).update(recipient_email=anonymous_email)
        _delete_queryset(share_model.objects.filter(sender=user), deleted_counts)

    for label, filters in (
        ("notas.Subscription", Q(nutritionist=user) | Q(member=user)),
        ("notas.MealAccess", Q(user=user)),
        ("notas.NutritionProposal", Q(created_by=user)),
        ("notas.AiNutritionChat", Q(user=user)),
        ("notas.ProgramCalendarization", Q(user=user)),
        ("notas.Program", Q(created_by=user)),
        ("notas.DailyPlan", Q(created_by=user)),
        ("notas.Meal", Q(created_by=user)),
    ):
        _delete_queryset(_model(label).objects.filter(filters), deleted_counts)

    Food = _model("notas.Food")
    Food.objects.filter(created_by=user, is_global=True).update(created_by=None)
    _delete_queryset(Food.objects.filter(created_by=user, is_global=False), deleted_counts)

    for label, field in (
        ("notas.SavedComparison", "owner"),
        ("notas.MCPUserToken", "user"),
        ("notas.OAuthAuthorizationCode", "user"),
        ("notas.ApplePushSubscription", "user"),
        ("notas.OAuthDeviceSession", "user"),
        ("notas.WebPushSubscription", "user"),
        ("notas.WeightLog", "user"),
        ("notas.Profile", "user"),
        ("ai_assistant.AIAsyncJob", "user"),
        ("ai_assistant.AIPreparedAction", "user"),
        ("ai_assistant.AICreditLedger", "user"),
        ("ai_assistant.AIUserCreditQuota", "user"),
        ("accounts.AccountSubscription", "user"),
        ("accounts.CreditWallet", "user"),
        ("account.EmailAddress", "user"),
        ("socialaccount.SocialAccount", "user"),
    ):
        _delete_queryset(_model(label).objects.filter(**{field: user}), deleted_counts)

    _delete_user_sessions(user.pk, deleted_counts)

    user.groups.clear()
    user.user_permissions.clear()
    user.username = f"deleted-{receipt_id.hex}"
    user.email = ""
    user.first_name = ""
    user.last_name = ""
    user.is_active = False
    user.is_staff = False
    user.is_superuser = False
    user.last_login = None
    user.set_unusable_password()
    user.save(
        update_fields=(
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
            "password",
        )
    )

    AccountDeletionRecord.objects.create(
        public_id=receipt_id,
        policy_version=POLICY_VERSION,
        source=source,
        deleted_counts=deleted_counts,
        retained_counts=retained_counts,
    )
    return AccountDeletionResult(receipt_id, deleted_counts, retained_counts)
