"""Brand-submitted food intake for the master Food Catalog.

This module imports brand-provided nutrition rows into ``CatalogFood`` as
curation work. It does not create ``notas.Food`` and it does not publish foods
automatically. The existing curation workflow must review/verify/publish them.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import hashlib
from typing import Iterable
from django.utils import timezone

from food_catalog.application.imports.normalization import normalize_food_name
from food_catalog.models import (
    CatalogFood,
    CatalogFoodAlias,
    CatalogFoodPortion,
    CatalogFoodSource,
    CatalogImportBatch,
)
from food_catalog.infrastructure.imports.governance import (
    catalog_import_identity,
    start_catalog_import_batch,
)

BRAND_INTAKE_SOURCE_NAME = "brand_verified_intake"
BRAND_INTAKE_SOURCE_VERSION = "v1"
REQUIRED_BRAND_INTAKE_COLUMNS = (
    "display_name",
    "brand_name",
    "protein_g_per_100g",
    "carbs_g_per_100g",
    "fat_g_per_100g",
    "default_portion_g",
    "authorization_confirmed",
)
OPTIONAL_BRAND_INTAKE_COLUMNS = (
    "canonical_name",
    "barcode",
    "country",
    "food_group",
    "food_subgroup",
    "preparation_state",
    "calories_kcal_per_100g",
    "fiber_g_per_100g",
    "sugar_g_per_100g",
    "saturated_fat_g_per_100g",
    "sodium_mg_per_100g",
    "serving_label",
    "solver_min_portion_g",
    "solver_max_portion_g",
    "solver_portion_step_g",
    "aliases",
    "label_evidence_url",
    "authorization_reference",
    "source_url",
    "contact_email",
    "notes",
)

_TRUE_VALUES = {"1", "true", "yes", "y", "si", "sí", "autorizado", "authorized"}
_ALLOWED_PREPARATION_STATES = {choice[0] for choice in CatalogFood.PREPARATION_STATE_CHOICES}


@dataclass(frozen=True)
class BrandFoodIntakeRow:
    row_number: int
    display_name: str
    brand_name: str
    canonical_name: str
    barcode: str
    country: str
    food_group: str
    food_subgroup: str
    preparation_state: str
    protein_g_per_100g: Decimal
    carbs_g_per_100g: Decimal
    fat_g_per_100g: Decimal
    calories_kcal_per_100g: Decimal | None
    fiber_g_per_100g: Decimal | None
    sugar_g_per_100g: Decimal | None
    saturated_fat_g_per_100g: Decimal | None
    sodium_mg_per_100g: Decimal | None
    default_portion_g: Decimal
    serving_label: str
    solver_min_portion_g: Decimal | None
    solver_max_portion_g: Decimal | None
    solver_portion_step_g: Decimal | None
    aliases: tuple[str, ...]
    label_evidence_url: str
    authorization_reference: str
    source_url: str
    contact_email: str
    notes: str
    authorization_confirmed: bool

    @property
    def source_food_id(self) -> str:
        if self.barcode:
            return self.barcode
        return f"{self.brand_name}:{self.canonical_name}:{self.country}".lower()


@dataclass(frozen=True)
class BrandFoodIntakeValidation:
    is_valid: bool
    errors: tuple[str, ...]
    row: BrandFoodIntakeRow | None = None


@dataclass(frozen=True)
class BrandFoodIntakeResult:
    total_rows: int
    created_rows: int
    updated_rows: int
    skipped_rows: int
    errors: tuple[str, ...]
    batch: CatalogImportBatch | None = None


def load_brand_food_intake_csv(path: str | Path) -> tuple[BrandFoodIntakeValidation, ...]:
    """Load and validate a brand intake CSV file.

    The CSV is curator-facing and intentionally strict: rows without explicit
    brand authorization are rejected so they cannot become publishable by
    accident.
    """

    path = Path(path)
    validations: list[BrandFoodIntakeValidation] = []
    with path.open(newline="", encoding="utf-8-sig") as file_obj:
        reader = csv.DictReader(file_obj)
        missing_columns = [column for column in REQUIRED_BRAND_INTAKE_COLUMNS if column not in (reader.fieldnames or [])]
        if missing_columns:
            return (
                BrandFoodIntakeValidation(
                    is_valid=False,
                    errors=(f"missing required columns: {', '.join(missing_columns)}",),
                ),
            )

        for row_number, raw_row in enumerate(reader, start=2):
            validations.append(validate_brand_food_intake_row(raw_row, row_number=row_number))
    return tuple(validations)


def validate_brand_food_intake_row(raw_row: dict[str, str | None], *, row_number: int) -> BrandFoodIntakeValidation:
    errors: list[str] = []

    display_name = _clean(raw_row.get("display_name"))
    brand_name = _clean(raw_row.get("brand_name"))
    canonical_name = normalize_food_name(_clean(raw_row.get("canonical_name")) or display_name)
    barcode = _clean(raw_row.get("barcode"))
    country = _clean(raw_row.get("country")) or "CL"
    food_group = _clean(raw_row.get("food_group"))
    food_subgroup = _clean(raw_row.get("food_subgroup"))
    preparation_state = _clean(raw_row.get("preparation_state")) or CatalogFood.PREPARATION_READY_TO_EAT
    serving_label = _clean(raw_row.get("serving_label")) or "Porción"
    aliases = tuple(
        alias.strip()
        for alias in _clean(raw_row.get("aliases")).split("|")
        if alias.strip()
    )
    authorization_confirmed = _as_bool(raw_row.get("authorization_confirmed"))

    if not display_name:
        errors.append("display_name is required")
    if not brand_name:
        errors.append("brand_name is required")
    if not canonical_name:
        errors.append("canonical_name is required")
    if preparation_state not in _ALLOWED_PREPARATION_STATES:
        errors.append(f"preparation_state is invalid: {preparation_state}")
    if not authorization_confirmed:
        errors.append("authorization_confirmed must be true/yes/sí/1")
    if not _clean(raw_row.get("label_evidence_url")):
        errors.append("label_evidence_url is required")
    if not _clean(raw_row.get("authorization_reference")):
        errors.append("authorization_reference is required")

    protein = _decimal_required(raw_row.get("protein_g_per_100g"), "protein_g_per_100g", errors)
    carbs = _decimal_required(raw_row.get("carbs_g_per_100g"), "carbs_g_per_100g", errors)
    fat = _decimal_required(raw_row.get("fat_g_per_100g"), "fat_g_per_100g", errors)
    default_portion = _decimal_required(raw_row.get("default_portion_g"), "default_portion_g", errors)

    optional_decimals = {
        "calories_kcal_per_100g": _decimal_optional(raw_row.get("calories_kcal_per_100g"), "calories_kcal_per_100g", errors),
        "fiber_g_per_100g": _decimal_optional(raw_row.get("fiber_g_per_100g"), "fiber_g_per_100g", errors),
        "sugar_g_per_100g": _decimal_optional(raw_row.get("sugar_g_per_100g"), "sugar_g_per_100g", errors),
        "saturated_fat_g_per_100g": _decimal_optional(raw_row.get("saturated_fat_g_per_100g"), "saturated_fat_g_per_100g", errors),
        "sodium_mg_per_100g": _decimal_optional(raw_row.get("sodium_mg_per_100g"), "sodium_mg_per_100g", errors),
        "solver_min_portion_g": _decimal_optional(raw_row.get("solver_min_portion_g"), "solver_min_portion_g", errors),
        "solver_max_portion_g": _decimal_optional(raw_row.get("solver_max_portion_g"), "solver_max_portion_g", errors),
        "solver_portion_step_g": _decimal_optional(raw_row.get("solver_portion_step_g"), "solver_portion_step_g", errors),
    }

    for field_name, value in {
        "protein_g_per_100g": protein,
        "carbs_g_per_100g": carbs,
        "fat_g_per_100g": fat,
    }.items():
        if value is not None and (value < 0 or value > 100):
            errors.append(f"{field_name} must be between 0 and 100")

    if protein is not None and carbs is not None and fat is not None:
        if protein + carbs + fat > Decimal("120"):
            errors.append("protein + carbs + fat cannot exceed 120 g per 100 g")

    if default_portion is not None and default_portion <= 0:
        errors.append("default_portion_g must be greater than 0")

    if errors:
        return BrandFoodIntakeValidation(
            is_valid=False,
            errors=tuple(f"row {row_number}: {error}" for error in errors),
        )

    assert protein is not None
    assert carbs is not None
    assert fat is not None
    assert default_portion is not None

    return BrandFoodIntakeValidation(
        is_valid=True,
        errors=(),
        row=BrandFoodIntakeRow(
            row_number=row_number,
            display_name=display_name,
            brand_name=brand_name,
            canonical_name=canonical_name,
            barcode=barcode,
            country=country,
            food_group=food_group,
            food_subgroup=food_subgroup,
            preparation_state=preparation_state,
            protein_g_per_100g=protein,
            carbs_g_per_100g=carbs,
            fat_g_per_100g=fat,
            calories_kcal_per_100g=optional_decimals["calories_kcal_per_100g"],
            fiber_g_per_100g=optional_decimals["fiber_g_per_100g"],
            sugar_g_per_100g=optional_decimals["sugar_g_per_100g"],
            saturated_fat_g_per_100g=optional_decimals["saturated_fat_g_per_100g"],
            sodium_mg_per_100g=optional_decimals["sodium_mg_per_100g"],
            default_portion_g=default_portion,
            serving_label=serving_label,
            solver_min_portion_g=optional_decimals["solver_min_portion_g"],
            solver_max_portion_g=optional_decimals["solver_max_portion_g"],
            solver_portion_step_g=optional_decimals["solver_portion_step_g"],
            aliases=aliases,
            label_evidence_url=_clean(raw_row.get("label_evidence_url")),
            authorization_reference=_clean(raw_row.get("authorization_reference")),
            source_url=_clean(raw_row.get("source_url")),
            contact_email=_clean(raw_row.get("contact_email")),
            notes=_clean(raw_row.get("notes")),
            authorization_confirmed=authorization_confirmed,
        ),
    )


def dry_run_brand_food_intake_csv(path: str | Path, *, limit: int | None = None) -> BrandFoodIntakeResult:
    validations = load_brand_food_intake_csv(path)
    if limit is not None:
        validations = validations[:limit]
    errors = _collect_errors(validations)
    invalid_rows = sum(1 for validation in validations if not validation.is_valid)
    return BrandFoodIntakeResult(
        total_rows=len(validations),
        created_rows=0,
        updated_rows=0,
        skipped_rows=invalid_rows,
        errors=errors,
    )


def brand_food_intake_identity(path: str | Path, *, limit: int):
    path = Path(path)
    return catalog_import_identity(
        source_type=CatalogFood.SOURCE_BRAND_SUBMITTED,
        source_name=BRAND_INTAKE_SOURCE_NAME,
        source_version=BRAND_INTAKE_SOURCE_VERSION,
        input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        parameters_payload={"format": "brand_csv_intake", "limit": limit},
    )


def apply_brand_food_intake_csv(
    path: str | Path,
    *,
    dry_run_batch: CatalogImportBatch,
    reason: str,
    limit: int,
    created_by=None,
) -> BrandFoodIntakeResult:
    validations = load_brand_food_intake_csv(path)[:limit]
    errors = _collect_errors(validations)
    valid_rows = [validation.row for validation in validations if validation.is_valid and validation.row is not None]

    if errors:
        return BrandFoodIntakeResult(
            total_rows=len(validations),
            created_rows=0,
            updated_rows=0,
            skipped_rows=sum(1 for validation in validations if not validation.is_valid),
            errors=errors,
        )

    batch = start_catalog_import_batch(
        identity=brand_food_intake_identity(path, limit=limit),
        dry_run_batch=dry_run_batch,
        total_rows=len(valid_rows),
        requested_by=created_by,
        reason=reason,
    )

    created = 0
    updated = 0
    for row in valid_rows:
        was_created = _upsert_brand_food(row, import_batch=batch, created_by=created_by)
        if was_created:
            created += 1
        else:
            updated += 1

    batch.imported_rows = created + updated
    batch.status = CatalogImportBatch.STATUS_COMPLETED
    batch.finished_at = timezone.now()
    batch.summary_payload = {"created": created, "updated": updated, "source": BRAND_INTAKE_SOURCE_NAME}
    batch.save(update_fields=["imported_rows", "status", "finished_at", "summary_payload"])

    return BrandFoodIntakeResult(
        total_rows=len(valid_rows),
        created_rows=created,
        updated_rows=updated,
        skipped_rows=0,
        errors=(),
        batch=batch,
    )


def _upsert_brand_food(row: BrandFoodIntakeRow, *, import_batch: CatalogImportBatch, created_by=None) -> bool:
    defaults = {
        "display_name": row.display_name,
        "brand_name": row.brand_name,
        "is_branded": True,
        "language": "es",
        "country": row.country,
        "food_group": row.food_group,
        "food_subgroup": row.food_subgroup,
        "preparation_state": row.preparation_state,
        "source_type": CatalogFood.SOURCE_BRAND_SUBMITTED,
        "status": CatalogFood.STATUS_BRAND_SUBMITTED,
        "protein_g_per_100g": row.protein_g_per_100g,
        "carbs_g_per_100g": row.carbs_g_per_100g,
        "fat_g_per_100g": row.fat_g_per_100g,
        "calories_kcal_per_100g": row.calories_kcal_per_100g,
        "fiber_g_per_100g": row.fiber_g_per_100g,
        "sugar_g_per_100g": row.sugar_g_per_100g,
        "saturated_fat_g_per_100g": row.saturated_fat_g_per_100g,
        "sodium_mg_per_100g": row.sodium_mg_per_100g,
        "data_quality_score": 85,
        "confidence_score": Decimal("90.00"),
        "solver_enabled": True,
        "solver_min_portion_g": row.solver_min_portion_g,
        "solver_max_portion_g": row.solver_max_portion_g,
        "solver_portion_step_g": row.solver_portion_step_g,
    }
    if created_by is not None and getattr(created_by, "is_authenticated", False):
        defaults["created_by"] = created_by

    food, created = CatalogFood.objects.update_or_create(
        canonical_name=row.canonical_name,
        brand_name=row.brand_name,
        country=row.country,
        defaults=defaults,
    )

    CatalogFoodPortion.objects.update_or_create(
        catalog_food=food,
        label=row.serving_label,
        defaults={
            "grams": row.default_portion_g,
            "source": BRAND_INTAKE_SOURCE_NAME,
            "is_default": True,
        },
    )

    for alias in _iter_aliases(row):
        CatalogFoodAlias.objects.update_or_create(
            catalog_food=food,
            normalized_name=normalize_food_name(alias),
            language="es",
            country=row.country,
            defaults={"name": alias, "alias_type": CatalogFoodAlias.ALIAS_SEARCH},
        )

    CatalogFoodSource.objects.update_or_create(
        source_name=BRAND_INTAKE_SOURCE_NAME,
        source_food_id=row.source_food_id,
        defaults={
            "catalog_food": food,
            "import_batch": import_batch,
            "source_type": CatalogFood.SOURCE_BRAND_SUBMITTED,
            "source_dataset": "brand_csv_intake",
            "source_version": BRAND_INTAKE_SOURCE_VERSION,
            "source_url": row.source_url or row.label_evidence_url,
            "license_name": "Brand authorization",
            "license_status": CatalogFoodSource.LICENSE_ALLOWED,
            "attribution": f"Brand-submitted nutrition data authorized by {row.brand_name}.",
            "evidence_payload": {
                "barcode": row.barcode,
                "label_evidence_url": row.label_evidence_url,
                "authorization_reference": row.authorization_reference,
                "authorization_confirmed": row.authorization_confirmed,
                "contact_email": row.contact_email,
                "notes": row.notes,
            },
        },
    )
    return created


def _iter_aliases(row: BrandFoodIntakeRow) -> Iterable[str]:
    seen = set()
    for alias in (row.display_name, row.canonical_name, *row.aliases):
        normalized = normalize_food_name(alias)
        if normalized and normalized not in seen:
            seen.add(normalized)
            yield alias


def _collect_errors(validations: Iterable[BrandFoodIntakeValidation]) -> tuple[str, ...]:
    errors: list[str] = []
    for validation in validations:
        errors.extend(validation.errors)
    return tuple(errors)


def _clean(value: str | None) -> str:
    return str(value or "").strip()


def _as_bool(value: str | None) -> bool:
    return _clean(value).lower() in _TRUE_VALUES


def _decimal_required(value: str | None, field_name: str, errors: list[str]) -> Decimal | None:
    parsed = _decimal_optional(value, field_name, errors)
    if parsed is None:
        errors.append(f"{field_name} is required")
    return parsed


def _decimal_optional(value: str | None, field_name: str, errors: list[str]) -> Decimal | None:
    raw_value = _clean(value)
    if not raw_value:
        return None
    try:
        return Decimal(raw_value)
    except (InvalidOperation, ValueError):
        errors.append(f"{field_name} must be numeric")
        return None
