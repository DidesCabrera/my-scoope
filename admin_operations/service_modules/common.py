from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist

from admin_operations.models import AdminOperationAuditEvent
from admin_operations.viewmodels import (
    AdminOperationsWarningVM,
)


@dataclass(frozen=True)
class AdminOperationResult:
    ok: bool
    message: str


class AdminOperationTargetNotFound(LookupError):
    """Raised when an application operation cannot resolve its target."""


def _get_operation_target(model_or_queryset, **lookup):
    queryset = (
        model_or_queryset._default_manager.all()
        if hasattr(model_or_queryset, "_default_manager")
        else model_or_queryset
    )
    try:
        return queryset.get(**lookup)
    except ObjectDoesNotExist as exc:
        raise AdminOperationTargetNotFound(str(exc)) from exc


def _actor_label(actor) -> str:
    return getattr(actor, "email", "") or getattr(actor, "username", "staff") or "staff"


def _user_label(user) -> str:
    full_name = (getattr(user, "get_full_name", lambda: "")() or "").strip()
    return full_name or getattr(user, "email", "") or getattr(user, "username", "") or f"User #{user.pk}"


def record_admin_operation_audit_event(
    *,
    actor,
    action: str,
    target,
    reason: str,
    status_before: str = "",
    status_after: str = "",
    metadata: dict | None = None,
) -> AdminOperationAuditEvent:
    target_meta = getattr(target, "_meta", None)
    target_label = str(target)[:220] if target is not None else ""
    return AdminOperationAuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        actor_label=_actor_label(actor),
        action=action,
        source="OPS06",
        target_app=getattr(target_meta, "app_label", "unknown"),
        target_model=getattr(target_meta, "model_name", target.__class__.__name__ if target is not None else "unknown"),
        target_id=str(getattr(target, "pk", "")),
        target_label=target_label,
        status_before=str(status_before or ""),
        status_after=str(status_after or ""),
        reason=(reason or "").strip(),
        metadata=metadata or {},
    )


def _format_int(value) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def _format_decimal(value: Decimal | None, *, suffix: str = "") -> str:
    if value is None:
        return "—"
    rendered = format(Decimal(value), "f").rstrip("0").rstrip(".") or "0"
    return f"{rendered}{suffix}"


def _queue_priority(count: int, *, warning_threshold: int = 1) -> str:
    return "warning" if int(count or 0) >= warning_threshold else "healthy"


def _warning_to_vm(warning: dict) -> AdminOperationsWarningVM:
    return AdminOperationsWarningVM(
        title=warning["title"],
        domain=warning["domain"],
        description=warning["description"],
        value=_format_int(warning["value"]),
        severity=warning.get("severity", "info"),
    )




__all__ = [
    "AdminOperationResult",
    "AdminOperationTargetNotFound",
    "record_admin_operation_audit_event",
]
