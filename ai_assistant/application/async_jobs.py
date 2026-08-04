from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Mapping

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.module_loading import import_string

from ai_assistant.infrastructure.job_signal import notify_job_available
from ai_assistant.models import AIAsyncJob

logger = logging.getLogger(__name__)


class AsyncJobContractError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid_async_job_request"):
        super().__init__(message)
        self.code = code


def async_jobs_enabled() -> bool:
    value = getattr(settings, "AI_ASSISTANT_ASYNC_ENABLED", False)
    return value is True or str(value).strip().lower() in {"1", "true", "yes", "on"}


def enqueue_async_job(
    *,
    user: Any,
    kind: str,
    idempotency_key: str,
    request_payload: Mapping[str, Any],
    lane_key: str = "",
    max_attempts: int | None = None,
) -> tuple[AIAsyncJob, bool]:
    normalized_kind = _required_text(kind, field="kind", max_length=80)
    normalized_key = _required_text(idempotency_key, field="idempotency_key", max_length=120)
    normalized_lane = " ".join(str(lane_key or "").split())[:160]
    if user is None or not getattr(user, "pk", None):
        raise AsyncJobContractError("A persisted user is required.")

    configured_attempts = max_attempts or getattr(settings, "AI_ASYNC_JOB_MAX_ATTEMPTS", 3)
    attempts = max(1, min(int(configured_attempts), 10))
    with transaction.atomic():
        job, created = AIAsyncJob.objects.get_or_create(
            user=user,
            kind=normalized_kind,
            idempotency_key=normalized_key,
            defaults={
                "lane_key": normalized_lane,
                "request_payload": dict(request_payload),
                "max_attempts": attempts,
            },
        )
        if not created and (
            dict(job.request_payload or {}) != dict(request_payload)
            or job.lane_key != normalized_lane
        ):
            raise AsyncJobContractError(
                "The idempotency key was already used with a different request.",
                code="idempotency_conflict",
            )
        if created:
            transaction.on_commit(lambda: notify_job_available(str(job.public_id)))
    return job, created


@transaction.atomic
def claim_next_async_job(*, lease_seconds: int | None = None) -> AIAsyncJob | None:
    now = timezone.now()
    lease_duration = max(
        30,
        min(
            int(lease_seconds or getattr(settings, "AI_ASYNC_JOB_LEASE_SECONDS", 180)),
            1800,
        ),
    )
    runnable = Q(
        status__in=(AIAsyncJob.Status.QUEUED, AIAsyncJob.Status.RETRYING),
        available_at__lte=now,
    ) | Q(
        status=AIAsyncJob.Status.RUNNING,
        lease_expires_at__lte=now,
    )
    queryset = AIAsyncJob.objects.filter(runnable).order_by("available_at", "created_at", "id")
    if connection.features.has_select_for_update_skip_locked:
        queryset = queryset.select_for_update(skip_locked=True)
    else:
        queryset = queryset.select_for_update()

    for job in queryset[:25]:
        if job.lane_key and AIAsyncJob.objects.filter(
            lane_key=job.lane_key,
            status=AIAsyncJob.Status.RUNNING,
            lease_expires_at__gt=now,
        ).exclude(pk=job.pk).exists():
            continue
        job.status = AIAsyncJob.Status.RUNNING
        job.attempts = int(job.attempts or 0) + 1
        job.leased_at = now
        job.lease_expires_at = now + timedelta(seconds=lease_duration)
        job.error_code = ""
        job.error_message = ""
        job.save(
            update_fields=[
                "status",
                "attempts",
                "leased_at",
                "lease_expires_at",
                "error_code",
                "error_message",
                "updated_at",
            ]
        )
        return job
    return None


def run_one_async_job() -> AIAsyncJob | None:
    job = claim_next_async_job()
    if job is None:
        return None
    try:
        handler = _resolve_handler(job.kind)
        result = handler(job=job)
        _mark_succeeded(job_id=job.pk, result=result)
    except Exception as exc:
        logger.exception("AI async job failed: kind=%s job=%s", job.kind, job.public_id)
        _mark_failed_or_retry(job_id=job.pk, exc=exc)
    return AIAsyncJob.objects.get(pk=job.pk)


def _resolve_handler(kind: str):
    handlers = getattr(settings, "AI_ASYNC_JOB_HANDLERS", {}) or {}
    path = handlers.get(kind) if isinstance(handlers, Mapping) else None
    if not path:
        raise AsyncJobContractError(f"No async handler is registered for {kind!r}.")
    return import_string(str(path))


@transaction.atomic
def _mark_succeeded(*, job_id: int, result: Any) -> None:
    job = AIAsyncJob.objects.select_for_update().get(pk=job_id)
    if job.status != AIAsyncJob.Status.RUNNING:
        return
    job.status = AIAsyncJob.Status.SUCCEEDED
    job.result_payload = dict(result or {})
    job.completed_at = timezone.now()
    job.lease_expires_at = None
    job.save(
        update_fields=[
            "status",
            "result_payload",
            "completed_at",
            "lease_expires_at",
            "updated_at",
        ]
    )


@transaction.atomic
def _mark_failed_or_retry(*, job_id: int, exc: Exception) -> None:
    job = AIAsyncJob.objects.select_for_update().get(pk=job_id)
    if job.status != AIAsyncJob.Status.RUNNING:
        return
    job.error_code = exc.__class__.__name__[:120]
    job.error_message = " ".join(str(exc or "Async job failed").split())[:500]
    job.lease_expires_at = None
    if job.attempts < job.max_attempts:
        job.status = AIAsyncJob.Status.RETRYING
        job.available_at = timezone.now() + timedelta(seconds=min(2 ** job.attempts, 60))
        update_fields = [
            "status",
            "available_at",
            "lease_expires_at",
            "error_code",
            "error_message",
            "updated_at",
        ]
        transaction.on_commit(lambda: notify_job_available(str(job.public_id)))
    else:
        job.status = AIAsyncJob.Status.FAILED
        job.completed_at = timezone.now()
        update_fields = [
            "status",
            "completed_at",
            "lease_expires_at",
            "error_code",
            "error_message",
            "updated_at",
        ]
    job.save(update_fields=update_fields)


def _required_text(value: Any, *, field: str, max_length: int) -> str:
    normalized = " ".join(str(value or "").split())[:max_length]
    if not normalized:
        raise AsyncJobContractError(f"{field} is required.")
    return normalized
