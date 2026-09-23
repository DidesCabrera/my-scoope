"""Curation boundary and authorized operational snapshots for the culinary solver."""

import hashlib
import json
import unicodedata
from math import isfinite

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from notas.application.queries.solver_food_candidates import get_solver_food_candidate_queryset
from notas.domain.models import CulinaryVariant
from nutrition_solver.application.culinary_planner import CulinaryCandidate, Ingredient

GROUPS = {"protein", "starch", "fruit", "vegetable", "dairy", "fat", "legume", "other"}
RUBRIC_KEYS = {"compatible_ingredients", "appropriate_preparation", "reasonable_portions", "substitutions_checked"}


def normalized(value):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", str(value).lower())
                             if not unicodedata.combining(c)).split())


def _snapshot_ingredient(row, components, foods, seen, ids):
    if not isinstance(row, dict) or set(row) != {"component", "food_id", "minimum_g", "maximum_g", "step_g"}:
        raise ValueError("culinary_ingredient_invalid")
    component = row["component"]
    rule = components.get(component)
    food = foods.get(row["food_id"])
    if not rule or food is None or component in seen or food.pk in ids:
        raise ValueError("culinary_food_unavailable_or_duplicate")
    if set(rule) != {"group", "foods", "minimum_g", "maximum_g", "step_g"} or rule["group"] not in GROUPS:
        raise ValueError("culinary_component_rule_invalid")
    metadata = rule["foods"].get(str(food.pk))
    if not metadata or set(metadata) != {"species", "preparation_state"} or not metadata["species"]:
        raise ValueError("culinary_substitution_not_allowed")
    if food.preparation_state == "unknown" or metadata["preparation_state"] != food.preparation_state:
        raise ValueError("culinary_preparation_state_mismatch")
    for key in ("minimum_g", "maximum_g", "step_g"):
        for value in (row[key], rule[key]):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value <= 0:
                raise ValueError("culinary_portion_invalid")
    if not rule["minimum_g"] <= row["minimum_g"] <= row["maximum_g"] <= rule["maximum_g"] or row["step_g"] != rule["step_g"]:
        raise ValueError("culinary_portion_outside_template")
    if rule["group"] in {"fruit", "vegetable"} and row["minimum_g"] < 50:
        raise ValueError("culinary_produce_portion_too_small")
    for value in (food.protein, food.carbs, food.fat):
        if not isfinite(value) or value < 0:
            raise ValueError("culinary_nutrients_invalid")
    ingredient = Ingredient(food.pk, food.name, component, rule["group"], metadata["species"],
                                  row["minimum_g"], row["maximum_g"], row["step_g"],
                                  food.protein, food.carbs, food.fat)
    return ingredient, food


def _snapshot(variant, foods):
    template = variant.template
    rules = template.rules
    components = rules.get("components", {})
    if not template.preparation.strip() or not variant.preparation.strip() or not template.family:
        raise ValueError("culinary_preparation_and_family_required")
    if not template.meal_kinds or set(template.meal_kinds) - {"breakfast", "main", "snack", "dinner"}:
        raise ValueError("culinary_meal_kind_invalid")
    if not isinstance(components, dict) or not components or not isinstance(variant.ingredients, list):
        raise ValueError("culinary_components_required")
    if set(rules) - {"components", "ratios"}:
        raise ValueError("culinary_unknown_rule")
    if len(variant.ingredients) != len(components):
        raise ValueError("culinary_components_mismatch")
    ingredients, seen, ids, food_evidence = [], set(), set(), []
    for row in variant.ingredients:
        ingredient, food = _snapshot_ingredient(row, components, foods, seen, ids)
        component = ingredient.component
        ingredients.append(ingredient)
        seen.add(component)
        ids.add(food.pk)
        food_evidence.append({"id": food.pk, "protein": food.protein, "carbs": food.carbs, "fat": food.fat,
                              "preparation_state": food.preparation_state, "capabilities": food.solver_capabilities})
    ratios = rules.get("ratios", [])
    for ratio in ratios:
        if set(ratio) != {"left", "right", "minimum", "maximum"} or ratio["left"] not in seen or ratio["right"] not in seen:
            raise ValueError("culinary_ratio_invalid")
        if any(isinstance(ratio[key], bool) or not isinstance(ratio[key], (int, float)) or not isfinite(ratio[key]) for key in ("minimum", "maximum")):
            raise ValueError("culinary_ratio_invalid")
        if not 0 < ratio["minimum"] <= ratio["maximum"]:
            raise ValueError("culinary_ratio_invalid")
    evidence = {"template": template.pk, "version": template.version, "rules": rules,
                "family": template.family, "meal_kinds": template.meal_kinds,
                "template_preparation": template.preparation, "preparation": variant.preparation,
                "ingredients": variant.ingredients, "foods": food_evidence}
    digest = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
    return CulinaryCandidate(variant.pk, template.pk, template.family, variant.name, tuple(template.meal_kinds),
                             variant.preparation, tuple(ingredients), tuple(ratios), digest, variant.status)


@transaction.atomic
def validate_variant(*, user, variant_id, human_review=False, rubric=None):
    variant = CulinaryVariant.objects.select_for_update().select_related("template").get(pk=variant_id)
    if variant.template.owner_id != user.pk and not user.is_staff:
        raise ValueError("culinary_variant_not_allowed")
    foods = {food.pk: food for food in get_solver_food_candidate_queryset(user)}
    if variant.template.owner_id is None and any(not foods.get(row.get("food_id")) or not foods[row["food_id"]].is_global for row in variant.ingredients):
        raise ValueError("culinary_public_variant_requires_global_foods")
    candidate = _snapshot(variant, foods)
    if human_review:
        if not user.is_staff or not isinstance(rubric, dict) or set(rubric) != RUBRIC_KEYS or not all(value is True for value in rubric.values()):
            raise ValueError("culinary_human_rubric_required")
        variant.status = CulinaryVariant.HUMAN_VALIDATED
        variant.reviewed_by, variant.reviewed_at, variant.rubric = user, timezone.now(), rubric
    else:
        # Never downgrade or manufacture a human review.
        if variant.status == CulinaryVariant.HUMAN_VALIDATED:
            raise ValueError("culinary_human_review_requires_explicit_revalidation")
        variant.status = CulinaryVariant.RULE_VALIDATED
        variant.rubric = {"structural_rules_passed": True, "human_review_pending": True}
    variant.evidence_digest = candidate.evidence_digest
    variant.save()
    return variant


def load_culinary_candidates(*, user, brief=None, variant_ids=None):
    foods = {food.pk: food for food in get_solver_food_candidate_queryset(user)}
    if brief:
        from notas.application.ai_intake.optimizer_v2_adapter import (
            _expanded_allergen_terms,
        )
        exclusions = [normalized(item) for item in brief.excluded_foods]
        allergies = _expanded_allergen_terms(brief.allergies_or_intolerances)
        patterns = {"vegan": {"vegan"}, "vegano": {"vegan"}, "vegana": {"vegan"},
                    "vegetarian": {"vegan", "vegetarian"}, "vegetariano": {"vegan", "vegetarian"},
                    "vegetariana": {"vegan", "vegetarian"}, "pescatarian": {"vegan", "vegetarian", "pescatarian"}}
        pattern = normalized(brief.dietary_pattern or "")
        if pattern and pattern not in patterns and pattern not in {"omnivore", "omnivoro", "omnivora"}:
            raise ValueError("culinary_dietary_pattern_unsupported")
        compatible = {}
        for key, food in foods.items():
            values = (food.solver_capabilities or {}).get("values", {})
            if any(term in normalized(food.name + " " + food.canonical_name) for term in exclusions):
                continue
            # Missing data is not evidence of absence. An explicit empty list is known-none.
            if allergies and ("allergens" not in values or not isinstance(values["allergens"], list) or
                              allergies.intersection(normalized(v) for v in values["allergens"])):
                continue
            if pattern in patterns and not patterns[pattern].intersection(normalized(v) for v in values.get("dietary_tags", [])):
                continue
            compatible[key] = food
        foods = compatible
    queryset = CulinaryVariant.objects.filter(Q(template__owner=user) | Q(template__owner__isnull=True)).exclude(
        status=CulinaryVariant.CANDIDATE).select_related("template").order_by("pk")
    if variant_ids is not None:
        queryset = queryset.filter(pk__in=variant_ids)
    candidates, rejected = [], []
    for variant in queryset:
        try:
            candidate = _snapshot(variant, foods)
            if variant.evidence_digest != candidate.evidence_digest:
                raise ValueError("culinary_evidence_stale")
            if variant.status == CulinaryVariant.HUMAN_VALIDATED and (not variant.reviewed_by_id or not variant.reviewed_at):
                raise ValueError("culinary_human_evidence_missing")
            candidates.append(candidate)
        except (ValueError, KeyError, TypeError) as exc:
            rejected.append({"variant_id": variant.pk, "reason": str(exc)})
    return tuple(candidates), rejected
