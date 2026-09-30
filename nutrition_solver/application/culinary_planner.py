"""Weekly CP-SAT selection of culinary variants, followed by independent validation.

No database, LLM or inferred food groups here. Quantities are multiples of an
ingredient's culinary step. Weekly family limits cannot be traded for macros.
"""

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from math import ceil, floor

from nutrition_solver.application.program_specification import ProgramSpecification


@dataclass(frozen=True)
class Ingredient:
    food_id: int
    name: str
    component: str
    group: str
    species: str
    minimum_g: float
    maximum_g: float
    step_g: float
    protein: float
    carbs: float
    fat: float

    @property
    def kcal(self):
        return self.protein * 4 + self.carbs * 4 + self.fat * 9


@dataclass(frozen=True)
class CulinaryCandidate:
    variant_id: int
    template_id: int
    family: str
    name: str
    meal_kinds: tuple[str, ...]
    preparation: str
    ingredients: tuple[Ingredient, ...]
    ratios: tuple[dict, ...]
    evidence_digest: str
    validation_level: str

    def as_dict(self):
        return asdict(self)


class CulinaryPlanningError(ValueError):
    def __init__(self, code, **details):
        self.code, self.details = code, details
        super().__init__(f"{code}: {details}")


def _slot_candidates(candidates, slot, day, slot_index, week, pinned, changed_from, avoid_food_ids, candidate_width):
    available = [c for c in candidates if slot["kind"] in c.meal_kinds]
    position = (day, slot_index)
    if position in pinned:
        available = [c for c in available if c.variant_id == pinned[position]["variant_id"]]
    elif position in changed_from:
        available = [c for c in available if c.variant_id != changed_from[position]
                     and not set(avoid_food_ids).intersection(i.food_id for i in c.ingredients)]
    if not available:
        raise CulinaryPlanningError("culinary_catalog_slot_unavailable", slot=slot["kind"])
    # Bounded, stratified portfolio: keep every family and rotate variants by day.
    # This avoids a huge symmetric food-by-variant search, without counting a
    # starch substitution as a new family. Failure is scoped to this portfolio.
    families = defaultdict(list)
    for candidate in available:
        families[candidate.family].append(candidate)
    available = []
    family_names = sorted(families)
    # Establish a balanced culinary schedule before optimizing quantities.
    # The independent validator still checks the complete weekly schedule.
    family_name = family_names[(day - 1 + slot_index + week.week - 1) % len(family_names)]
    for family_candidates in (families[family_name],):
        offset = (day - 1 + slot_index + (week.week - 1) * 3) % len(family_candidates)
        available.extend(family_candidates[(offset + index * max(1, len(family_candidates) // candidate_width)) % len(family_candidates)]
                         for index in range(min(candidate_width, len(family_candidates))))
    return position, available


def solve_culinary_week(spec: ProgramSpecification, week, slots, candidates, *, previous=(), time_limit_seconds=5,
                       candidate_width=2, pinned=None, changed_from=None, avoid_food_ids=()):
    from ortools.sat.python import cp_model

    model = cp_model.CpModel()
    pinned, changed_from = pinned or {}, changed_from or {}
    selected, quantities, options = {}, {}, {}
    objectives, weekly_groups, family_use = [], defaultdict(list), defaultdict(list)
    species_use = defaultdict(list)
    # A small rotation preference across weeks; hard weekly constraints still dominate.
    previous_counts = Counter((row["slot"], row["family"]) for row in previous)
    daily_energy = []
    for day in range(1, 8):
        totals = {key: [] for key in ("kcal", "protein", "carbs", "fat", "fruit", "vegetable")}
        lower = {key: [] for key in ("kcal", "protein", "carbs", "fat")}
        upper = {key: [] for key in lower}
        for slot_index, slot in enumerate(slots):
            position, available = _slot_candidates(candidates, slot, day, slot_index, week, pinned,
                                                   changed_from, avoid_food_ids, candidate_width)
            slot_selected, slot_energy, slot_lower, slot_upper = [], [], [], []
            for candidate in available:
                key = (day, slot_index, candidate.variant_id)
                y = model.new_bool_var(f"v_{day}_{slot_index}_{candidate.variant_id}")
                selected[key], options[key] = y, candidate
                slot_selected.append(y)
                family_use[slot_index, candidate.family].append(y)
                # Avoid reproducing the exact prior week's family on the same day.
                repeated = any(row["day"] == day and row["slot"] == slot_index and
                               row["family"] == candidate.family for row in previous)
                objectives.append(5000 * (20 * repeated + previous_counts[slot_index, candidate.family]) * y)
                component_vars = {}
                for index, ingredient in enumerate(candidate.ingredients):
                    q = model.new_int_var(0, floor(ingredient.maximum_g / ingredient.step_g), f"q_{key}_{index}")
                    model.add(q >= ceil(ingredient.minimum_g / ingredient.step_g) * y)
                    model.add(q <= floor(ingredient.maximum_g / ingredient.step_g) * y)
                    quantities[key, index] = q
                    if position in pinned:
                        amounts = {item["food_id"]: item["quantity"] for item in pinned[position]["foods"]}
                        model.add(q * round(ingredient.step_g * 1000) == round(amounts[ingredient.food_id] * 1000))
                    component_vars[ingredient.component] = (q, ingredient.step_g)
                    for metric in ("kcal", "protein", "carbs", "fat"):
                        coefficient = getattr(ingredient, metric) * ingredient.step_g * 10
                        term = round(coefficient) * q
                        totals[metric].append(term)
                        lower[metric].append(floor(coefficient) * q)
                        upper[metric].append(ceil(coefficient) * q)
                        if metric == "kcal":
                            slot_energy.append(term)
                            slot_lower.append(floor(coefficient) * q)
                            slot_upper.append(ceil(coefficient) * q)
                    if ingredient.group in {"fruit", "vegetable"}:
                        totals[ingredient.group].append(round(ingredient.step_g * 1000) * q)
                        species_use[ingredient.group, ingredient.species].append(y)
                for ratio in candidate.ratios:
                    left, left_step = component_vars[ratio["left"]]
                    right, right_step = component_vars[ratio["right"]]
                    model.add(round(left_step * 1000) * left >= round(ratio["minimum"] * right_step * 1000) * right)
                    model.add(round(left_step * 1000) * left <= round(ratio["maximum"] * right_step * 1000) * right)
            model.add(sum(slot_selected) == 1)
            slot_target = round(week.kcal * slot["allocation"] * 1000)
            # Prevent the optimizer putting virtually all energy in one meal.
            model.add(sum(slot_lower) >= ceil(slot_target * .65))
            model.add(sum(slot_upper) <= floor(slot_target * 1.35))
            deviation = model.new_int_var(0, 8_000_000, f"meal_deviation_{day}_{slot_index}")
            model.add_abs_equality(deviation, sum(slot_energy) - slot_target)
            objectives.append(deviation)
        expressions = {key: sum(items) for key, items in totals.items()}
        lower = {key: sum(items) for key, items in lower.items()}
        upper = {key: sum(items) for key, items in upper.items()}
        tolerance = spec.calorie_tolerance_percent / 100
        model.add(lower["kcal"] >= ceil(week.kcal * (1 - tolerance) * 1000))
        model.add(upper["kcal"] <= floor(week.kcal * (1 + tolerance) * 1000))
        # Bound each coefficient BEFORE multiplying by the number of portion
        # steps. A fixed .02g guard cannot bound accumulated rounding error.
        model.add(lower["protein"] >= ceil(week.protein_min_g * 1000))
        model.add(upper["protein"] <= floor(week.protein_max_g * 1000))
        model.add(upper["fat"] * 90000 <= floor(spec.fat_max_percent * 100) * lower["kcal"])
        model.add(expressions["fruit"] >= ceil(spec.fruit_min_g * 1000))
        model.add(expressions["vegetable"] >= ceil(spec.vegetable_min_g * 1000))
        for metric, percent in spec.macro_distribution.items():
            factor = 9 if metric == "fat" else 4
            tolerance = spec.macro_tolerance_percent / 100
            model.add(lower[metric] * factor * 10000 >= ceil(percent * (1 - tolerance) * 100) * upper["kcal"])
            model.add(upper[metric] * factor * 10000 <= floor(percent * (1 + tolerance) * 100) * lower["kcal"])
        daily_energy.append((lower["kcal"], upper["kcal"]))
        deviation = model.new_int_var(0, 8_000_000, f"day_deviation_{day}")
        model.add_abs_equality(deviation, expressions["kcal"] - round(week.kcal * 1000))
        objectives.append(deviation * 4)
    return _finish_week_model(model, spec, week, previous, family_use, species_use, weekly_groups,
                              daily_energy, objectives, selected, quantities, options, time_limit_seconds)


def _finish_week_model(model, spec, week, previous, family_use, species_use, weekly_groups,
                       daily_energy, objectives, selected, quantities, options, time_limit_seconds):
    from ortools.sat.python import cp_model

    for uses in family_use.values():
        model.add(sum(uses) <= spec.max_family_per_week_per_slot)
    for (group, species), uses in species_use.items():
        present = model.new_bool_var(f"species_{group}_{species}")
        model.add_max_equality(present, uses)
        weekly_groups[group].append(present)
    for group, minimum in (("fruit", spec.weekly_fruit_species), ("vegetable", spec.weekly_vegetable_species)):
        model.add(sum(weekly_groups[group]) >= minimum)
    if previous:
        prior_week = spec.weeks[week.week - 2]
        prior_total = sum(row["kcal"] for row in previous)
        if week.kcal < prior_week.kcal:
            model.add(sum(upper for _, upper in daily_energy) < ceil(prior_total * 1000))
        elif week.kcal > prior_week.kcal:
            model.add(sum(lower for lower, _ in daily_energy) > floor(prior_total * 1000))
    model.minimize(sum(objectives))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = min(max(float(time_limit_seconds), .1), 30)
    # Production workers have a bounded memory/CPU budget. Parallel CP-SAT
    # portfolios duplicate search state; a single worker keeps the weekly
    # problem reproducible and leaves room for the assistant and ORM.
    solver.parameters.num_search_workers = 1
    # Portion expressions have large sparse integer domains; full presolve can
    # spend the whole budget enumerating them before searching any solution.
    solver.parameters.cp_model_presolve = False
    solver.parameters.random_seed = week.week
    import os
    solver.parameters.log_search_progress = os.environ.get("MYSCOOPE_SOLVER_DEBUG") == "1"
    status = solver.solve(model)
    if status not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        code = "culinary_candidate_pool_infeasible" if status == cp_model.INFEASIBLE else "culinary_search_timeout"
        if status == cp_model.MODEL_INVALID:
            code = "culinary_model_invalid"
        raise CulinaryPlanningError(code, week=week.week, solver_status=solver.status_name(status), wall_seconds=solver.wall_time)
    meals = []
    for key, y in selected.items():
        if not solver.value(y):
            continue
        candidate = options[key]
        portions = [{"food_id": ingredient.food_id, "quantity": solver.value(quantities[key, index]) * ingredient.step_g,
                     "unit": "g"} for index, ingredient in enumerate(candidate.ingredients)]
        kcal = sum(ingredient.kcal * portion["quantity"] / 100
                   for ingredient, portion in zip(candidate.ingredients, portions))
        meals.append({"day": key[0], "slot": key[1], "variant_id": candidate.variant_id,
                      "family": candidate.family, "name": candidate.name, "preparation": candidate.preparation,
                      "foods": portions, "kcal": kcal, "evidence_digest": candidate.evidence_digest})
    return sorted(meals, key=lambda row: (row["day"], row["slot"]))


def _validate_meal_portions(row, candidate, target, allocation, totals, species, errors):
    portions = row.get("foods", [])
    if len(portions) != len(candidate.ingredients) or {p.get("food_id") for p in portions} != {i.food_id for i in candidate.ingredients}:
        errors.append(f"week_{target.week}:ingredient_mismatch")
        return
    amounts = {portion["food_id"]: portion for portion in portions}
    components, meal_energy = {}, 0.0
    for ingredient in candidate.ingredients:
        portion = amounts[ingredient.food_id]
        quantity = portion.get("quantity")
        from math import isfinite
        if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or not isfinite(quantity) or portion.get("unit") != "g":
            errors.append("invalid_portion")
            continue
        if not ingredient.minimum_g <= quantity <= ingredient.maximum_g or abs(quantity / ingredient.step_g - round(quantity / ingredient.step_g)) > 1e-6:
            errors.append("culinary_portion_bounds")
        components[ingredient.component] = quantity
        for metric in ("kcal", "protein", "carbs", "fat"):
            totals[metric] += getattr(ingredient, metric) * quantity / 100
        meal_energy += ingredient.kcal * quantity / 100
        if ingredient.group in {"fruit", "vegetable"}:
            totals[ingredient.group] += quantity
            if quantity >= 50:
                species[ingredient.group].add(ingredient.species)
    for ratio in candidate.ratios:
        left, right = components.get(ratio["left"], 0), components.get(ratio["right"], 0)
        if not ratio["minimum"] * right - 1e-6 <= left <= ratio["maximum"] * right + 1e-6:
            errors.append("culinary_ratio_violated")
    if not target.kcal * allocation * .65 - .02 <= meal_energy <= target.kcal * allocation * 1.35 + .02:
        errors.append("meal_energy_distribution")


def validate_culinary_program(spec, weeks, slots, candidates):
    """Recalculate every day and culinary bound; do not trust solver totals or labels."""
    errors, evidence, weekly_totals = [], [], []
    by_id = {candidate.variant_id: candidate for candidate in candidates}
    if len(weeks) != spec.duration_weeks:
        errors.append("incomplete_weeks")
    for target, rows in zip(spec.weeks, weeks):
        families, species = Counter(), defaultdict(set)
        seen, week_energy = set(), 0.0
        for day in range(1, 8):
            totals = dict.fromkeys(("kcal", "protein", "carbs", "fat", "fruit", "vegetable"), 0.0)
            daily_rows = [row for row in rows if row.get("day") == day]
            for row in daily_rows:
                slot = row.get("slot")
                candidate = by_id.get(row.get("variant_id"))
                if (day, slot) in seen or type(slot) is not int or not 0 <= slot < len(slots):
                    errors.append(f"week_{target.week}:invalid_slot")
                    continue
                seen.add((day, slot))
                if not candidate or candidate.evidence_digest != row.get("evidence_digest") or slots[slot]["kind"] not in candidate.meal_kinds:
                    errors.append(f"week_{target.week}:invalid_variant")
                    continue
                families[slot, candidate.family] += 1
                _validate_meal_portions(row, candidate, target, slots[slot]["allocation"], totals, species, errors)
            tolerance = spec.calorie_tolerance_percent / 100
            checks = {
                "energy": target.kcal * (1 - tolerance) - 1e-6 <= totals["kcal"] <= target.kcal * (1 + tolerance) + 1e-6,
                "protein": target.protein_min_g - 1e-6 <= totals["protein"] <= target.protein_max_g + 1e-6,
                "fat_cap": totals["fat"] * 9 <= totals["kcal"] * spec.fat_max_percent / 100 + 1e-6,
                "fruit": totals["fruit"] >= spec.fruit_min_g,
                "vegetable": totals["vegetable"] >= spec.vegetable_min_g,
            }
            for metric, percent in spec.macro_distribution.items():
                factor = 9 if metric == "fat" else 4
                actual = totals[metric] * factor * 100 / totals["kcal"] if totals["kcal"] else 0
                tolerance = spec.macro_tolerance_percent / 100
                checks[f"distribution_{metric}"] = percent * (1 - tolerance) - 1e-6 <= actual <= percent * (1 + tolerance) + 1e-6
            errors.extend(f"week_{target.week}:day_{day}:{key}" for key, passed in checks.items() if not passed)
            evidence.append({"week": target.week, "day": day, "checks": checks, "totals": totals,
                             "ppk": totals["protein"] / target.reference_weight_kg,
                             "fat_percent": totals["fat"] * 900 / totals["kcal"] if totals["kcal"] else None})
            week_energy += totals["kcal"]
        if seen != {(day, slot) for day in range(1, 8) for slot in range(len(slots))} or len(rows) != 7 * len(slots):
            errors.append("incomplete_or_extra_meals")
        if any(count > spec.max_family_per_week_per_slot for count in families.values()):
            errors.append("family_repetition_limit")
        for group, minimum in (("fruit", spec.weekly_fruit_species), ("vegetable", spec.weekly_vegetable_species)):
            if len(species[group]) < minimum:
                errors.append(f"weekly_{group}_diversity")
        weekly_totals.append(week_energy)
    for index in range(1, len(weekly_totals)):
        change = spec.weeks[index].kcal - spec.weeks[index - 1].kcal
        if change and (weekly_totals[index] - weekly_totals[index - 1]) * change <= 0:
            errors.append("weekly_energy_progression")
    return {"valid": not errors, "errors": sorted(set(errors)), "days": evidence,
            "weekly_mean_kcal": [total / 7 for total in weekly_totals], "validator_version": "culinary_program.v1"}
