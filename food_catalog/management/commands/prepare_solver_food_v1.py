"""Prepare an auditable solver food curation batch from the versioned first pass."""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.enrichment import (
    CONTRACT_VERSION,
    create_enrichment_batch,
    dry_run_enrichment_manifest,
)
from food_catalog.models import CatalogFood

DATASET = Path(__file__).resolve().parents[2] / "data/curation/solver_219_first_pass_v1.csv"
POLICY_VERSION = "myscoope.solver_food_curation.v1"
CATALOG_VERSION = "2026-11-solver-v1"
KNOWN_OPERATIONAL_DEFAULTS = {
    "Leche semidescremada": Decimal("240"),
    "Leche entera": Decimal("240"),
    "Aceite de oliva": Decimal("15"),
}


class Command(BaseCommand):
    help = "Validate 219 source-linked foods and prepare a reversible enrichment batch. Does not apply or publish."

    def add_arguments(self, parser):
        parser.add_argument("--environment", required=True, choices=("staging", "production"))
        parser.add_argument("--dataset", type=Path, default=DATASET)

    def handle(self, *args, **options):
        with options["dataset"].open(newline="") as file:
            rows = list(csv.DictReader(file))
        source_ids = [row["source_food_id"] for row in rows]
        if len(rows) != 219 or len(set(source_ids)) != 219 or not all(source_ids):
            raise CommandError("The dataset must contain 219 unique source food identifiers.")
        candidates = list(CatalogFood.objects.filter(sources__source_food_id__in=source_ids).distinct().prefetch_related("sources", "portions"))
        by_source = {}
        for food in candidates:
            for source in food.sources.all():
                by_source.setdefault(source.source_food_id, []).append((food, source))
        foods = []
        prepared_rows = []
        for entry in rows:
            matches = [(food, source) for food, source in by_source.get(entry["source_food_id"], [])
                       if food.display_name == entry["display_name"]]
            if len(matches) != 1:
                raise CommandError(f"Expected one food for source {entry['source_food_id']} and {entry['display_name']}; found {len(matches)}.")
            food, source = matches[0]
            foods.append(food)
            if source.license_status != source.LICENSE_ALLOWED or source.source_url != entry["source_url"]:
                raise CommandError(f"Source mismatch for {entry['display_name']}")
            if food.display_name != entry["display_name"] or food.preparation_state != entry["preparation_state"]:
                raise CommandError(f"Identity or preparation mismatch for {entry['display_name']}")
            default = next((portion for portion in food.portions.all() if portion.is_default), None)
            allowed_defaults = {Decimal(entry["default_portion_g"])}
            if entry["display_name"] in KNOWN_OPERATIONAL_DEFAULTS:
                allowed_defaults.add(KNOWN_OPERATIONAL_DEFAULTS[entry["display_name"]])
            if default is None or default.grams not in allowed_defaults:
                raise CommandError(f"Default portion changed for {entry['display_name']}")
            selected = default.grams if default.grams != Decimal(entry["default_portion_g"]) else Decimal(entry["proposed_default_portion_g"])
            if selected != default.grams and not any(portion.grams == selected for portion in food.portions.all()):
                if entry["display_name"] not in {"Higo seco", "Ciruela seca", "Damasco seco"} or entry["proposed_default_portion_label"] != "1/4 taza":
                    raise CommandError(f"Proposed portion has no source option for {entry['display_name']}")
            if entry["solver_use"] not in {"direct_candidate", "preparation_required", "recipe_component"}:
                raise CommandError(f"Unknown solver use for {entry['display_name']}")
            if entry["solver_use"] == "direct_candidate" and entry["preparation_state"] == "dry" and food.food_group not in {"fruits_and_fruit_juices", "cereals", "fats"}:
                raise CommandError(f"Dry direct candidate requires explicit review: {entry['display_name']}")
            changes = _changes(food, entry, default, selected=selected)
            if changes:
                prepared_rows.append({"catalog_food_id": food.pk, "expected_updated_at": food.updated_at.isoformat(), "changes": changes})
        if len({food.pk for food in foods}) != 219:
            raise CommandError("The source identifiers resolve to fewer than 219 distinct foods.")
        batch = create_enrichment_batch(
            foods=foods,
            environment=options["environment"],
            reason="First-pass solver curation for the original 219-food catalog",
            instruction="Review the exact dry-run, apply to the catalog authority, then build a new release and materialize it in consumers.",
        )
        batch.policy_version = POLICY_VERSION
        batch.save(update_fields=["policy_version", "updated_at"])
        manifest = {"batch_ref": str(batch.batch_ref), "contract_version": CONTRACT_VERSION, "food_proposals": prepared_rows}
        result = dry_run_enrichment_manifest(batch=batch, manifest=manifest)
        self.stdout.write(json.dumps({
            "batch_ref": str(batch.batch_ref), "foods": len(foods), "changed_foods": len(prepared_rows),
            "proposals": result.total, "valid": result.valid, "invalid": result.invalid,
            "solver_enabled_after_apply": sum(entry["solver_use"] == "direct_candidate" for entry in rows),
            "preparation_or_recipe_only": sum(entry["solver_use"] != "direct_candidate" for entry in rows),
        }, sort_keys=True))
        if result.invalid:
            raise CommandError("Dry-run contains invalid proposals; no changes applied.")


def _changes(food, entry, default, *, selected):
    source_option_exists = any(portion.grams == selected for portion in food.portions.all())
    base_selected = Decimal(entry["proposed_default_portion_g"])
    minimum = Decimal(entry["proposed_min_g"])
    maximum = Decimal(entry["proposed_max_g"])
    if selected != base_selected:
        minimum = selected * Decimal("0.5")
        maximum = selected if entry["proposed_food_form"] == "condiment" else selected * 2
    target = {
        "default_portion_g": (
            {"grams": str(selected), "label": entry["proposed_default_portion_label"],
             "source": entry["proposed_default_portion_source"]}
            if not source_option_exists else selected
        ),
        "solver_min_portion_g": minimum,
        "solver_max_portion_g": maximum,
        "solver_portion_step_g": Decimal(entry["proposed_step_g"]),
        "food_form": entry["proposed_food_form"],
        "functional_roles": entry["proposed_functional_roles"].split("|"),
        "meal_affinities": entry["proposed_meal_affinities"].split("|"),
        "dietary_tags": entry["proposed_dietary_tags"].split("|") if entry["proposed_dietary_tags"] else [],
        "solver_enabled": entry["solver_use"] == "direct_candidate",
        "catalog_version": CATALOG_VERSION,
    }
    if entry["positive_allergen_evidence"]:
        target["allergens"] = [entry["positive_allergen_evidence"]]
    current = {name: getattr(food, name) for name in target if name != "default_portion_g"}
    current["default_portion_g"] = default.grams
    changes = []
    for name, value in target.items():
        if current[name] == value or name == "default_portion_g" and current[name] == selected:
            continue
        is_portion = name in {"default_portion_g", "solver_min_portion_g", "solver_max_portion_g", "solver_portion_step_g"}
        changes.append({
            "field_name": name, "proposed_value": str(value) if isinstance(value, Decimal) else value,
            "nature": "operational" if is_portion or name == "solver_enabled" else "semantic",
            "provenance": ["external_evidence", "internal_policy"] if name == "default_portion_g" else ["internal_policy"],
            "consumers": ["nutrition_solver"], "maturity": "candidate",
            "generation_method": "versioned_catalog_policy", "authority_requirement": "internal_review",
            "risk_level": "medium" if is_portion or name in {"solver_enabled", "allergens"} else "low",
            "assessment_status": "proposed", "confidence": 90 if name == "default_portion_g" else 75,
            "policy_version": POLICY_VERSION,
            "rationale": entry["default_change_reason"] if name == "default_portion_g" else f"{entry['solver_use']}: {entry['review_reason'] or 'Versioned first-pass catalog classification.'}",
            "evidence_references": [entry["source_url"]] if name in {"default_portion_g", "allergens"} and entry["source_url"] else [],
        })
    return changes
