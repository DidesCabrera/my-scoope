"""Persistence boundary for immutable Food Catalog delivery releases."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping
from uuid import UUID

from django.db import models, transaction
from django.utils import timezone

from food_catalog.models import (
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
    CatalogImportBatch,
    CatalogRelease,
)

CATALOG_RELEASE_SCHEMA_VERSION = "myscoope.food_catalog.release.v1"
CATALOG_AUTHORITY_SNAPSHOT_SCHEMA_VERSION = "myscoope.food_catalog.authority_snapshot.v1"

_FOOD_EXCLUDED_FIELDS = {
    "id",
    "created_by",
    "reviewed_by",
    "created_at",
    "updated_at",
    "reviewed_at",
    "published_at",
    "is_release_managed",
    "imported_release_version",
}
_RELATED_EXCLUDED_FIELDS = {
    "id",
    "catalog_food",
    "import_batch",
    "created_at",
    "updated_at",
    "imported_at",
    "last_checked_at",
}
_BATCH_EXCLUDED_FIELDS = {
    "id",
    "dry_run_batch",
    "requested_by",
    "started_at",
    "finished_at",
}


class CatalogReleaseError(ValueError):
    """Raised when a release cannot be built, verified or imported safely."""


@dataclass(frozen=True)
class CatalogReleaseImportResult:
    release: CatalogRelease
    created_foods: int
    updated_foods: int
    deprecated_foods: int
    changed_catalog_refs: tuple[str, ...]
    idempotent: bool = False


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def payload_sha256(payload: object) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def build_authority_snapshot_envelope() -> dict[str, object]:
    """Export master curation state once when bootstrapping the authority."""

    batches = tuple(CatalogImportBatch.objects.order_by("id"))
    foods = tuple(
        CatalogFood.objects.prefetch_related("aliases", "portions", "sources").order_by(
            "catalog_ref",
            "id",
        )
    )
    payload = {
        "schema_version": CATALOG_AUTHORITY_SNAPSHOT_SCHEMA_VERSION,
        "generated_at": timezone.now().isoformat(),
        "import_batches": [_serialize_import_batch(batch) for batch in batches],
        "foods": [
            _serialize_catalog_food(food, include_import_batch=True) for food in foods
        ],
    }
    return {
        "snapshot": {
            "schema_version": CATALOG_AUTHORITY_SNAPSHOT_SCHEMA_VERSION,
            "food_count": len(foods),
            "import_batch_count": len(batches),
            "payload_sha256": payload_sha256(payload),
        },
        "payload": payload,
    }


@transaction.atomic
def import_authority_snapshot(envelope: Mapping[str, object]) -> int:
    foods, batches = _validate_authority_snapshot_envelope(envelope)
    imported_batches = _import_authority_batches(batches)
    _restore_authority_foods(foods, imported_batches)
    return len(foods)


def _validate_authority_snapshot_envelope(
    envelope: Mapping[str, object],
) -> tuple[list[object], list[object]]:
    metadata = envelope.get("snapshot") if isinstance(envelope, Mapping) else None
    payload = envelope.get("payload") if isinstance(envelope, Mapping) else None
    if not isinstance(metadata, Mapping) or not isinstance(payload, Mapping):
        raise CatalogReleaseError("catalog_authority_snapshot_invalid")
    if metadata.get("schema_version") != CATALOG_AUTHORITY_SNAPSHOT_SCHEMA_VERSION:
        raise CatalogReleaseError("catalog_authority_snapshot_schema_unsupported")
    if payload.get("schema_version") != CATALOG_AUTHORITY_SNAPSHOT_SCHEMA_VERSION:
        raise CatalogReleaseError("catalog_authority_snapshot_payload_schema_unsupported")
    if payload_sha256(payload) != str(metadata.get("payload_sha256") or ""):
        raise CatalogReleaseError("catalog_authority_snapshot_checksum_mismatch")
    foods = payload.get("foods")
    if not isinstance(foods, list) or len(foods) != int(metadata.get("food_count") or 0):
        raise CatalogReleaseError("catalog_authority_snapshot_food_count_mismatch")
    batches = payload.get("import_batches")
    if not isinstance(batches, list) or len(batches) != int(
        metadata.get("import_batch_count") or 0
    ):
        raise CatalogReleaseError("catalog_authority_snapshot_batch_count_mismatch")
    if CatalogFood.objects.exists():
        raise CatalogReleaseError("catalog_authority_snapshot_requires_empty_catalog")
    if CatalogImportBatch.objects.exists():
        raise CatalogReleaseError("catalog_authority_snapshot_requires_empty_batches")
    return foods, batches


def _import_authority_batches(
    batches: list[object],
) -> dict[int, CatalogImportBatch]:
    imported_batches: dict[int, CatalogImportBatch] = {}
    pending_dry_run_links: list[tuple[CatalogImportBatch, int]] = []
    for raw_batch in batches:
        if not isinstance(raw_batch, Mapping):
            raise CatalogReleaseError("catalog_authority_snapshot_batch_item_invalid")
        legacy_id = int(raw_batch.get("legacy_id") or 0)
        if legacy_id <= 0 or legacy_id in imported_batches:
            raise CatalogReleaseError("catalog_authority_snapshot_batch_id_invalid")
        values = _importable_values(
            CatalogImportBatch,
            dict(raw_batch.get("batch") or {}),
            excluded=_BATCH_EXCLUDED_FIELDS,
        )
        imported = CatalogImportBatch.objects.create(**values)
        imported_batches[legacy_id] = imported
        dry_run_legacy_id = int(raw_batch.get("dry_run_legacy_id") or 0)
        if dry_run_legacy_id:
            pending_dry_run_links.append((imported, dry_run_legacy_id))

    for imported, dry_run_legacy_id in pending_dry_run_links:
        dry_run_batch = imported_batches.get(dry_run_legacy_id)
        if dry_run_batch is None:
            raise CatalogReleaseError("catalog_authority_snapshot_dry_run_batch_missing")
        imported.dry_run_batch = dry_run_batch
        imported.save(update_fields=["dry_run_batch"])
    return imported_batches


def _restore_authority_foods(
    foods: list[object],
    imported_batches: Mapping[int, CatalogImportBatch],
) -> None:
    for raw_item in foods:
        if not isinstance(raw_item, Mapping):
            raise CatalogReleaseError("catalog_authority_snapshot_food_item_invalid")
        food_values = dict(raw_item.get("food") or {})
        catalog_ref = str(food_values.get("catalog_ref") or "")
        if not catalog_ref:
            raise CatalogReleaseError("catalog_authority_snapshot_catalog_ref_required")
        values = _importable_values(
            CatalogFood,
            food_values,
            excluded=_FOOD_EXCLUDED_FIELDS,
        )
        values.update(
            is_release_managed=False,
            imported_release_version="",
        )
        catalog_food = CatalogFood.objects.create(**values)
        _replace_related(
            catalog_food,
            raw_item,
            import_batches=imported_batches,
        )


@transaction.atomic
def build_catalog_release(
    *,
    version: str,
    actor=None,
    notes: str = "",
    previous_version: str = "",
) -> CatalogRelease:
    normalized_version = str(version or "").strip()
    if not normalized_version:
        raise CatalogReleaseError("catalog_release_version_required")
    if CatalogRelease.objects.filter(version=normalized_version).exists():
        raise CatalogReleaseError("catalog_release_version_already_exists")

    foods = tuple(
        CatalogFood.objects.filter(status=CatalogFood.STATUS_PUBLISHED)
        .prefetch_related("aliases", "portions", "sources")
        .order_by("catalog_ref", "id")
    )
    if not foods:
        raise CatalogReleaseError("catalog_release_requires_published_foods")

    previous = str(previous_version or "").strip()
    if not previous:
        previous = (
            CatalogRelease.objects.filter(
                role=CatalogRelease.ROLE_AUTHORITY,
                status=CatalogRelease.STATUS_APPROVED,
            )
            .order_by("-approved_at", "-id")
            .values_list("version", flat=True)
            .first()
            or ""
        )

    payload = {
        "schema_version": CATALOG_RELEASE_SCHEMA_VERSION,
        "release_version": normalized_version,
        "previous_version": previous,
        "generated_at": timezone.now().isoformat(),
        "foods": [_serialize_catalog_food(food) for food in foods],
    }
    return CatalogRelease.objects.create(
        version=normalized_version,
        schema_version=CATALOG_RELEASE_SCHEMA_VERSION,
        status=CatalogRelease.STATUS_CANDIDATE,
        role=CatalogRelease.ROLE_AUTHORITY,
        previous_version=previous,
        payload=payload,
        payload_sha256=payload_sha256(payload),
        food_count=len(foods),
        notes=str(notes or "").strip(),
        created_by=actor if getattr(actor, "pk", None) else None,
    )


@transaction.atomic
def approve_catalog_release(release: CatalogRelease, *, actor=None) -> CatalogRelease:
    locked = CatalogRelease.objects.select_for_update().get(pk=release.pk)
    if locked.role != CatalogRelease.ROLE_AUTHORITY:
        raise CatalogReleaseError("catalog_release_replica_cannot_be_approved")
    if locked.status == CatalogRelease.STATUS_APPROVED:
        return locked
    if locked.status != CatalogRelease.STATUS_CANDIDATE:
        raise CatalogReleaseError("catalog_release_not_candidate")
    if payload_sha256(locked.payload) != locked.payload_sha256:
        raise CatalogReleaseError("catalog_release_checksum_mismatch")
    locked.status = CatalogRelease.STATUS_APPROVED
    locked.approved_by = actor if getattr(actor, "pk", None) else None
    locked.approved_at = timezone.now()
    locked.save(update_fields=["status", "approved_by", "approved_at"])
    return locked


def release_envelope(release: CatalogRelease) -> dict[str, Any]:
    if release.status != CatalogRelease.STATUS_APPROVED:
        raise CatalogReleaseError("catalog_release_not_approved")
    return {
        "release": {
            "release_ref": str(release.release_ref),
            "version": release.version,
            "schema_version": release.schema_version,
            "status": release.status,
            "previous_version": release.previous_version,
            "food_count": release.food_count,
            "payload_sha256": release.payload_sha256,
            "approved_at": release.approved_at.isoformat() if release.approved_at else None,
        },
        "payload": release.payload,
    }


def validate_release_envelope(envelope: Mapping[str, object]) -> tuple[dict, dict]:
    if not isinstance(envelope, Mapping):
        raise CatalogReleaseError("catalog_release_envelope_invalid")
    metadata = envelope.get("release")
    payload = envelope.get("payload")
    if not isinstance(metadata, Mapping) or not isinstance(payload, Mapping):
        raise CatalogReleaseError("catalog_release_envelope_invalid")
    metadata = dict(metadata)
    payload = dict(payload)
    if metadata.get("status") != CatalogRelease.STATUS_APPROVED:
        raise CatalogReleaseError("catalog_release_not_approved")
    if metadata.get("schema_version") != CATALOG_RELEASE_SCHEMA_VERSION:
        raise CatalogReleaseError("catalog_release_schema_unsupported")
    if payload.get("schema_version") != CATALOG_RELEASE_SCHEMA_VERSION:
        raise CatalogReleaseError("catalog_release_payload_schema_unsupported")
    if str(metadata.get("version") or "") != str(payload.get("release_version") or ""):
        raise CatalogReleaseError("catalog_release_version_mismatch")
    expected_hash = str(metadata.get("payload_sha256") or "")
    if not expected_hash or payload_sha256(payload) != expected_hash:
        raise CatalogReleaseError("catalog_release_checksum_mismatch")
    foods = payload.get("foods")
    if not isinstance(foods, list) or len(foods) != int(metadata.get("food_count") or 0):
        raise CatalogReleaseError("catalog_release_food_count_mismatch")
    return metadata, payload


@transaction.atomic
def import_catalog_release(envelope: Mapping[str, object]) -> CatalogReleaseImportResult:
    metadata, payload = validate_release_envelope(envelope)
    version = str(metadata["version"])
    checksum = str(metadata["payload_sha256"])
    existing_release = CatalogRelease.objects.filter(version=version).first()
    if existing_release:
        if existing_release.payload_sha256 != checksum:
            raise CatalogReleaseError("catalog_release_version_checksum_conflict")
        return CatalogReleaseImportResult(
            release=existing_release,
            created_foods=0,
            updated_foods=0,
            deprecated_foods=0,
            changed_catalog_refs=(),
            idempotent=True,
        )

    created_foods = 0
    updated_foods = 0
    changed_refs: list[str] = []
    delivered_refs: set[str] = set()

    for raw_item in payload["foods"]:
        if not isinstance(raw_item, Mapping):
            raise CatalogReleaseError("catalog_release_food_item_invalid")
        food_values = dict(raw_item.get("food") or {})
        catalog_ref = str(food_values.get("catalog_ref") or "")
        if not catalog_ref:
            raise CatalogReleaseError("catalog_release_food_catalog_ref_required")
        delivered_refs.add(catalog_ref)
        defaults = _importable_values(
            CatalogFood,
            food_values,
            excluded=_FOOD_EXCLUDED_FIELDS,
        )
        defaults.update(
            status=CatalogFood.STATUS_PUBLISHED,
            is_release_managed=True,
            imported_release_version=version,
        )
        catalog_food, created = CatalogFood.objects.update_or_create(
            catalog_ref=catalog_ref,
            defaults=defaults,
        )
        created_foods += int(created)
        updated_foods += int(not created)
        changed_refs.append(catalog_ref)
        _replace_related(catalog_food, raw_item)

    deprecated_qs = CatalogFood.objects.filter(
        is_release_managed=True,
        status=CatalogFood.STATUS_PUBLISHED,
    ).exclude(catalog_ref__in=delivered_refs)
    deprecated_foods = deprecated_qs.update(
        status=CatalogFood.STATUS_DEPRECATED,
        imported_release_version=version,
    )

    release = CatalogRelease.objects.create(
        release_ref=metadata["release_ref"],
        version=version,
        schema_version=str(metadata["schema_version"]),
        status=CatalogRelease.STATUS_APPROVED,
        role=CatalogRelease.ROLE_REPLICA,
        previous_version=str(metadata.get("previous_version") or ""),
        payload=payload,
        payload_sha256=checksum,
        food_count=int(metadata["food_count"]),
        approved_at=_parse_datetime(metadata.get("approved_at")),
        imported_at=timezone.now(),
    )
    return CatalogReleaseImportResult(
        release=release,
        created_foods=created_foods,
        updated_foods=updated_foods,
        deprecated_foods=deprecated_foods,
        changed_catalog_refs=tuple(changed_refs),
    )


def _serialize_catalog_food(
    food: CatalogFood,
    *,
    include_import_batch: bool = False,
) -> dict[str, object]:
    sources = []
    for item in food.sources.all().order_by("id"):
        value = _serialize_model(item, excluded=_RELATED_EXCLUDED_FIELDS)
        if include_import_batch:
            value["_import_batch_legacy_id"] = item.import_batch_id
        sources.append(value)
    return {
        "food": _serialize_model(food, excluded=_FOOD_EXCLUDED_FIELDS),
        "portions": [
            _serialize_model(item, excluded=_RELATED_EXCLUDED_FIELDS)
            for item in food.portions.all().order_by("id")
        ],
        "aliases": [
            _serialize_model(item, excluded=_RELATED_EXCLUDED_FIELDS)
            for item in food.aliases.all().order_by("id")
        ],
        "sources": sources,
    }


def _serialize_import_batch(batch: CatalogImportBatch) -> dict[str, object]:
    return {
        "legacy_id": batch.pk,
        "dry_run_legacy_id": batch.dry_run_batch_id,
        "batch": _serialize_model(batch, excluded=_BATCH_EXCLUDED_FIELDS),
    }


def _serialize_model(instance: models.Model, *, excluded: set[str]) -> dict[str, object]:
    values = {}
    for field in instance._meta.concrete_fields:
        if field.name in excluded or isinstance(field, models.AutoField):
            continue
        values[field.name] = _json_value(field.value_from_object(instance))
    return values


def _json_value(value: object) -> object:
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _importable_values(
    model: type[models.Model],
    raw_values: Mapping[str, object],
    *,
    excluded: set[str],
) -> dict[str, object]:
    allowed = {
        field.name
        for field in model._meta.concrete_fields
        if field.name not in excluded and not isinstance(field, models.AutoField)
    }
    return {key: value for key, value in raw_values.items() if key in allowed}


def _replace_related(
    catalog_food: CatalogFood,
    item: Mapping[str, object],
    *,
    import_batches: Mapping[int, CatalogImportBatch] | None = None,
) -> None:
    related_specs = (
        ("portions", CatalogFoodPortion),
        ("aliases", CatalogFoodAlias),
        ("sources", CatalogFoodSource),
    )
    for payload_key, model in related_specs:
        getattr(catalog_food, payload_key).all().delete()
        rows = item.get(payload_key) or []
        if not isinstance(rows, list):
            raise CatalogReleaseError(f"catalog_release_{payload_key}_invalid")
        instances = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            values = dict(row)
            kwargs = _importable_values(
                model,
                values,
                excluded=_RELATED_EXCLUDED_FIELDS,
            )
            if model is CatalogFoodSource and import_batches is not None:
                legacy_id = int(values.get("_import_batch_legacy_id") or 0)
                if legacy_id:
                    import_batch = import_batches.get(legacy_id)
                    if import_batch is None:
                        raise CatalogReleaseError(
                            "catalog_authority_snapshot_source_batch_missing"
                        )
                    kwargs["import_batch"] = import_batch
            instances.append(model(catalog_food=catalog_food, **kwargs))
        model.objects.bulk_create(instances)


def _parse_datetime(value: object):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise CatalogReleaseError("catalog_release_approved_at_invalid") from exc


__all__ = [
    "CATALOG_AUTHORITY_SNAPSHOT_SCHEMA_VERSION",
    "CATALOG_RELEASE_SCHEMA_VERSION",
    "CatalogReleaseError",
    "CatalogReleaseImportResult",
    "approve_catalog_release",
    "build_authority_snapshot_envelope",
    "build_catalog_release",
    "canonical_json_bytes",
    "import_catalog_release",
    "import_authority_snapshot",
    "payload_sha256",
    "release_envelope",
    "validate_release_envelope",
]
