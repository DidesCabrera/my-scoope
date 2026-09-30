"""Independent validation: never infer feasibility from solver status."""

from collections import Counter
from math import isfinite

SUPPORTED_HARD_CONSTRAINTS = {"exclude_food_id", "require_food_id", "max_food_repetitions"}


def validate_constraint_contract(problem):
    for constraint in problem.constraints:
        if constraint.severity.lower() == "hard" and constraint.constraint_type not in SUPPORTED_HARD_CONSTRAINTS:
            raise ValueError(f"unsupported_hard_constraint:{constraint.constraint_type}")


def hard_constraint_violations(problem, result):
    errors = []
    try:
        validate_constraint_contract(problem)
    except ValueError as exc:
        errors.append(str(exc))
    profiles = {item.food.food_id: item for item in problem.food_profiles}
    slots = {item.slot_id: item for item in problem.meal_slots}
    counts = Counter(meal.slot_id for meal in result.meals)
    if set(counts) != set(slots) or any(value != 1 for value in counts.values()):
        errors.append("meal_slots_incomplete_or_duplicate")
    daily = dict.fromkeys(("kcal", "protein", "carbs", "fat"), 0.0)
    repetitions = Counter()
    for meal in result.meals:
        slot = slots.get(meal.slot_id)
        if slot is None:
            continue
        archetype = next((a for a in slot.allowed_archetypes if a.key == meal.archetype), None)
        if archetype is None:
            errors.append("meal_archetype_invalid")
            continue
        totals = dict.fromkeys(daily, 0.0)
        roles, ids = set(), set()
        for portion in meal.portions:
            profile = profiles.get(portion.food_id)
            if profile is None or portion.food_id in ids:
                errors.append("food_unknown_or_duplicate")
                continue
            ids.add(portion.food_id)
            repetitions[portion.food_id] += 1
            quantity = portion.quantity_g
            bounds = profile.food.bounds.normalized()
            if not isfinite(quantity) or not bounds.minimum_g <= quantity <= bounds.maximum_g:
                errors.append("portion_bounds_violated")
                continue
            if abs(quantity / bounds.step_g - round(quantity / bounds.step_g)) > 1e-6:
                errors.append("portion_step_violated")
            food = profile.food
            for metric in totals:
                totals[metric] += quantity * getattr(food, f"{metric}_per_100g") / 100
            roles.update(profile.functional_roles)
        if not archetype.minimum_components <= len(ids) <= archetype.maximum_components:
            errors.append("meal_component_bounds_violated")
        if any(not roles.intersection(group) for group in archetype.required_role_groups):
            errors.append("meal_required_role_missing")
        errors.extend(_ranges(slot.nutrient_ranges, totals, meal.slot_id))
        for metric in daily:
            daily[metric] += totals[metric]
    errors.extend(_ranges(problem.daily_nutrient_ranges, daily, "daily"))
    _check_food_constraints(problem, repetitions, errors)
    return tuple(dict.fromkeys(errors))


def _check_food_constraints(problem, repetitions, errors):
    for constraint in problem.constraints:
        if constraint.severity.lower() != "hard":
            continue
        ids = constraint.payload.get("food_ids", [constraint.payload.get("food_id")])
        ids = {int(value) for value in ids if value is not None}
        if constraint.constraint_type == "exclude_food_id" and ids.intersection(repetitions):
            errors.append("excluded_food_present")
        if constraint.constraint_type == "require_food_id" and not ids.issubset(repetitions):
            errors.append("required_food_missing")
        if constraint.constraint_type == "max_food_repetitions":
            maximum = constraint.payload.get("count")
            if maximum is None or any(count > int(maximum) for count in repetitions.values()):
                errors.append("food_repetition_limit_violated")


def _ranges(ranges, totals, scope):
    return [f"{scope}:{item.metric}:outside_hard_range" for item in ranges
            if item.metric not in totals or not item.minimum - 1e-6 <= totals[item.metric] <= item.maximum + 1e-6]
