"""Django orchestration for compact, governed catalog readiness batches."""

from __future__ import annotations

from django.db.models import Exists, OuterRef, Q
from django.db.models.query import prefetch_related_objects

from food_catalog.application.readiness_pipeline import (
    MANDATORY_INTERNAL_FIELDS,
    READINESS_POLICY_VERSION,
    decide_readiness,
)
from food_catalog.infrastructure.enrichment import (
    CONTRACT_VERSION,
    create_enrichment_batch,
    dry_run_enrichment_manifest,
)
from food_catalog.models import CatalogFood, CatalogFoodPortion, CatalogFoodSource


def prepare_readiness_batch(*, foods, environment: str, reason: str, requested_by=None):
    selected = sorted(foods, key=lambda food: food.pk)
    prefetch_related_objects(selected, "portions", "sources")
    if not selected:
        raise ValueError("No catalog foods selected for readiness.")
    batch = create_enrichment_batch(
        foods=selected,
        environment=environment,
        reason=reason,
        instruction=(
            "Complete every missing mandatory internal field from versioned policy and source portions; "
            "leave pending review; do not publish or snapshot."
        ),
        requested_by=requested_by,
    )
    batch.policy_version = READINESS_POLICY_VERSION
    batch.save(update_fields=["policy_version", "updated_at"])
    rows = []
    skipped = []
    for food in selected:
        source = _trusted_source(food)
        if source is None:
            skipped.append({"catalog_food_id": food.pk, "reason": "source_incomplete"})
            continue
        try:
            decision = decide_readiness(food, source)
        except ValueError as exc:
            skipped.append({"catalog_food_id": food.pk, "reason": str(exc)})
            continue
        changes = _missing_changes(food, decision)
        if changes:
            rows.append({
                "catalog_food_id": food.pk,
                "expected_updated_at": food.updated_at.isoformat(),
                "profile_key": decision.profile_key,
                "changes": changes,
            })
    manifest = {
        "batch_ref": str(batch.batch_ref),
        "contract_version": CONTRACT_VERSION,
        "food_proposals": rows,
    }
    result = dry_run_enrichment_manifest(batch=batch, manifest=manifest, actor=requested_by)
    return batch, result, skipped


def source_complete_queryset(queryset=None):
    foods = queryset if queryset is not None else CatalogFood.objects.all()
    trusted_sources = CatalogFoodSource.objects.filter(
        catalog_food_id=OuterRef("pk"),
        license_status=CatalogFoodSource.LICENSE_ALLOWED,
    ).exclude(source_name="").exclude(source_food_id="")
    return foods.annotate(has_trusted_source=Exists(trusted_sources)).filter(has_trusted_source=True).distinct()


def readiness_incomplete_queryset(queryset=None):
    return source_complete_queryset(queryset).annotate(
        has_default_portion=Exists(
            CatalogFoodPortion.objects.filter(catalog_food_id=OuterRef("pk"), is_default=True)
        )
    ).filter(
        Q(has_default_portion=False)
        | Q(solver_min_portion_g__isnull=True)
        | Q(solver_max_portion_g__isnull=True)
        | Q(solver_portion_step_g__isnull=True)
        | Q(solver_enabled=False)
        | Q(food_form="unknown")
        | Q(functional_roles=[])
        | Q(meal_affinities=[])
        | Q(preparation_effort="unknown")
        | Q(cost_band="unknown")
    ).distinct()


def _trusted_source(food):
    return food.sources.filter(
        license_status=CatalogFoodSource.LICENSE_ALLOWED,
    ).exclude(source_name="").exclude(source_food_id="").order_by("id").first()


def _missing_changes(food, decision):
    default = food.portions.filter(is_default=True).order_by("id").first()
    values = {
        "default_portion_g": str(decision.default_portion_g),
        "solver_min_portion_g": str(decision.minimum_g),
        "solver_max_portion_g": str(decision.maximum_g),
        "solver_portion_step_g": str(decision.step_g),
        "solver_enabled": True,
        "food_form": decision.food_form,
        "functional_roles": list(decision.functional_roles),
        "meal_affinities": list(decision.meal_affinities),
        "preparation_effort": decision.preparation_effort,
        "cost_band": decision.cost_band,
    }
    current = {
        "default_portion_g": default.grams if default else None,
        **{field: getattr(food, field) for field in MANDATORY_INTERNAL_FIELDS if field != "default_portion_g"},
    }
    changes = []
    for field_name in MANDATORY_INTERNAL_FIELDS:
        if not _is_missing(field_name, current[field_name]):
            continue
        external = field_name == "default_portion_g"
        changes.append({
            "field_name": field_name,
            "proposed_value": values[field_name],
            "nature": "operational" if field_name not in {"food_form", "functional_roles", "meal_affinities"} else "semantic",
            "provenance": (["external_evidence", "internal_policy", "ai_assisted"] if external
                           else ["internal_policy", "ai_assisted"]),
            "consumers": ["nutrition_solver", "admin_operations"],
            "maturity": "candidate",
            "generation_method": "codex_policy_assisted",
            "authority_requirement": "internal_review",
            "risk_level": "medium" if field_name in {
                "default_portion_g", "solver_min_portion_g", "solver_max_portion_g",
                "solver_portion_step_g", "solver_enabled", "cost_band",
            } else "low",
            "assessment_status": "proposed",
            "confidence": 94 if external else 88,
            "policy_version": READINESS_POLICY_VERSION,
            "rationale": _rationale(field_name, decision),
            "evidence_references": list(decision.evidence_references) if external else [],
        })
    return changes


def _is_missing(field_name, value):
    if field_name == "solver_enabled":
        return value is False
    if field_name in {"functional_roles", "meal_affinities"}:
        return not value
    if field_name in {"food_form", "preparation_effort", "cost_band"}:
        return value == "unknown"
    return value is None


def _rationale(field_name, decision):
    if field_name == "default_portion_g":
        return f"Medida doméstica de la fuente: {decision.portion_label} = {decision.default_portion_g} g."
    if field_name.startswith("solver_"):
        return f"Decisión por alimento dentro del perfil versionado {decision.profile_key}."
    return "Clasificación interna propuesta por Codex según grupo, preparación y uso culinario."


__all__ = ["prepare_readiness_batch", "readiness_incomplete_queryset", "source_complete_queryset"]
