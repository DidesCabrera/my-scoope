from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction

from notas.domain.models import DailyPlan, DailyPlanShare, Meal, MealShare


@dataclass(frozen=True)
class DailyPlanShareCreateResult:
    share: DailyPlanShare
    created: bool


@dataclass(frozen=True)
class DailyPlanShareAcceptResult:
    share: DailyPlanShare


@dataclass(frozen=True)
class DailyPlanShareDismissResult:
    share: DailyPlanShare


@dataclass(frozen=True)
class DailyPlanShareRemoveResult:
    share: DailyPlanShare


@dataclass(frozen=True)
class MealShareCreateResult:
    share: MealShare
    created: bool


@dataclass(frozen=True)
class MealShareAcceptResult:
    share: MealShare


@dataclass(frozen=True)
class MealShareDismissResult:
    share: MealShare


@dataclass(frozen=True)
class MealShareRemoveResult:
    share: MealShare


def _find_recipient_user_by_email(email: str):
    if not email:
        return None

    User = get_user_model()
    return (
        User.objects
        .filter(email__iexact=email.strip())
        .order_by("id")
        .first()
    )


def _share_delivery_fields_for_email(email: str):
    recipient_user = _find_recipient_user_by_email(email)
    if recipient_user is None:
        return {}

    return {
        "accepted_by": recipient_user,
        "dismissed": False,
        "removed": False,
    }


def _clean_share_message(message: str | None) -> str:
    return (message or "").strip()


def _clean_share_subject(subject: str | None, fallback: str) -> str:
    clean_subject = (subject or "").strip()
    return clean_subject or fallback


@transaction.atomic
def create_dailyplan_share(
    *,
    sender,
    dailyplan: DailyPlan,
    recipient_email: str,
    subject: str | None = None,
    message: str | None = None,
) -> DailyPlanShareCreateResult:
    clean_email = (recipient_email or "").strip().lower()
    clean_message = _clean_share_message(message)
    clean_subject = _clean_share_subject(subject, dailyplan.name)

    if not clean_email:
        raise ValueError("recipient_email_required")

    delivery_defaults = _share_delivery_fields_for_email(clean_email)
    defaults = {
        **delivery_defaults,
        "message": clean_message,
        "subject": clean_subject,
        "is_read": False,
    }

    share, created = DailyPlanShare.objects.get_or_create(
        sender=sender,
        recipient_email=clean_email,
        dailyplan=dailyplan,
        defaults=defaults,
    )

    update_fields = []

    recipient_user = delivery_defaults.get("accepted_by")
    if recipient_user is not None and share.accepted_by_id != recipient_user.id:
        share.accepted_by = recipient_user
        update_fields.append("accepted_by")

    if share.message != clean_message:
        share.message = clean_message
        update_fields.append("message")

    if share.subject != clean_subject:
        share.subject = clean_subject
        update_fields.append("subject")

    if share.is_read:
        share.is_read = False
        update_fields.append("is_read")

    if share.removed:
        share.removed = False
        update_fields.append("removed")

    if share.dismissed:
        share.dismissed = False
        update_fields.append("dismissed")

    if update_fields:
        share.save(update_fields=update_fields)

    return DailyPlanShareCreateResult(
        share=share,
        created=created,
    )


@transaction.atomic
def accept_dailyplan_share(
    *,
    share: DailyPlanShare,
    user,
) -> DailyPlanShareAcceptResult:
    share.accepted_by = user
    share.dismissed = False
    share.removed = False
    share.is_read = False
    share.save(
        update_fields=[
            "accepted_by",
            "dismissed",
            "removed",
            "is_read",
        ]
    )

    return DailyPlanShareAcceptResult(
        share=share,
    )


@transaction.atomic
def dismiss_dailyplan_share(
    *,
    share: DailyPlanShare,
) -> DailyPlanShareDismissResult:
    share.dismissed = True
    share.save(update_fields=["dismissed"])

    return DailyPlanShareDismissResult(
        share=share,
    )


@transaction.atomic
def remove_dailyplan_share(
    *,
    share: DailyPlanShare,
) -> DailyPlanShareRemoveResult:
    share.removed = True
    share.save(update_fields=["removed"])

    return DailyPlanShareRemoveResult(
        share=share,
    )


@transaction.atomic
def create_meal_share(
    *,
    sender,
    meal: Meal,
    recipient_email: str,
    subject: str | None = None,
    message: str | None = None,
) -> MealShareCreateResult:
    clean_email = (recipient_email or "").strip().lower()
    clean_message = _clean_share_message(message)
    clean_subject = _clean_share_subject(subject, meal.name)

    if not clean_email:
        raise ValueError("recipient_email_required")

    delivery_defaults = _share_delivery_fields_for_email(clean_email)
    defaults = {
        **delivery_defaults,
        "message": clean_message,
        "subject": clean_subject,
        "is_read": False,
    }

    share, created = MealShare.objects.get_or_create(
        sender=sender,
        recipient_email=clean_email,
        meal=meal,
        defaults=defaults,
    )

    update_fields = []

    recipient_user = delivery_defaults.get("accepted_by")
    if recipient_user is not None and share.accepted_by_id != recipient_user.id:
        share.accepted_by = recipient_user
        update_fields.append("accepted_by")

    if share.message != clean_message:
        share.message = clean_message
        update_fields.append("message")

    if share.subject != clean_subject:
        share.subject = clean_subject
        update_fields.append("subject")

    if share.is_read:
        share.is_read = False
        update_fields.append("is_read")

    if share.removed:
        share.removed = False
        update_fields.append("removed")

    if share.dismissed:
        share.dismissed = False
        update_fields.append("dismissed")

    if update_fields:
        share.save(update_fields=update_fields)

    return MealShareCreateResult(
        share=share,
        created=created,
    )


@transaction.atomic
def accept_meal_share(
    *,
    share: MealShare,
    user,
) -> MealShareAcceptResult:
    share.accepted_by = user
    share.dismissed = False
    share.removed = False
    share.is_read = False
    share.save(
        update_fields=[
            "accepted_by",
            "dismissed",
            "removed",
            "is_read",
        ]
    )

    return MealShareAcceptResult(
        share=share,
    )


@transaction.atomic
def dismiss_meal_share(
    *,
    share: MealShare,
) -> MealShareDismissResult:
    share.dismissed = True
    share.save(update_fields=["dismissed"])

    return MealShareDismissResult(
        share=share,
    )


@transaction.atomic
def remove_meal_share(
    *,
    share: MealShare,
) -> MealShareRemoveResult:
    share.removed = True
    share.save(update_fields=["removed"])

    return MealShareRemoveResult(
        share=share,
    )
