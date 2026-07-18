"""Evidence-first manual intake for real, curator-sourced foods."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from food_catalog.application.imports.normalization import normalize_food_name
from food_catalog.infrastructure.imports.governance import catalog_import_identity, start_catalog_import_batch
from food_catalog.models import CatalogFood, CatalogFoodPortion, CatalogFoodSource, CatalogImportBatch


MANUAL_INTAKE_SOURCE_NAME = "manual_evidence_intake"
REQUIRED_COLUMNS = (
    "display_name", "protein_g_per_100g", "carbs_g_per_100g", "fat_g_per_100g",
    "default_portion_g", "preparation_state", "evidence_url", "evidence_reference",
    "license_name", "attribution", "source_version",
)


@dataclass(frozen=True)
class ManualEvidenceRow:
    display_name: str
    canonical_name: str
    protein: Decimal
    carbs: Decimal
    fat: Decimal
    portion_g: Decimal
    preparation_state: str
    evidence_url: str
    evidence_reference: str
    license_name: str
    attribution: str
    source_version: str
    country: str
    food_group: str


@dataclass(frozen=True)
class ManualIntakePlan:
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: tuple[str, ...]
    rows: tuple[ManualEvidenceRow, ...]


@dataclass(frozen=True)
class ManualIntakeResult:
    batch: CatalogImportBatch
    total_rows: int
    created_rows: int
    updated_rows: int


def dry_run_manual_evidence_csv(path: str | Path, *, limit: int) -> ManualIntakePlan:
    path = Path(path)
    errors: list[str] = []
    rows: list[ManualEvidenceRow] = []
    with path.open(newline="", encoding="utf-8-sig") as file_obj:
        reader = csv.DictReader(file_obj)
        missing = [name for name in REQUIRED_COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            return ManualIntakePlan(0, 0, 0, (f"missing required columns: {', '.join(missing)}",), ())
        raw_rows = list(reader)[:limit]

    for row_number, raw in enumerate(raw_rows, start=2):
        row_errors: list[str] = []
        display_name = _clean(raw.get("display_name"))
        canonical_name = normalize_food_name(_clean(raw.get("canonical_name")) or display_name)
        protein = _decimal(raw.get("protein_g_per_100g"), "protein_g_per_100g", row_errors)
        carbs = _decimal(raw.get("carbs_g_per_100g"), "carbs_g_per_100g", row_errors)
        fat = _decimal(raw.get("fat_g_per_100g"), "fat_g_per_100g", row_errors)
        portion = _decimal(raw.get("default_portion_g"), "default_portion_g", row_errors)
        preparation = _clean(raw.get("preparation_state"))
        evidence_url = _clean(raw.get("evidence_url"))
        evidence_reference = _clean(raw.get("evidence_reference"))
        license_name = _clean(raw.get("license_name"))
        attribution = _clean(raw.get("attribution"))
        source_version = _clean(raw.get("source_version"))
        if not display_name or not canonical_name:
            row_errors.append("display_name/canonical_name is required")
        if preparation not in dict(CatalogFood.PREPARATION_STATE_CHOICES) or preparation == CatalogFood.PREPARATION_UNKNOWN:
            row_errors.append("preparation_state must be explicit")
        for field_name, value in {
            "evidence_url": evidence_url,
            "evidence_reference": evidence_reference,
            "license_name": license_name,
            "attribution": attribution,
            "source_version": source_version,
        }.items():
            if not value:
                row_errors.append(f"{field_name} is required")
        if any(value is not None and (value < 0 or value > 100) for value in (protein, carbs, fat)):
            row_errors.append("macros must be between 0 and 100")
        if portion is not None and portion <= 0:
            row_errors.append("default_portion_g must be positive")
        if row_errors:
            errors.extend(f"row {row_number}: {error}" for error in row_errors)
            continue
        assert None not in (protein, carbs, fat, portion)
        rows.append(ManualEvidenceRow(
            display_name=display_name,
            canonical_name=canonical_name,
            protein=protein,
            carbs=carbs,
            fat=fat,
            portion_g=portion,
            preparation_state=preparation,
            evidence_url=evidence_url,
            evidence_reference=evidence_reference,
            license_name=license_name,
            attribution=attribution,
            source_version=source_version,
            country=_clean(raw.get("country")) or "CL",
            food_group=_clean(raw.get("food_group")),
        ))
    return ManualIntakePlan(len(raw_rows), len(rows), len(raw_rows) - len(rows), tuple(errors), tuple(rows))


def manual_evidence_identity(path: str | Path, *, limit: int, source_version: str):
    path = Path(path)
    return catalog_import_identity(
        source_type=CatalogFood.SOURCE_ADMIN_IMPORT,
        source_name=MANUAL_INTAKE_SOURCE_NAME,
        source_version=source_version,
        input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        parameters_payload={"format": "manual_evidence_csv", "limit": limit},
    )


@transaction.atomic
def apply_manual_evidence_csv(
    path: str | Path,
    *,
    limit: int,
    dry_run_batch: CatalogImportBatch,
    reason: str,
    requested_by=None,
) -> ManualIntakeResult:
    plan = dry_run_manual_evidence_csv(path, limit=limit)
    if plan.errors:
        raise ValueError("Manual evidence CSV is invalid: " + "; ".join(plan.errors[:3]))
    versions = {row.source_version for row in plan.rows}
    if len(versions) != 1:
        raise ValueError("All manual evidence rows must share one source_version.")
    source_version = next(iter(versions), "")
    batch = start_catalog_import_batch(
        identity=manual_evidence_identity(path, limit=limit, source_version=source_version),
        dry_run_batch=dry_run_batch,
        total_rows=plan.total_rows,
        requested_by=requested_by,
        reason=reason,
    )
    created = 0
    updated = 0
    for row in plan.rows:
        food, was_created = CatalogFood.objects.update_or_create(
            canonical_name=row.canonical_name,
            brand_name="",
            country=row.country,
            defaults={
                "display_name": row.display_name,
                "language": "es",
                "food_group": row.food_group,
                "preparation_state": row.preparation_state,
                "protein_g_per_100g": row.protein,
                "carbs_g_per_100g": row.carbs,
                "fat_g_per_100g": row.fat,
                "source_type": CatalogFood.SOURCE_ADMIN_IMPORT,
                "status": CatalogFood.STATUS_MANUAL_CANDIDATE,
                "data_quality_score": 75,
                "created_by": requested_by if getattr(requested_by, "is_authenticated", False) else None,
            },
        )
        created += int(was_created)
        updated += int(not was_created)
        CatalogFoodPortion.objects.update_or_create(
            catalog_food=food,
            label="Porción",
            defaults={"grams": row.portion_g, "source": MANUAL_INTAKE_SOURCE_NAME, "is_default": True},
        )
        CatalogFoodSource.objects.update_or_create(
            source_name=MANUAL_INTAKE_SOURCE_NAME,
            source_food_id=row.evidence_reference,
            defaults={
                "catalog_food": food,
                "import_batch": batch,
                "source_type": CatalogFood.SOURCE_ADMIN_IMPORT,
                "source_dataset": "manual_evidence",
                "source_version": row.source_version,
                "source_url": row.evidence_url,
                "license_name": row.license_name,
                "license_status": CatalogFoodSource.LICENSE_ALLOWED,
                "attribution": row.attribution,
                "evidence_payload": {"reference": row.evidence_reference, "curator_reason": reason},
            },
        )
    batch.imported_rows = created + updated
    batch.status = CatalogImportBatch.STATUS_COMPLETED
    batch.finished_at = timezone.now()
    batch.summary_payload = {"created": created, "updated": updated, "published": 0}
    batch.save(update_fields=["imported_rows", "status", "finished_at", "summary_payload"])
    return ManualIntakeResult(batch, plan.total_rows, created, updated)


def _clean(value) -> str:
    return str(value or "").strip()


def _decimal(value, field_name: str, errors: list[str]) -> Decimal | None:
    try:
        return Decimal(_clean(value))
    except (InvalidOperation, ValueError):
        errors.append(f"{field_name} must be numeric")
        return None
