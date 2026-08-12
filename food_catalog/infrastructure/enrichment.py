"""Governed, reversible enrichment of production CatalogFood records.

This service accepts structured Codex-authored manifests. It never publishes a
food, changes curation status, alters nutrition/source evidence, or creates an
operational snapshot.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from django.db import transaction
from django.utils import timezone

from food_catalog.application.enrichment_profiles import validate_profile_portions
from food_catalog.models import (
    CatalogCapabilityDefinition,
    CatalogEnrichmentBatch,
    CatalogEnrichmentChange,
    CatalogFieldProposal,
    CatalogFood,
    CatalogFoodCapability,
    CatalogFoodPortion,
)

CONTRACT_VERSION = "catalog-enrichment.v1"
DEFAULT_DRY_RUN_TTL = timedelta(hours=24)

ALLOWED_CATALOG_FIELDS = {
    "default_portion_g",
    "solver_min_portion_g",
    "solver_max_portion_g",
    "solver_portion_step_g",
    "solver_enabled",
    "food_form",
    "functional_roles",
    "meal_affinities",
    "preparation_effort",
    "cost_band",
}
DECIMAL_FIELDS = {"default_portion_g", "solver_min_portion_g", "solver_max_portion_g", "solver_portion_step_g"}
LIST_FIELDS = {"functional_roles", "meal_affinities"}
CHOICE_FIELDS = {
    "food_form": {value for value, _label in CatalogFood.FOOD_FORM_CHOICES},
    "preparation_effort": {value for value, _label in CatalogFood.PREPARATION_EFFORT_CHOICES},
    "cost_band": {value for value, _label in CatalogFood.COST_BAND_CHOICES},
}


class CatalogEnrichmentError(ValueError):
    pass


@dataclass(frozen=True)
class CatalogEnrichmentAudit:
    total: int
    missing_counts: dict[str, int]
    client_requirement_gaps: dict[str, int]


@dataclass(frozen=True)
class CatalogEnrichmentDryRunResult:
    batch: CatalogEnrichmentBatch
    total: int
    valid: int
    invalid: int


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def audit_catalog_enrichment(queryset=None) -> CatalogEnrichmentAudit:
    foods = queryset if queryset is not None else CatalogFood.objects.all()
    missing = {
        "default_portion": foods.exclude(portions__is_default=True).distinct().count(),
        "solver_min_portion_g": foods.filter(solver_min_portion_g__isnull=True).count(),
        "solver_max_portion_g": foods.filter(solver_max_portion_g__isnull=True).count(),
        "solver_portion_step_g": foods.filter(solver_portion_step_g__isnull=True).count(),
        "food_form": foods.filter(food_form=CatalogFood.FOOD_FORM_UNKNOWN).count(),
        "functional_roles": foods.filter(functional_roles=[]).count(),
        "meal_affinities": foods.filter(meal_affinities=[]).count(),
        "preparation_effort": foods.filter(preparation_effort=CatalogFood.PREPARATION_EFFORT_UNKNOWN).count(),
        "cost_band": foods.filter(cost_band=CatalogFood.COST_BAND_UNKNOWN).count(),
    }
    client_gaps = {}
    requirements = CatalogCapabilityDefinition.objects.filter(
        client_requirements__is_active=True,
        client_requirements__is_required=True,
        is_active=True,
    ).distinct()
    for definition in requirements:
        assessed_ids = CatalogFoodCapability.objects.filter(
            definition=definition,
            assessment_status__in=(
                CatalogFoodCapability.STATUS_CONFIRMED_VALUE,
                CatalogFoodCapability.STATUS_CONFIRMED_NONE,
                CatalogFoodCapability.STATUS_NOT_APPLICABLE,
            ),
        ).values_list("catalog_food_id", flat=True)
        client_gaps[str(definition)] = foods.exclude(id__in=assessed_ids).count()
    return CatalogEnrichmentAudit(total=foods.count(), missing_counts=missing, client_requirement_gaps=client_gaps)


def create_enrichment_batch(
    *, foods: Iterable[CatalogFood], environment: str, reason: str, instruction: str = "", requested_by=None
) -> CatalogEnrichmentBatch:
    selected = sorted(foods, key=lambda food: food.pk)
    if not selected:
        raise CatalogEnrichmentError("At least one CatalogFood is required.")
    if environment not in {"staging", "production"}:
        raise CatalogEnrichmentError("Environment must be staging or production.")
    scope = {"catalog_food_ids": [food.pk for food in selected]}
    input_payload = [_food_snapshot(food) for food in selected]
    return CatalogEnrichmentBatch.objects.create(
        environment=environment,
        reason=reason.strip(),
        scope_payload=scope,
        instruction=instruction.strip(),
        requested_by=_authenticated_or_none(requested_by),
        input_sha256=canonical_sha256(input_payload),
    )


@transaction.atomic
def dry_run_enrichment_manifest(
    *, batch: CatalogEnrichmentBatch, manifest: dict[str, Any], actor=None
) -> CatalogEnrichmentDryRunResult:
    if batch.status not in {CatalogEnrichmentBatch.STATUS_DRAFT, CatalogEnrichmentBatch.STATUS_GENERATED,
                            CatalogEnrichmentBatch.STATUS_DRY_RUN_FAILED}:
        raise CatalogEnrichmentError(f"Batch status {batch.status} cannot be dry-run.")
    manifest_hash = canonical_sha256(manifest)
    top_errors = _validate_manifest_header(batch, manifest)
    rows = manifest.get("food_proposals", []) if isinstance(manifest, dict) else []
    CatalogFieldProposal.objects.filter(batch=batch).delete()
    valid = 0
    invalid = 0
    allowed_ids = set(batch.scope_payload.get("catalog_food_ids", []))
    foods = {food.pk: food for food in CatalogFood.objects.filter(pk__in=allowed_ids).prefetch_related("portions")}

    for row in rows:
        food = foods.get(row.get("catalog_food_id"))
        for change in row.get("changes", []):
            errors = list(top_errors)
            if food is None:
                errors.append("catalog_food_id is outside the batch scope or no longer exists")
                continue
            errors.extend(_validate_change(food, row, change))
            proposal = _build_proposal(batch=batch, food=food, row=row, change=change, errors=errors)
            proposal.save()
            if errors:
                invalid += 1
            else:
                valid += 1

    batch.manifest_sha256 = manifest_hash
    batch.manifest_payload = manifest
    batch.total_proposals = valid + invalid
    batch.valid_proposals = valid
    batch.failed_proposals = invalid
    batch.dry_run_at = timezone.now()
    batch.status = CatalogEnrichmentBatch.STATUS_DRY_RUN_VALID if not invalid and valid else CatalogEnrichmentBatch.STATUS_DRY_RUN_FAILED
    batch.save(update_fields=[
        "manifest_sha256", "manifest_payload", "total_proposals", "valid_proposals",
        "failed_proposals", "dry_run_at", "status", "updated_at",
    ])
    return CatalogEnrichmentDryRunResult(batch=batch, total=valid + invalid, valid=valid, invalid=invalid)


@transaction.atomic
def apply_enrichment_batch(
    *, batch: CatalogEnrichmentBatch, manifest: dict[str, Any], actor=None, reason: str, now=None,
    ttl: timedelta = DEFAULT_DRY_RUN_TTL,
) -> CatalogEnrichmentBatch:
    current_time = now or timezone.now()
    if batch.status != CatalogEnrichmentBatch.STATUS_DRY_RUN_VALID:
        raise CatalogEnrichmentError("Batch must have a valid dry-run before apply.")
    if not reason.strip():
        raise CatalogEnrichmentError("An apply reason is required.")
    if batch.manifest_sha256 != canonical_sha256(manifest):
        raise CatalogEnrichmentError("Manifest does not match the dry-run.")
    if batch.dry_run_at is None or batch.dry_run_at < current_time - ttl:
        raise CatalogEnrichmentError("The enrichment dry-run has expired.")

    proposals = list(batch.proposals.select_related("catalog_food", "capability_definition").order_by("id"))
    locked_foods = {
        food.pk: food
        for food in CatalogFood.objects.select_for_update().filter(
            pk__in={proposal.catalog_food_id for proposal in proposals}
        )
    }
    for proposal in proposals:
        food = locked_foods[proposal.catalog_food_id]
        if food.updated_at != proposal.expected_food_updated_at:
            raise CatalogEnrichmentError(f"CatalogFood {food.pk} changed after dry-run.")
    for proposal in proposals:
        food = locked_foods[proposal.catalog_food_id]
        before_timestamp = food.updated_at
        before = _json_value(_read_value(food, proposal))
        _write_value(food, proposal, actor=actor)
        food.refresh_from_db(fields=["updated_at"])
        CatalogEnrichmentChange.objects.create(
            batch=batch, proposal=proposal, catalog_food=food, field_name=proposal.field_name,
            action=CatalogEnrichmentChange.ACTION_APPLY, value_before=before,
            value_after=proposal.proposed_value, food_updated_at_before=before_timestamp,
            food_updated_at_after=food.updated_at, actor=_authenticated_or_none(actor), reason=reason.strip(),
        )
        proposal.status = CatalogFieldProposal.STATUS_APPLIED
        proposal.reviewed_by = _authenticated_or_none(actor)
        proposal.reviewed_at = current_time
        proposal.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

    batch.status = CatalogEnrichmentBatch.STATUS_APPLIED
    batch.applied_proposals = len(proposals)
    batch.applied_by = _authenticated_or_none(actor)
    batch.approved_at = current_time
    batch.applied_at = current_time
    batch.save(update_fields=["status", "applied_proposals", "applied_by", "approved_at", "applied_at", "updated_at"])
    return batch


@transaction.atomic
def revert_enrichment_batch(*, batch: CatalogEnrichmentBatch, actor=None, reason: str) -> CatalogEnrichmentBatch:
    if batch.status != CatalogEnrichmentBatch.STATUS_APPLIED:
        raise CatalogEnrichmentError("Only an applied batch can be reverted.")
    if not reason.strip():
        raise CatalogEnrichmentError("A revert reason is required.")
    applied_changes = list(batch.changes.filter(action=CatalogEnrichmentChange.ACTION_APPLY).select_related("proposal"))
    latest_by_food = {}
    for change in applied_changes:
        latest_by_food[change.catalog_food_id] = change
    locked_foods = {
        food.pk: food
        for food in CatalogFood.objects.select_for_update().filter(pk__in=latest_by_food)
    }
    for food_id, latest in latest_by_food.items():
        if locked_foods[food_id].updated_at != latest.food_updated_at_after:
            raise CatalogEnrichmentError(f"CatalogFood {food_id} changed after this batch; safe revert is blocked.")
    for change in reversed(applied_changes):
        food = locked_foods[change.catalog_food_id]
        before_timestamp = food.updated_at
        _write_raw_value(food, change.proposal, change.value_before, actor=actor)
        food.refresh_from_db(fields=["updated_at"])
        CatalogEnrichmentChange.objects.create(
            batch=batch, proposal=change.proposal, catalog_food=food, field_name=change.field_name,
            action=CatalogEnrichmentChange.ACTION_REVERT, value_before=change.value_after,
            value_after=change.value_before, food_updated_at_before=before_timestamp,
            food_updated_at_after=food.updated_at, actor=_authenticated_or_none(actor), reason=reason.strip(),
        )
    batch.status = CatalogEnrichmentBatch.STATUS_REVERTED
    batch.reverted_at = timezone.now()
    batch.save(update_fields=["status", "reverted_at", "updated_at"])
    return batch


def _validate_manifest_header(batch, manifest) -> tuple[str, ...]:
    errors = []
    if not isinstance(manifest, dict):
        return ("manifest must be an object",)
    if manifest.get("contract_version") != CONTRACT_VERSION:
        errors.append(f"contract_version must be {CONTRACT_VERSION}")
    if str(manifest.get("batch_ref")) != str(batch.batch_ref):
        errors.append("batch_ref does not match")
    if not isinstance(manifest.get("food_proposals"), list):
        errors.append("food_proposals must be a list")
    return tuple(errors)


def _validate_change(food, row, change) -> tuple[str, ...]:
    errors = []
    field_name = str(change.get("field_name", ""))
    capability_key = change.get("capability_key")
    if field_name not in ALLOWED_CATALOG_FIELDS and not capability_key:
        errors.append(f"field is not enrichable: {field_name}")
    expected = str(row.get("expected_updated_at", ""))
    if expected != food.updated_at.isoformat():
        errors.append("expected_updated_at does not match current CatalogFood")
    if not str(change.get("rationale", "")).strip():
        errors.append("rationale is required")
    try:
        confidence = Decimal(str(change.get("confidence")))
        if confidence < 0 or confidence > 100:
            errors.append("confidence must be between 0 and 100")
    except (InvalidOperation, TypeError):
        errors.append("confidence must be numeric")
    if field_name in DECIMAL_FIELDS:
        try:
            value = Decimal(str(change.get("proposed_value")))
            if value <= 0:
                errors.append(f"{field_name} must be positive")
        except (InvalidOperation, TypeError):
            errors.append(f"{field_name} must be decimal")
    elif field_name in LIST_FIELDS and not isinstance(change.get("proposed_value"), list):
        errors.append(f"{field_name} must be a list")
    elif field_name == "solver_enabled" and not isinstance(change.get("proposed_value"), bool):
        errors.append("solver_enabled must be boolean")
    elif field_name in CHOICE_FIELDS and change.get("proposed_value") not in CHOICE_FIELDS[field_name]:
        errors.append(f"unsupported {field_name} value")
    if field_name in DECIMAL_FIELDS:
        errors.extend(_validate_portion_triplet(food, row))
    return tuple(dict.fromkeys(errors))


def _validate_portion_triplet(food, row) -> tuple[str, ...]:
    values = {
        "solver_min_portion_g": food.solver_min_portion_g,
        "solver_max_portion_g": food.solver_max_portion_g,
        "solver_portion_step_g": food.solver_portion_step_g,
    }
    for change in row.get("changes", []):
        if change.get("field_name") in values:
            try:
                values[change["field_name"]] = Decimal(str(change.get("proposed_value")))
            except (InvalidOperation, TypeError):
                return ()
    minimum, maximum, step = values.values()
    errors = []
    if minimum is not None and maximum is not None and minimum > maximum:
        errors.append("solver minimum cannot exceed maximum")
    default = food.portions.filter(is_default=True).order_by("id").first()
    if default and minimum is not None and minimum > default.grams:
        errors.append("solver minimum cannot exceed default portion")
    if default and maximum is not None and maximum < default.grams:
        errors.append("solver maximum cannot be below default portion")
    profile_key = row.get("profile_key", "")
    if profile_key and None not in (minimum, maximum, step):
        errors.extend(validate_profile_portions(profile_key, minimum=minimum, maximum=maximum, step=step))
    return tuple(errors)


def _build_proposal(*, batch, food, row, change, errors):
    capability = None
    if change.get("capability_key"):
        capability = CatalogCapabilityDefinition.objects.filter(
            key=change["capability_key"], schema_version=change.get("capability_version", "v1"), is_active=True
        ).first()
        if capability is None:
            errors.append("active capability definition not found")
    field_name = change.get("field_name") or (f"capability:{capability}" if capability else "")
    return CatalogFieldProposal(
        batch=batch, catalog_food=food, field_name=field_name, capability_definition=capability,
        expected_food_updated_at=food.updated_at, current_value=_json_value(_read_raw_value(food, field_name, capability)),
        proposed_value=change.get("proposed_value"), nature=change.get("nature", "operational"),
        provenance=change.get("provenance", ["internal_policy", "ai_assisted"]),
        consumers=change.get("consumers", []), maturity=change.get("maturity", "candidate"),
        generation_method=change.get("generation_method", "codex_assisted"),
        authority_requirement=change.get("authority_requirement", "internal_review"),
        risk_level=change.get("risk_level", "medium"),
        assessment_status=change.get("assessment_status", "proposed"), profile_key=row.get("profile_key", ""),
        policy_version=change.get("policy_version", batch.policy_version), rationale=change.get("rationale", ""),
        confidence=change.get("confidence", 0), evidence_references=change.get("evidence_references", []),
        validation_errors=errors, status=CatalogFieldProposal.STATUS_INVALID if errors else CatalogFieldProposal.STATUS_VALID,
    )


def _read_raw_value(food, field_name, capability=None):
    if capability:
        entry = CatalogFoodCapability.objects.filter(catalog_food=food, definition=capability).first()
        if entry is None:
            return {"__capability_state__": "absent"}
        return {
            "__capability_state__": "present",
            "value": entry.value,
            "assessment_status": entry.assessment_status,
            "provenance": entry.provenance,
            "generation_method": entry.generation_method,
            "evidence_references": entry.evidence_references,
            "confidence": str(entry.confidence) if entry.confidence is not None else None,
            "policy_version": entry.policy_version,
            "scope": entry.scope,
        }
    if field_name == "default_portion_g":
        return food.portions.filter(is_default=True).order_by("id").values_list("grams", flat=True).first()
    return getattr(food, field_name)


def _read_value(food, proposal):
    return _read_raw_value(food, proposal.field_name, proposal.capability_definition)


def _write_value(food, proposal, *, actor=None):
    _write_raw_value(food, proposal, proposal.proposed_value, actor=actor)


def _write_raw_value(food, proposal, value, *, actor=None):
    if proposal.capability_definition_id:
        if isinstance(value, dict) and value.get("__capability_state__") == "absent":
            CatalogFoodCapability.objects.filter(
                catalog_food=food, definition=proposal.capability_definition
            ).delete()
            food.save(update_fields=["updated_at"])
            return
        if isinstance(value, dict) and value.get("__capability_state__") == "present":
            CatalogFoodCapability.objects.update_or_create(
                catalog_food=food,
                definition=proposal.capability_definition,
                defaults={
                    "value": value.get("value"),
                    "assessment_status": value.get("assessment_status", CatalogFoodCapability.STATUS_UNASSESSED),
                    "provenance": value.get("provenance", []),
                    "generation_method": value.get("generation_method", ""),
                    "evidence_references": value.get("evidence_references", []),
                    "confidence": value.get("confidence"),
                    "policy_version": value.get("policy_version", ""),
                    "scope": value.get("scope", {}),
                    "decided_by": _authenticated_or_none(actor),
                },
            )
            food.save(update_fields=["updated_at"])
            return
        CatalogFoodCapability.objects.update_or_create(
            catalog_food=food, definition=proposal.capability_definition,
            defaults={"value": value, "assessment_status": CatalogFoodCapability.STATUS_CONFIRMED_VALUE,
                      "provenance": proposal.provenance, "generation_method": proposal.generation_method,
                      "confidence": proposal.confidence, "policy_version": proposal.policy_version,
                      "decided_by": _authenticated_or_none(actor), "valid_from": timezone.now()},
        )
        food.save(update_fields=["updated_at"])
        return
    if proposal.field_name == "default_portion_g":
        current = food.portions.filter(is_default=True).order_by("id").first()
        if value is None:
            if current is not None:
                current.delete()
        else:
            grams = Decimal(str(value))
            if current is None:
                CatalogFoodPortion.objects.create(
                    catalog_food=food,
                    label="porción",
                    grams=grams,
                    source="internal_policy_ai_assisted",
                    is_default=True,
                )
            else:
                current.grams = grams
                current.source = "internal_policy_ai_assisted"
                current.save(update_fields=["grams", "source", "updated_at"])
        food.save(update_fields=["updated_at"])
        return
    if proposal.field_name in DECIMAL_FIELDS and value is not None:
        value = Decimal(str(value))
    setattr(food, proposal.field_name, value)
    food.save(update_fields=[proposal.field_name, "updated_at"])


def _food_snapshot(food):
    direct_fields = ALLOWED_CATALOG_FIELDS - {"default_portion_g"}
    return {
        "id": food.pk, "updated_at": food.updated_at.isoformat(), "display_name": food.display_name,
        "food_group": food.food_group, "food_subgroup": food.food_subgroup,
        "preparation_state": food.preparation_state,
        "default_portion_g": str(food.portions.filter(is_default=True).values_list("grams", flat=True).first() or ""),
        **{field: _json_value(getattr(food, field)) for field in sorted(direct_fields)},
    }


def _json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    return value


def _authenticated_or_none(user):
    return user if user is not None and getattr(user, "is_authenticated", False) else None


__all__ = [
    "ALLOWED_CATALOG_FIELDS", "CONTRACT_VERSION", "CatalogEnrichmentError",
    "apply_enrichment_batch", "audit_catalog_enrichment", "canonical_sha256",
    "create_enrichment_batch", "dry_run_enrichment_manifest", "revert_enrichment_batch",
]
