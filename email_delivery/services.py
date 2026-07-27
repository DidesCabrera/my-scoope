from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from email_delivery.models import EmailDeliveryAttempt


@dataclass(frozen=True)
class EmailDeliveryResult:
    status: str
    sent: bool
    reason: str = ""
    attempt_id: int | None = None


def _normalized_email(value: str) -> str:
    return (value or "").strip().lower()


def _sender_has_verified_email(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    return EmailAddress.objects.filter(user=user, verified=True).exists()


def _record_suppressed_share(
    *,
    actor,
    recipient_email: str,
    subject: str,
    source_model: str,
    source_id: str,
    reason: str,
    idempotency_key: str | None,
) -> EmailDeliveryResult:
    try:
        attempt, _ = EmailDeliveryAttempt.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={
                "category": EmailDeliveryAttempt.CATEGORY_SHARE_INVITATION,
                "status": EmailDeliveryAttempt.STATUS_SUPPRESSED,
                "actor": actor,
                "recipient_email": recipient_email,
                "subject": subject,
                "source_model": source_model,
                "source_id": source_id,
                "reason": reason,
            },
        )
    except IntegrityError:
        attempt = EmailDeliveryAttempt.objects.get(idempotency_key=idempotency_key)
    return EmailDeliveryResult(
        status=attempt.status,
        sent=False,
        reason=reason,
        attempt_id=attempt.id,
    )


def _share_policy_reason(*, actor, recipient_email: str) -> str:
    if not getattr(settings, "EMAIL_SHARE_DELIVERY_ENABLED", True):
        return "delivery_disabled"
    if not _sender_has_verified_email(actor):
        return "sender_email_unverified"

    now = timezone.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    counted_statuses = (
        EmailDeliveryAttempt.STATUS_PENDING,
        EmailDeliveryAttempt.STATUS_SENT,
    )
    sent_today = EmailDeliveryAttempt.objects.filter(
        category=EmailDeliveryAttempt.CATEGORY_SHARE_INVITATION,
        status__in=counted_statuses,
        created_at__gte=start_of_day,
    )
    if sent_today.count() >= getattr(settings, "EMAIL_SHARE_DAILY_BUDGET", 70):
        return "global_daily_budget"
    if sent_today.filter(actor=actor).count() >= getattr(
        settings,
        "EMAIL_SHARE_USER_DAILY_LIMIT",
        20,
    ):
        return "user_daily_limit"
    if sent_today.filter(recipient_email=recipient_email).count() >= getattr(
        settings,
        "EMAIL_SHARE_RECIPIENT_DAILY_LIMIT",
        3,
    ):
        return "recipient_daily_limit"

    cooldown_seconds = getattr(settings, "EMAIL_SHARE_RECIPIENT_COOLDOWN_SECONDS", 600)
    if cooldown_seconds > 0 and sent_today.filter(
        actor=actor,
        recipient_email=recipient_email,
        created_at__gte=now - timedelta(seconds=cooldown_seconds),
    ).exists():
        return "recipient_cooldown"
    return ""


def deliver_share_invitation(
    *,
    share,
    subject: str,
    message: str,
    from_email: str,
) -> EmailDeliveryResult:
    actor = share.sender
    recipient_email = _normalized_email(share.recipient_email)
    source_model = share._meta.label_lower
    source_id = str(share.pk)
    idempotency_key = f"share:{source_model}:{source_id}:initial"

    if share.accepted_by_id:
        return _record_suppressed_share(
            actor=actor,
            recipient_email=recipient_email,
            subject=subject,
            source_model=source_model,
            source_id=source_id,
            reason="existing_recipient_inbox",
            idempotency_key=idempotency_key,
        )

    with transaction.atomic():
        type(actor).objects.select_for_update().get(pk=actor.pk)
        existing = EmailDeliveryAttempt.objects.filter(
            idempotency_key=idempotency_key
        ).first()
        if existing:
            return EmailDeliveryResult(
                status=existing.status,
                sent=False,
                reason="duplicate_share",
                attempt_id=existing.id,
            )

        reason = _share_policy_reason(
            actor=actor,
            recipient_email=recipient_email,
        )
        if reason:
            status = (
                EmailDeliveryAttempt.STATUS_RATE_LIMITED
                if reason.endswith("_limit") or reason == "global_daily_budget"
                else EmailDeliveryAttempt.STATUS_SUPPRESSED
            )
            policy_key = (
                f"share:{source_model}:{source_id}:policy:"
                f"{timezone.localdate().isoformat()}"
            )
            attempt, _ = EmailDeliveryAttempt.objects.get_or_create(
                idempotency_key=policy_key,
                defaults={
                    "category": EmailDeliveryAttempt.CATEGORY_SHARE_INVITATION,
                    "status": status,
                    "actor": actor,
                    "recipient_email": recipient_email,
                    "subject": subject,
                    "source_model": source_model,
                    "source_id": source_id,
                    "reason": reason,
                },
            )
            return EmailDeliveryResult(
                status=attempt.status,
                sent=False,
                reason=reason,
                attempt_id=attempt.id,
            )

        attempt = EmailDeliveryAttempt.objects.create(
            category=EmailDeliveryAttempt.CATEGORY_SHARE_INVITATION,
            status=EmailDeliveryAttempt.STATUS_PENDING,
            actor=actor,
            recipient_email=recipient_email,
            subject=subject,
            source_model=source_model,
            source_id=source_id,
            idempotency_key=idempotency_key,
        )

        try:
            sent = bool(
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=from_email,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
            )
        except Exception as exc:
            attempt.status = EmailDeliveryAttempt.STATUS_FAILED
            attempt.error_code = type(exc).__name__[:120]
            attempt.save(update_fields=["status", "error_code", "updated_at"])
            return EmailDeliveryResult(
                status=attempt.status,
                sent=False,
                reason="provider_error",
                attempt_id=attempt.id,
            )

        if sent:
            attempt.status = EmailDeliveryAttempt.STATUS_SENT
            attempt.sent_at = timezone.now()
            attempt.save(update_fields=["status", "sent_at", "updated_at"])
            return EmailDeliveryResult(
                status=attempt.status,
                sent=True,
                attempt_id=attempt.id,
            )

        attempt.status = EmailDeliveryAttempt.STATUS_FAILED
        attempt.reason = "provider_rejected"
        attempt.save(update_fields=["status", "reason", "updated_at"])
        return EmailDeliveryResult(
            status=attempt.status,
            sent=False,
            reason=attempt.reason,
            attempt_id=attempt.id,
        )


def deliver_account_message(
    *,
    category: str,
    recipient_email: str,
    message: EmailMessage,
    actor=None,
) -> EmailDeliveryResult:
    attempt = EmailDeliveryAttempt.objects.create(
        category=category,
        status=EmailDeliveryAttempt.STATUS_PENDING,
        actor=actor if getattr(actor, "pk", None) else None,
        recipient_email=_normalized_email(recipient_email),
        subject=message.subject[:255],
    )
    try:
        sent = bool(message.send(fail_silently=False))
    except Exception as exc:
        attempt.status = EmailDeliveryAttempt.STATUS_FAILED
        attempt.error_code = type(exc).__name__[:120]
        attempt.save(update_fields=["status", "error_code", "updated_at"])
        raise

    attempt.status = (
        EmailDeliveryAttempt.STATUS_SENT
        if sent
        else EmailDeliveryAttempt.STATUS_FAILED
    )
    if sent:
        attempt.sent_at = timezone.now()
    else:
        attempt.reason = "provider_rejected"
    attempt.save(
        update_fields=["status", "sent_at", "reason", "updated_at"]
    )
    return EmailDeliveryResult(
        status=attempt.status,
        sent=sent,
        reason=attempt.reason,
        attempt_id=attempt.id,
    )
