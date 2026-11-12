"""Fixed-fixture Nutrition Solver lab, separate from the AI Assistant lab."""

from __future__ import annotations

import hashlib
import json
import time
import unicodedata
from pathlib import Path
from statistics import mean

from nutrition_solver.application.optimizer_v2 import (
    solve_optimization_alternatives, solve_optimization_problem,
)
from nutrition_solver.application.problem_v2 import MealSlotProblem, NutrientRange, OptimizationProblemV2
from nutrition_solver.domain.food_profiles import SolverFeatureValue, SolverFoodProfile
from nutrition_solver.domain.meal_grammar import archetypes_for_meal_kind
from nutrition_solver.domain.models import PortionBounds, SolverFood
from nutrition_solver.evaluation_lab.metrics import measure

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ALLOCATIONS = {3: (("breakfast", .28), ("main", .38), ("dinner", .34)),
               4: (("breakfast", .24), ("main", .34), ("snack", .16), ("dinner", .26))}
ALLERGEN_GROUPS = (
    {"milk", "dairy", "lactose", "leche", "lactosa", "lacteos"},
    {"gluten", "wheat", "trigo", "cebada", "barley", "rye", "centeno"},
    {"nuts", "tree nuts", "peanut", "peanuts", "frutos secos", "mani"},
    {"shellfish", "crustaceans", "mariscos", "crustaceos"},
    {"soy", "soya", "soja"}, {"egg", "eggs", "huevo", "huevos"},
    {"fish", "pescado"}, {"sesame", "sesamo"},
)
DIETARY_TAGS = {"vegan": {"vegan"}, "vegetarian": {"vegan", "vegetarian"},
                "pescatarian": {"vegan", "vegetarian", "pescatarian"}}


def _normalize(value):
    decomposed = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    return " ".join("".join(ch for ch in decomposed if not unicodedata.combining(ch)).split())


def _expanded_allergens(values):
    declared = {_normalize(value) for value in values}
    expanded = set(declared)
    for group in ALLERGEN_GROUPS:
        if declared.intersection(group):
            expanded.update(group)
    return expanded


def _profile(row):
    values = row["solver_capabilities"]["values"]
    food = SolverFood(
        food_id=int(row["id"]), name=row["name"], role="balanced",
        protein_per_100g=float(row["protein"]), carbs_per_100g=float(row["carbs"]),
        fat_per_100g=float(row["fat"]),
        kcal_per_100g=float(row["protein"]) * 4 + float(row["carbs"]) * 4 + float(row["fat"]) * 9,
        bounds=PortionBounds(float(row["min_portion_g"]), float(row["max_portion_g"]),
                             float(row["portion_step_g"])), required=False,
    )
    keys = {"functional_roles", "meal_affinities", "dietary_tags", "allergens",
            "food_form", "preparation_effort", "cost_band"}
    features = tuple(SolverFeatureValue(key, value, 90, "fixed_operational_snapshot",
                                        row["solver_capabilities"].get("schema_version", ""))
                     for key, value in values.items() if key in keys and value not in (None, "", [], "unknown"))
    return SolverFoodProfile(food, features)


def _candidates(rows, case):
    exclusions = tuple(_normalize(value) for value in case["exclusions"])
    allergens = _expanded_allergens(case["allergies"])
    accepted_tags = DIETARY_TAGS.get(case["pattern"])
    profiles = []
    for row in rows:
        if any(term in _normalize(row["name"]) for term in exclusions):
            continue
        profile = _profile(row)
        values = row["solver_capabilities"]["values"]
        tags = {_normalize(value) for value in values.get("dietary_tags", ())}
        # Match the current operational adapter, including its documented
        # empty-allergen-list issue. This is an observed baseline, not policy.
        declared = {_normalize(value) for value in values.get("allergens", ())}
        if accepted_tags is not None and not tags.intersection(accepted_tags):
            continue
        if allergens and (not declared or declared.intersection(allergens)):
            continue
        profiles.append(profile)
    return tuple(profiles)


def _ranges(targets, *, allocation=1, daily=False):
    widths = (("kcal", .88, 1.12, 4), ("protein", .82, 1.18, 4),
              ("carbs", .78, 1.22, 2), ("fat", .75, 1.25, 2)) if daily else (
              ("kcal", .72, 1.28, 3), ("protein", .55, 1.45, 3),
              ("carbs", .50, 1.50, 1.5), ("fat", .45, 1.55, 1.5))
    return tuple(NutrientRange(metric, targets[metric] * allocation,
                               targets[metric] * allocation * low,
                               targets[metric] * allocation * high, weight)
                 for metric, low, high, weight in widths)


def _problem(case, rows, *, kcal_delta=0, time_limit_ms=1500):
    ratios = (.40, .40, .20) if case["macro_style"] == "high_protein" else (
        (.20, .55, .25) if case["macro_style"] == "high_carbs" else (.30, .45, .25))
    kcal = case["kcal"] * (1 + kcal_delta)
    targets = {"kcal": kcal, "protein": kcal * ratios[0] / 4,
               "carbs": kcal * ratios[1] / 4, "fat": kcal * ratios[2] / 9}
    profiles = _candidates(rows, case)
    if not profiles:
        return None, targets
    slots = tuple(MealSlotProblem(f"meal_{i}", kind, _ranges(targets, allocation=part),
                                  archetypes_for_meal_kind(kind))
                  for i, (kind, part) in enumerate(ALLOCATIONS[case["meals"]]))
    preferred_ids = tuple(p.food.food_id for p in profiles if any(
        _normalize(term) in _normalize(p.food.name) for term in case["preferred"]))
    return OptimizationProblemV2(
        profiles, slots, daily_nutrient_ranges=_ranges(targets, daily=True),
        preferences={"preferred_food_ids": preferred_ids,
                     "cooking_time_preference": case["cooking_time"],
                     "budget_preference": case["budget"]},
        time_limit_ms=time_limit_ms,
    ), targets


def _signature(result):
    return tuple(sorted((meal.slot_id, portion.food_id) for meal in result.meals for portion in meal.portions))


def run_case(case, foods, *, alternatives=3, time_limit_ms=1500, stability=False):
    problem, targets = _problem(case, foods, time_limit_ms=time_limit_ms)
    base = {"id": case["id"], "label": case["label"], "expected": case["expected"],
            "horizon": case["horizon"], "targets": targets,
            "candidate_count": len(problem.food_profiles) if problem else 0}
    if problem is None:
        return {**base, "feasible": False, "alternative_count": 0, "reason_code": "no_eligible_foods",
                "latency_ms": 0, "metrics": None, "alternatives": [], "stability": None}
    started = time.perf_counter()
    portfolio = solve_optimization_alternatives(problem, count=alternatives, backend="cp_sat_v1")
    elapsed = (time.perf_counter() - started) * 1000
    if not portfolio.alternatives:
        diagnostic = solve_optimization_problem(problem, backend="cp_sat_v1")
        return {**base, "feasible": False, "alternative_count": 0,
                "reason_code": str(diagnostic.diagnostics.get("reason") or "solver_no_solution"),
                "solver_status": diagnostic.diagnostics.get("solver_status"),
                "latency_ms": round(elapsed, 1), "metrics": None, "alternatives": [], "stability": None}
    preparation = {int(row["id"]): row["preparation_state"] for row in foods}
    ranked = sorted(((result, measure(problem, result, preparation_by_id=preparation))
                     for result in portfolio.alternatives),
                    key=lambda pair: (-pair[1]["nutrition_score_existing"],
                                      -pair[1]["role_grammar_score_existing"], pair[0].objective_value))
    selected, metrics = ranked[0]
    alternatives_summary = [{"rank": index, "status": result.status.value,
                             "objective": round(result.objective_value, 3),
                             "nutrition_score": item["nutrition_score_existing"],
                             "signature": _signature(result),
                             "meals": [meal.as_dict() for meal in result.meals]}
                            for index, (result, item) in enumerate(ranked, 1)]
    signatures = [set(_signature(result)) for result, _ in ranked]
    metrics["variety"]["distinct_alternatives"] = len({tuple(sorted(s)) for s in signatures})
    metrics["variety"]["mean_alternative_overlap"] = round(mean(
        len(signatures[0] & other) / len(signatures[0] | other) if signatures[0] | other else 1
        for other in signatures[1:]), 3) if len(signatures) > 1 else None
    stability_result = None
    if stability:
        repeated = solve_optimization_problem(problem, backend="cp_sat_v1")
        perturbed_problem, _ = _problem(case, foods, kcal_delta=.01, time_limit_ms=time_limit_ms)
        perturbed = solve_optimization_problem(perturbed_problem, backend="cp_sat_v1")
        first = portfolio.alternatives[0]
        base_ids = {portion.food_id for meal in first.meals for portion in meal.portions}
        changed_ids = {portion.food_id for meal in perturbed.meals for portion in meal.portions}
        stability_result = {"repeat_same_signature": _signature(first) == _signature(repeated),
                            "plus_1pct_feasible": perturbed.status.value != "impossible",
                            "plus_1pct_food_jaccard": round(len(base_ids & changed_ids) / len(base_ids | changed_ids), 3)
                            if base_ids | changed_ids else None}
    return {**base, "feasible": True, "alternative_count": len(ranked), "reason_code": None,
            "latency_ms": round(elapsed, 1), "metrics": metrics,
            "alternatives": alternatives_summary, "stability": stability_result}


def run_suite(*, case_ids=None, alternatives=3, time_limit_ms=1500, stability=True):
    case_path = FIXTURES / "cases_v1.json"
    food_path = FIXTURES / "foods_157_v1.json"
    cases = json.loads(case_path.read_text())["cases"]
    foods = json.loads(food_path.read_text())["foods"]
    if case_ids is not None:
        unknown = set(case_ids) - {case["id"] for case in cases}
        if unknown:
            raise ValueError(f"unknown_case_ids:{','.join(sorted(unknown))}")
        cases = [case for case in cases if case["id"] in case_ids]
    results = [run_case(case, foods, alternatives=alternatives, time_limit_ms=time_limit_ms,
                        stability=stability and case["stability_probe"]) for case in cases]
    case_digest = hashlib.sha256(case_path.read_bytes()).hexdigest()
    food_digest = hashlib.sha256(food_path.read_bytes()).hexdigest()
    source_root = Path(__file__).resolve().parents[1]
    implementation = hashlib.sha256()
    for path in (
        source_root / "application" / "optimizer_v2.py",
        source_root / "application" / "quality.py",
        source_root / "application" / "hard_validation.py",
        Path(__file__),
        Path(__file__).with_name("metrics.py"),
    ):
        implementation.update(path.read_bytes())
    implementation_digest = implementation.hexdigest()
    config = {"alternatives": alternatives, "time_limit_ms": time_limit_ms,
              "stability": stability, "case_ids": [case["id"] for case in cases]}
    run_id = hashlib.sha256(json.dumps({"cases": case_digest, "foods": food_digest,
                                       "implementation": implementation_digest, "config": config},
                                      sort_keys=True).encode()).hexdigest()[:16]
    feasible = [result for result in results if result["feasible"]]
    latencies = sorted(result["latency_ms"] for result in results)
    p95 = latencies[min(len(latencies) - 1, int(.95 * len(latencies)))] if latencies else None
    return {"schema_version": "nutrition_solver_lab_run.v1", "run_id": run_id,
            "case_digest": case_digest, "food_digest": food_digest, "config": config,
            "implementation_digest": implementation_digest,
            "fixture_provenance": json.loads(food_path.read_text())["provenance"],
            "summary": {"case_count": len(results), "feasible_count": len(feasible),
                        "feasibility_rate": round(len(feasible) / len(results), 3) if results else None,
                        "p95_latency_ms": p95,
                        "hard_violation_cases": [result["id"] for result in feasible
                                                 if result["metrics"]["hard_violations"]],
                        "unexplained_infeasible": [result["id"] for result in results
                                                 if not result["feasible"] and not result["reason_code"]],
                        "human_review_required": [result["id"] for result in feasible]},
            "cases": results}
