"""Operational governance shared by every persistent Food Catalog source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from food_catalog.models import CatalogFood, CatalogImportBatch, CatalogImportSourcePolicy


DEFAULT_DRY_RUN_TTL = timedelta(hours=24)


def atomic_catalog_import(func):
    """Apply the persistence transaction without coupling application modules to Django."""

    return transaction.atomic(func)


class CatalogImportGovernanceError(ValueError):
    """Raised when a mutation is not backed by an equivalent valid dry-run."""


@dataclass(frozen=True)
class CatalogImportIdentity:
    source_type: str
    source_name: str
    source_version: str
    input_sha256: str
    parameters_payload: dict[str, Any]


def record_catalog_import_dry_run(
    *,
    identity: CatalogImportIdentity,
    total_rows: int,
    would_import_rows: int,
    skipped_rows: int,
    failed_rows: int,
    summary_payload: dict[str, Any] | None = None,
    requested_by=None,
    reason: str,
) -> CatalogImportBatch:
    """Persist a non-mutating result so a later apply can be authorized."""

    normalized_reason = reason.strip()
    if not normalized_reason:
        raise CatalogImportGovernanceError("A dry-run reason is required.")

    return CatalogImportBatch.objects.create(
        source_type=identity.source_type,
        source_name=identity.source_name,
        source_version=identity.source_version,
        status=CatalogImportBatch.STATUS_COMPLETED,
        is_dry_run=True,
        requested_by=_authenticated_user_or_none(requested_by),
        reason=normalized_reason,
        input_sha256=identity.input_sha256,
        parameters_payload=identity.parameters_payload,
        total_rows=total_rows,
        imported_rows=would_import_rows,
        skipped_rows=skipped_rows,
        failed_rows=failed_rows,
        summary_payload=summary_payload or {},
        finished_at=timezone.now(),
    )


@transaction.atomic
def start_catalog_import_batch(
    *,
    identity: CatalogImportIdentity,
    dry_run_batch: CatalogImportBatch,
    total_rows: int,
    requested_by=None,
    reason: str,
    notes: str = "",
    now=None,
    ttl: timedelta = DEFAULT_DRY_RUN_TTL,
) -> CatalogImportBatch:
    """Start a mutating batch only after verifying an equivalent fresh dry-run."""

    normalized_reason = reason.strip()
    if not normalized_reason:
        raise CatalogImportGovernanceError("An import reason is required.")
    if identity.source_type == CatalogFood.SOURCE_OPEN_FOOD_FACTS:
        raise CatalogImportGovernanceError(
            "Open Food Facts persistence is disabled: ODbL attribution/share-alike review has not approved a combined CatalogFood database."
        )
    _validate_source_scale(identity=identity, total_rows=total_rows)

    current_time = now or timezone.now()
    _validate_dry_run(
        dry_run_batch=dry_run_batch,
        identity=identity,
        total_rows=total_rows,
        now=current_time,
        ttl=ttl,
    )

    return CatalogImportBatch.objects.create(
        source_type=identity.source_type,
        source_name=identity.source_name,
        source_version=identity.source_version,
        status=CatalogImportBatch.STATUS_RUNNING,
        is_dry_run=False,
        dry_run_batch=dry_run_batch,
        requested_by=_authenticated_user_or_none(requested_by),
        reason=normalized_reason,
        input_sha256=identity.input_sha256,
        parameters_payload=identity.parameters_payload,
        total_rows=total_rows,
        notes=notes,
    )


def _validate_dry_run(
    *,
    dry_run_batch: CatalogImportBatch,
    identity: CatalogImportIdentity,
    total_rows: int,
    now,
    ttl: timedelta,
) -> None:
    if not dry_run_batch.is_dry_run:
        raise CatalogImportGovernanceError("The selected batch is not a dry-run.")
    if dry_run_batch.status != CatalogImportBatch.STATUS_COMPLETED:
        raise CatalogImportGovernanceError("The dry-run did not complete successfully.")
    if dry_run_batch.finished_at is None or dry_run_batch.finished_at < now - ttl:
        raise CatalogImportGovernanceError("The dry-run has expired.")

    expected = (
        identity.source_type,
        identity.source_name,
        identity.source_version,
        identity.input_sha256,
        identity.parameters_payload,
        total_rows,
    )
    actual = (
        dry_run_batch.source_type,
        dry_run_batch.source_name,
        dry_run_batch.source_version,
        dry_run_batch.input_sha256,
        dry_run_batch.parameters_payload,
        dry_run_batch.total_rows,
    )
    if actual != expected:
        raise CatalogImportGovernanceError(
            "The dry-run does not match the source, version, input, parameters and row count."
        )


def _validate_source_scale(*, identity: CatalogImportIdentity, total_rows: int) -> None:
    sample_limit = _sample_limit(identity)
    policy = CatalogImportSourcePolicy.objects.filter(
        source_type=identity.source_type,
        source_name=identity.source_name,
    ).first()
    if policy and (not policy.is_enabled or policy.kill_switch):
        raise CatalogImportGovernanceError("This catalog source is disabled by its kill switch policy.")
    if total_rows <= sample_limit:
        return
    if policy is None or not policy.scale_approved:
        raise CatalogImportGovernanceError(
            f"Batch exceeds the {sample_limit}-row sample gate and scaling is not approved."
        )
    if total_rows > policy.max_batch_rows:
        raise CatalogImportGovernanceError(
            f"Batch exceeds the approved maximum of {policy.max_batch_rows} rows."
        )
    successful_applies = CatalogImportBatch.objects.filter(
        source_type=identity.source_type,
        source_name=identity.source_name,
        is_dry_run=False,
        dry_run_batch__isnull=False,
        status=CatalogImportBatch.STATUS_COMPLETED,
        failed_rows=0,
    ).count()
    if successful_applies < 2:
        raise CatalogImportGovernanceError("Scaling requires two successful governed sample applies.")


def _sample_limit(identity: CatalogImportIdentity) -> int:
    if identity.source_type == CatalogFood.SOURCE_NATURAL_VERIFIED:
        return 30
    if identity.source_type == CatalogFood.SOURCE_USDA:
        return 10
    if identity.source_type == CatalogFood.SOURCE_BRAND_SUBMITTED:
        return 5
    if identity.source_name == "manual_evidence_intake":
        return 5
    if identity.source_name == "My Scoope operational foods":
        return 10
    return 10


def _authenticated_user_or_none(user):
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    return None


def catalog_import_identity(
    *,
    source_type: str,
    source_name: str,
    source_version: str,
    input_sha256: str,
    parameters_payload: dict[str, Any] | None = None,
) -> CatalogImportIdentity:
    if source_type not in dict(CatalogFood.SOURCE_TYPE_CHOICES):
        raise CatalogImportGovernanceError(f"Unsupported catalog source type: {source_type}")
    if not source_name.strip():
        raise CatalogImportGovernanceError("A source name is required.")
    if not source_version.strip():
        raise CatalogImportGovernanceError("A source version is required.")
    if len(input_sha256) != 64 or any(character not in "0123456789abcdef" for character in input_sha256.lower()):
        raise CatalogImportGovernanceError("input_sha256 must be a 64-character SHA-256 hex digest.")

    return CatalogImportIdentity(
        source_type=source_type,
        source_name=source_name.strip(),
        source_version=source_version.strip(),
        input_sha256=input_sha256.lower(),
        parameters_payload=parameters_payload or {},
    )
