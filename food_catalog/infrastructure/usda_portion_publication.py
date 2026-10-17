"""Prepare the reviewed USDA SR Legacy catalog wave for publication."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from food_catalog.application.curation import transition_catalog_food_status
from food_catalog.application.publication import check_catalog_food_publishable
from food_catalog.application.readiness_pipeline import _portion_rank
from food_catalog.infrastructure.source_portion_backfill import load_portion_evidence
from food_catalog.models import CatalogFood, CatalogFoodPortion, CatalogFoodSource

PORTION_SOURCE = "USDA FoodData Central SR Legacy 2018-04"
FALLBACK_SOURCE = "Base nutricional USDA SR Legacy por 100 g"


@dataclass(frozen=True)
class UsdaPublicationPreparationResult:
    foods: int
    official_foods: int
    fallback_foods: int
    portion_rows: int
    changed_foods: int


def prepare_usda_sr_legacy_publication(
    *,
    apply: bool = False,
    actor=None,
    reason: str = "",
) -> UsdaPublicationPreparationResult:
    """Add traceable portions and verify the complete pending USDA wave."""

    normalized_reason = str(reason or "").strip()
    if apply and not normalized_reason:
        raise ValueError("reason is required when applying publication preparation")
    if apply and not getattr(actor, "is_authenticated", False):
        raise ValueError("an authenticated actor is required when applying publication preparation")

    evidence = load_portion_evidence()
    foods = list(
        CatalogFood.objects.filter(
            status=CatalogFood.STATUS_PENDING_REVIEW,
            sources__source_type=CatalogFood.SOURCE_USDA,
            sources__source_dataset="sr_legacy",
            sources__source_version=str(evidence["version"]),
        )
        .prefetch_related("sources", "portions")
        .order_by("catalog_ref", "id")
        .distinct()
    )
    if not foods:
        return UsdaPublicationPreparationResult(0, 0, 0, 0, 0)

    plans = [_build_plan(food, evidence) for food in foods]
    blocked = [plan["error"] for plan in plans if plan.get("error")]
    if blocked:
        raise ValueError("publication preparation blocked:\n- " + "\n- ".join(blocked))

    result = UsdaPublicationPreparationResult(
        foods=len(plans),
        official_foods=sum(not plan["is_fallback"] for plan in plans),
        fallback_foods=sum(plan["is_fallback"] for plan in plans),
        portion_rows=sum(len(plan["rows"]) for plan in plans),
        changed_foods=len(plans) if apply else 0,
    )
    if not apply:
        return result

    with transaction.atomic():
        for plan in plans:
            food = CatalogFood.objects.select_for_update().get(pk=plan["food"].pk)
            source = CatalogFoodSource.objects.select_for_update().get(pk=plan["source"].pk)
            _record_evidence(source=source, plan=plan, evidence=evidence, reason=normalized_reason)
            _sync_portions(food=food, plan=plan)
            review = transition_catalog_food_status(
                food,
                CatalogFood.STATUS_REVIEWED,
                user=actor,
            )
            if not review.changed:
                raise ValueError(f"{food.display_name}: review transition failed: {review.errors}")
            verification = transition_catalog_food_status(
                food,
                CatalogFood.STATUS_VERIFIED,
                user=actor,
            )
            if not verification.changed:
                raise ValueError(
                    f"{food.display_name}: verification transition failed: {verification.errors}"
                )
            publication = check_catalog_food_publishable(food)
            if not publication.can_publish:
                raise ValueError(
                    f"{food.display_name}: publication validation failed: {publication.errors}"
                )

    return result


def _build_plan(food, evidence):
    source = next(
        (
            item
            for item in food.sources.all()
            if item.source_type == CatalogFood.SOURCE_USDA
            and item.source_dataset == "sr_legacy"
            and item.source_version == str(evidence["version"])
            and item.license_status == CatalogFoodSource.LICENSE_ALLOWED
        ),
        None,
    )
    if source is None:
        return {"error": f"{food.display_name}: allowed USDA SR Legacy source missing"}

    source_food_id = source.source_food_id
    rows = list(evidence.get("portions", {}).get(source_food_id, ()))
    is_fallback = False
    if not rows:
        fallback = evidence.get("fallbacks", {}).get(source_food_id)
        if fallback:
            rows = [fallback]
            is_fallback = True
    if not rows:
        return {"error": f"{food.display_name}: source portion evidence missing"}

    original_status = food.status
    food.status = CatalogFood.STATUS_REVIEWED
    errors = tuple(
        error
        for error in check_catalog_food_publishable(food).errors
        if error
        not in {
            "at least one serving/portion option is required",
            "one serving/portion option must be marked as default",
        }
    )
    food.status = original_status
    if errors:
        return {"error": f"{food.display_name}: {', '.join(errors)}"}

    return {
        "food": food,
        "source": source,
        "rows": rows,
        "is_fallback": is_fallback,
    }


def _record_evidence(*, source, plan, evidence, reason):
    payload = dict(source.evidence_payload or {})
    now = timezone.now()
    if plan["is_fallback"]:
        row = plan["rows"][0]
        payload["operational_portion_fallback"] = {
            "label": _portion_label(row),
            "grams": str(row["grams"]),
            "basis": str(row["rationale"]),
            "dataset": evidence["dataset"],
            "dataset_version": evidence["version"],
            "archive_url": evidence["archive_url"],
            "reason": reason,
            "applied_at": now.isoformat(),
        }
    else:
        payload["source_portions"] = [
            {key: row[key] for key in ("amount", "grams", "modifier", "measure_unit")}
            for row in plan["rows"]
        ]
        payload["source_portions_provenance"] = {
            "dataset": evidence["dataset"],
            "dataset_version": evidence["version"],
            "archive_url": evidence["archive_url"],
            "evidence_url": evidence["evidence_url_template"].format(
                fdc_id=source.source_food_id
            ),
            "reason": reason,
            "applied_at": now.isoformat(),
        }
    source.evidence_payload = payload
    source.last_checked_at = now
    source.save(update_fields=["evidence_payload", "last_checked_at"])


def _sync_portions(*, food, plan):
    existing_default = food.portions.filter(is_default=True).order_by("id").first()
    default_row = min(plan["rows"], key=_portion_rank)
    selected = None
    for row in plan["rows"]:
        portion, _ = CatalogFoodPortion.objects.update_or_create(
            catalog_food=food,
            label=_portion_label(row),
            defaults={
                "grams": Decimal(str(row["grams"])),
                "source": FALLBACK_SOURCE if plan["is_fallback"] else PORTION_SOURCE,
                "is_default": False,
            },
        )
        if row is default_row:
            selected = portion
    if existing_default is None and selected is not None:
        selected.is_default = True
        selected.save(update_fields=["is_default", "updated_at"])


def _portion_label(row) -> str:
    return " ".join(
        part for part in (str(row.get("amount", "")).strip(), str(row.get("modifier", "")).strip()) if part
    )


__all__ = ["UsdaPublicationPreparationResult", "prepare_usda_sr_legacy_publication"]
