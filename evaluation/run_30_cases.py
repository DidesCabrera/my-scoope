"""Run synthetic daily-plan cases against a read-only operational food snapshot."""

import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miapp.settings.dev")
import django
django.setup()

from notas.application.ai_intake.optimizer_v2_adapter import (
    _daily_ranges, _filter_profiles_by_typed_safety_constraints, _meal_ranges,
    _normalize_text,
)
from notas.application.nutrition_engine.meal_templates import build_dailyplan_meal_templates
from nutrition_solver.application.optimizer_v2 import solve_optimization_alternatives
from nutrition_solver.application.problem_v2 import MealSlotProblem, OptimizationProblemV2
from nutrition_solver.application.quality import assess_optimization_quality
from nutrition_solver.domain.food_profiles import SolverFeatureValue, SolverFoodProfile
from nutrition_solver.domain.meal_grammar import archetypes_for_meal_kind
from nutrition_solver.domain.models import PortionBounds, SolverFood

ROOT = Path(__file__).resolve().parent
FOODS = json.loads((ROOT / "foods_staging_2026-11-solver-v1.json").read_text())["foods"]

# Targets are synthetic product test inputs, not nutrition recommendations.
CASES = [
    ("S01", "Omnívoro, 1800 kcal, 3 comidas", 1800, 3, "omnivore", (), (), (), "", "", ""),
    ("S02", "Omnívoro, 2200 kcal, 4 comidas", 2200, 4, "omnivore", (), (), (), "", "", ""),
    ("S03", "Omnívoro, 2600 kcal, 4 comidas", 2600, 4, "omnivore", (), (), (), "", "", ""),
    ("S04", "Omnívoro, 3000 kcal, 4 comidas", 3000, 4, "omnivore", (), (), (), "", "", ""),
    ("S05", "Omnívoro, alto en proteína", 2300, 4, "omnivore", (), (), (), "", "", "high_protein"),
    ("S06", "Omnívoro, alto en carbohidratos", 2300, 4, "omnivore", (), (), (), "", "", "high_carbs"),
    ("S07", "Vegetariano, 1800 kcal", 1800, 4, "vegetarian", (), (), (), "", "", ""),
    ("S08", "Vegetariano, 2300 kcal", 2300, 4, "vegetarian", (), (), (), "", "", ""),
    ("S09", "Vegetariano, alto en proteína", 2300, 4, "vegetarian", (), (), (), "", "", "high_protein"),
    ("S10", "Vegano, 1800 kcal", 1800, 4, "vegan", (), (), (), "", "", ""),
    ("S11", "Vegano, 2300 kcal", 2300, 4, "vegan", (), (), (), "", "", ""),
    ("S12", "Vegano, alto en proteína", 2300, 4, "vegan", (), (), (), "", "", "high_protein"),
    ("S13", "Pescetariano, 1800 kcal", 1800, 4, "pescatarian", (), (), (), "", "", ""),
    ("S14", "Pescetariano, 2300 kcal", 2300, 4, "pescatarian", (), (), (), "", "", ""),
    ("S15", "Pescetariano, alto en proteína", 2300, 4, "pescatarian", (), (), (), "", "", "high_protein"),
    ("S16", "Alergia a leche", 2100, 4, "omnivore", ("milk",), (), (), "", "", ""),
    ("S17", "Alergia a huevo", 2100, 4, "omnivore", ("egg",), (), (), "", "", ""),
    ("S18", "Alergia a frutos secos", 2100, 4, "omnivore", ("nuts",), (), (), "", "", ""),
    ("S19", "Alergia a soya", 2100, 4, "omnivore", ("soy",), (), (), "", "", ""),
    ("S20", "Alergia a pescado", 2100, 4, "omnivore", ("fish",), (), (), "", "", ""),
    ("S21", "Vegano y alergia a soya", 2100, 4, "vegan", ("soy",), (), (), "", "", ""),
    ("S22", "Vegetariano y alergia a leche", 2100, 4, "vegetarian", ("milk",), (), (), "", "", ""),
    ("S23", "Sin pollo", 2100, 4, "omnivore", (), ("pollo",), (), "", "", ""),
    ("S24", "Sin arroz", 2100, 4, "omnivore", (), ("arroz",), (), "", "", ""),
    ("S25", "Prefiere legumbres", 2100, 4, "omnivore", (), (), ("lenteja", "garbanzo"), "", "", ""),
    ("S26", "Poco tiempo para cocinar", 2100, 4, "omnivore", (), (), (), "low", "", ""),
    ("S27", "Presupuesto bajo", 2100, 4, "omnivore", (), (), (), "", "low", ""),
    ("S28", "Vegano, poco tiempo y bajo presupuesto", 2100, 4, "vegan", (), (), (), "low", "low", ""),
    ("S29", "Vegetariano, sin huevos ni lácteos por exclusión", 2100, 4, "vegetarian", (), ("huevo", "leche", "yogur", "queso"), (), "", "", ""),
    ("S30", "Omnívoro, sin carnes ni pescados por exclusión", 2100, 4, "omnivore", (), ("pollo", "pavo", "carne", "cerdo", "pescado", "salmon", "atun"), (), "", "", ""),
]


def profile(row):
    values = row["solver_capabilities"]["values"]
    food = SolverFood(
        row["id"], row["name"], "balanced", float(row["protein"]),
        float(row["carbs"]), float(row["fat"]),
        float(row["protein"]) * 4 + float(row["carbs"]) * 4 + float(row["fat"]) * 9,
        PortionBounds(float(row["min_portion_g"]), float(row["max_portion_g"]), float(row["portion_step_g"])),
        False,
    )
    features = tuple(
        SolverFeatureValue(key, value, 90, "staging_snapshot", "solver_food_capabilities.v1")
        for key, value in values.items() if key in {
            "functional_roles", "meal_affinities", "dietary_tags", "allergens",
            "food_form", "preparation_effort", "cost_band",
        } and value not in (None, "", [], "unknown")
    )
    return SolverFoodProfile(food, features)


def run(case):
    (case_id, label, kcal, meal_count, pattern, allergies, exclusions, preferred,
     cooking_time, budget, macro_style) = case
    ratios = (0.40, 0.40, 0.20) if macro_style == "high_protein" else (
        (0.20, 0.55, 0.25) if macro_style == "high_carbs" else (0.30, 0.45, 0.25)
    )
    target = SimpleNamespace(total_kcal=kcal, protein=kcal * ratios[0] / 4,
                             carbs=kcal * ratios[1] / 4, fat=kcal * ratios[2] / 9)
    excluded = tuple(_normalize_text(term) for term in exclusions)
    candidates = tuple(profile(row) for row in FOODS if not any(
        term in _normalize_text(row["name"]) for term in excluded
    ))
    candidates = _filter_profiles_by_typed_safety_constraints(
        candidates, dietary_pattern=pattern, allergies_or_intolerances=allergies,
    )
    output = {"id": case_id, "request": label, "target_kcal": kcal, "meals": meal_count,
              "dietary_pattern": pattern, "allergies": allergies, "exclusions": exclusions,
              "preferred": preferred, "cooking_time": cooking_time, "budget": budget,
              "macro_style": macro_style, "candidate_count": len(candidates)}
    if not candidates:
        return {**output, "status": "no_candidates", "reason": "typed_filter_removed_all"}
    slots = tuple(MealSlotProblem(
        f"meal_{template.index}", template.kind, _meal_ranges(target, template.kcal_allocation),
        archetypes_for_meal_kind(template.kind),
    ) for template in build_dailyplan_meal_templates(meal_count))
    problem = OptimizationProblemV2(
        food_profiles=candidates, meal_slots=slots, daily_nutrient_ranges=_daily_ranges(target),
        preferences={"preferred_food_ids": tuple(
            p.food.food_id for p in candidates if any(
                _normalize_text(term) in _normalize_text(p.food.name) for term in preferred
            )), "cooking_time_preference": cooking_time, "budget_preference": budget},
        time_limit_ms=1500,
    )
    started = time.monotonic()
    portfolio = solve_optimization_alternatives(problem, count=3, backend="cp_sat_v1")
    if not portfolio.alternatives:
        return {**output, "status": "impossible", "reason": "no_feasible_alternative",
                "elapsed_seconds": round(time.monotonic() - started, 3), "alternative_count": 0}
    ranked = sorted(
        ((result, assess_optimization_quality(problem, result)) for result in portfolio.alternatives),
        key=lambda item: (-item[1].nutritional_score, -item[1].functional_score, item[0].objective_value),
    )
    result, quality = ranked[0]
    return {**output, "status": result.status.value, "reason": result.diagnostics.get("reason", ""),
            "solver_status": result.diagnostics.get("solver_status", ""),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "alternative_count": len(portfolio.alternatives),
            "quality": quality.as_dict(), "daily_totals": result.daily_totals,
            "selected_foods": [portion.as_dict() for meal in result.meals for portion in meal.portions],
            "meal_compositions": [{"slot": meal.slot_id, "archetype": meal.archetype,
                                   "foods": [p.name for p in meal.portions]} for meal in result.meals]}


if __name__ == "__main__":
    results = []
    for case in CASES:
        try:
            item = run(case)
        except Exception as exc:
            item = {"id": case[0], "request": case[1], "status": "error", "reason": f"{type(exc).__name__}: {exc}"}
        results.append(item)
        print(f"{item['id']} {item['status']} candidates={item.get('candidate_count', '-')} {item.get('reason', '')}", flush=True)
    (ROOT / "results_30_cases.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
