"""Stable read-only audit contract for Food Catalog readiness."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from django.db.models import Prefetch

from food_catalog.application.readiness_pipeline import MANDATORY_INTERNAL_FIELDS
from food_catalog.application.solver_readiness import MIN_SOLVER_QUALITY_SCORE
from food_catalog.infrastructure.readiness_pipeline import source_complete_queryset
from food_catalog.models import CatalogFood, CatalogFoodPortion


@dataclass(frozen=True)
class ReadinessAudit:
    total_catalog_foods: int
    source_complete: int
    source_incomplete: int
    internally_complete: int
    internally_incomplete: int
    pending_review: int
    published: int
    missing_counts: dict[str, int]
    invalid_solver_food_ids: tuple[int, ...]
    foods: tuple[dict, ...]

    @property
    def passes(self):
        return self.internally_incomplete == 0 and not self.invalid_solver_food_ids

    def as_dict(self, *, include_foods=False):
        payload = asdict(self)
        payload["passes"] = self.passes
        if not include_foods:
            payload.pop("foods")
        return payload


def audit_catalog_readiness(queryset=None) -> ReadinessAudit:
    all_foods = queryset if queryset is not None else CatalogFood.objects.all()
    eligible = source_complete_queryset(all_foods).prefetch_related(
        Prefetch("portions", queryset=CatalogFoodPortion.objects.order_by("id"), to_attr="audit_portions"),
        "sources",
    ).order_by("id")
    foods = list(eligible)
    missing_counts = dict.fromkeys(MANDATORY_INTERNAL_FIELDS, 0)
    invalid_solver_ids = []
    rows = []

    for food in foods:
        default = next((portion for portion in food.audit_portions if portion.is_default), None)
        values = {
            "default_portion_g": default.grams if default else None,
            **{
                field: getattr(food, field)
                for field in MANDATORY_INTERNAL_FIELDS
                if field != "default_portion_g"
            },
        }
        missing = [field for field, value in values.items() if _is_missing(field, value)]
        for field in missing:
            missing_counts[field] += 1
        solver_errors = _solver_errors(food, default)
        if solver_errors:
            invalid_solver_ids.append(food.pk)
        trusted_source = next((
            source for source in food.sources.all()
            if source.license_status == source.LICENSE_ALLOWED and source.source_name and source.source_food_id
        ), None)
        rows.append({
            "catalog_food_id": food.pk,
            "display_name": food.display_name,
            "status": food.status,
            "published": bool(food.published_at),
            "source": {
                "name": trusted_source.source_name,
                "food_id": trusted_source.source_food_id,
                "url": trusted_source.source_url,
            } if trusted_source else None,
            "missing_fields": missing,
            "solver_errors": list(solver_errors),
        })

    incomplete_ids = {row["catalog_food_id"] for row in rows if row["missing_fields"]}
    source_complete = len(foods)
    return ReadinessAudit(
        total_catalog_foods=all_foods.distinct().count(),
        source_complete=source_complete,
        source_incomplete=all_foods.exclude(pk__in=[food.pk for food in foods]).distinct().count(),
        internally_complete=source_complete - len(incomplete_ids),
        internally_incomplete=len(incomplete_ids),
        pending_review=sum(food.status == CatalogFood.STATUS_PENDING_REVIEW for food in foods),
        published=sum(bool(food.published_at) for food in foods),
        missing_counts=missing_counts,
        invalid_solver_food_ids=tuple(invalid_solver_ids),
        foods=tuple(rows),
    )


def _is_missing(field_name, value):
    if field_name == "solver_enabled":
        return value is False
    if field_name in {"functional_roles", "meal_affinities"}:
        return not value
    if field_name in {"food_form", "preparation_effort", "cost_band"}:
        return value == "unknown"
    return value is None


def _solver_errors(food, default):
    if not food.solver_enabled:
        return ()
    errors = []
    if food.data_quality_score < MIN_SOLVER_QUALITY_SCORE:
        errors.append(f"data_quality_score must be at least {MIN_SOLVER_QUALITY_SCORE}")
    if not food.food_group.strip():
        errors.append("food_group is required for solver-enabled foods")
    if food.preparation_state == CatalogFood.PREPARATION_UNKNOWN:
        errors.append("preparation_state must be explicit for solver-enabled foods")
    if default is None:
        errors.append("a default portion is required for solver-enabled foods")
    minimum = food.solver_min_portion_g
    maximum = food.solver_max_portion_g
    step = food.solver_portion_step_g
    if minimum is None:
        errors.append("minimum solver portion is required")
    if maximum is None:
        errors.append("maximum solver portion is required")
    if step is None:
        errors.append("portion step is required")
    if minimum is not None and maximum is not None and minimum > maximum:
        errors.append("minimum solver portion cannot exceed maximum portion")
    if default is not None and minimum is not None and minimum > default.grams:
        errors.append("minimum solver portion cannot exceed default portion")
    if default is not None and maximum is not None and maximum < default.grams:
        errors.append("maximum solver portion cannot be lower than default portion")
    if step is not None and step <= 0:
        errors.append("portion step must be positive")
    return tuple(errors)


__all__ = ["ReadinessAudit", "audit_catalog_readiness"]
