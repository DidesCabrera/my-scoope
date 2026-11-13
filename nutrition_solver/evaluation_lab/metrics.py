"""Independent measurements; scores here never change solver selection."""

from __future__ import annotations

from collections import Counter
from statistics import mean

from nutrition_solver.application.hard_validation import hard_constraint_violations
from nutrition_solver.application.quality import assess_optimization_quality


def measure(problem, result, *, preparation_by_id: dict[int, str]) -> dict:
    violations = list(hard_constraint_violations(problem, result))
    quality = assess_optimization_quality(problem, result)
    preferences = []
    absolute_deviations = []
    for nutrient in problem.daily_nutrient_ranges:
        actual = float(result.daily_totals.get(nutrient.metric, 0))
        preferences.append({
            "metric": nutrient.metric,
            "target": nutrient.preferred,
            "actual": round(actual, 3),
            "relative_deviation_pct": round(abs(actual - nutrient.preferred) / nutrient.preferred * 100, 2)
            if nutrient.preferred else None,
            "within_hard_range": nutrient.minimum - 1e-6 <= actual <= nutrient.maximum + 1e-6,
        })
        if nutrient.preferred:
            absolute_deviations.append(abs(actual - nutrient.preferred) / nutrient.preferred * 100)
    portions = [portion for meal in result.meals for portion in meal.portions]
    uses = Counter(portion.food_id for portion in portions)
    total_uses = sum(uses.values())
    affinity_misses = []
    profiles = {profile.food.food_id: profile for profile in problem.food_profiles}
    slots = {slot.slot_id: slot for slot in problem.meal_slots}
    for meal in result.meals:
        kind = slots[meal.slot_id].meal_kind
        for portion in meal.portions:
            affinity = profiles[portion.food_id].feature("meal_affinities")
            if affinity and affinity.available:
                allowed = {"main" if value == "lunch" else value for value in affinity.value}
                if kind not in allowed:
                    affinity_misses.append({"slot": meal.slot_id, "food_id": portion.food_id, "kind": kind})
    return {
        "hard_violations": violations,
        "nutrient_deviations": preferences,
        "mean_nutrient_deviation_pct": round(mean(absolute_deviations), 2) if absolute_deviations else None,
        "max_nutrient_deviation_pct": round(max(absolute_deviations), 2) if absolute_deviations else None,
        "nutrition_score_existing": quality.nutritional_score,
        "role_grammar_score_existing": quality.functional_score,
        "culinary_signals": {
            "affinity_mismatches": affinity_misses,
            "raw_or_dry_food_ids": sorted({portion.food_id for portion in portions
                                           if preparation_by_id.get(portion.food_id) in {"raw", "dry"}}),
            "validated_recipe_evidence": False,
            "requires_human_review": True,
        },
        "variety": {
            "distinct_foods": len(uses),
            "max_daily_repetitions": max(uses.values(), default=0),
            "concentration_hhi": round(sum((count / total_uses) ** 2 for count in uses.values()), 4)
            if total_uses else None,
        },
    }


def compare_runs(baseline: dict, candidate: dict) -> dict:
    """Compare only matching scenario and fixture definitions."""
    for field in ("case_digest", "food_digest"):
        if baseline[field] != candidate[field]:
            raise ValueError(f"incomparable_{field}")
    if baseline["config"] != candidate["config"]:
        raise ValueError("incomparable_config")
    prior = {case["id"]: case for case in baseline["cases"]}
    current = {case["id"]: case for case in candidate["cases"]}
    if prior.keys() != current.keys():
        raise ValueError("incomparable_case_ids")
    changes = []
    for case_id in sorted(prior):
        old, new = prior[case_id], current[case_id]
        old_metrics, new_metrics = old.get("metrics") or {}, new.get("metrics") or {}
        old_culinary = old_metrics.get("culinary_signals") or {}
        new_culinary = new_metrics.get("culinary_signals") or {}
        old_variety = old_metrics.get("variety") or {}
        new_variety = new_metrics.get("variety") or {}
        changes.append({
            "id": case_id,
            "feasibility_changed": old["feasible"] != new["feasible"],
            "new_hard_violations": sorted(set(new_metrics.get("hard_violations", ())) -
                                          set(old_metrics.get("hard_violations", ()))),
            "nutrition_score_delta": round(new_metrics.get("nutrition_score_existing", 0) -
                                           old_metrics.get("nutrition_score_existing", 0), 2),
            "latency_delta_ms": round(new["latency_ms"] - old["latency_ms"], 1),
            "affinity_mismatch_delta": len(new_culinary.get("affinity_mismatches", ())) -
                                       len(old_culinary.get("affinity_mismatches", ())),
            "max_repetition_delta": new_variety.get("max_daily_repetitions", 0) -
                                    old_variety.get("max_daily_repetitions", 0),
        })
    regressions = []
    for change in changes:
        if prior[change["id"]]["feasible"] and not current[change["id"]]["feasible"]:
            regressions.append({"id": change["id"], "reason": "new_infeasibility"})
        if change["new_hard_violations"]:
            regressions.append({"id": change["id"], "reason": "new_hard_violation"})
        if prior[change["id"]]["feasible"] and current[change["id"]]["feasible"]:
            if change["nutrition_score_delta"] < -5:
                regressions.append({"id": change["id"], "reason": "nutrition_score_drop_over_5"})
            if change["affinity_mismatch_delta"] > 0:
                regressions.append({"id": change["id"], "reason": "more_affinity_mismatches"})
            if change["max_repetition_delta"] > 1:
                regressions.append({"id": change["id"], "reason": "repetition_increase_over_1"})
    return {"baseline_run_id": baseline["run_id"], "candidate_run_id": candidate["run_id"],
            "changes": changes, "new_infeasible": [c["id"] for c in changes if prior[c["id"]]["feasible"] and not current[c["id"]]["feasible"]],
            "new_hard_violation_cases": [c["id"] for c in changes if c["new_hard_violations"]],
            "regressions": regressions}


def assess_human_review(run: dict, review: dict) -> dict:
    dimensions = ("coherence", "portion_realism", "preparation", "practicality", "local_relevance")
    expected = {case["id"] for case in run["cases"] if case["feasible"]}
    submitted = {case.get("id"): case for case in review.get("cases", ())}
    errors = []
    if review.get("run_id") != run["run_id"]:
        errors.append("review_run_id_mismatch")
    if not str(review.get("reviewer") or "").strip() or not str(review.get("reviewed_at") or "").strip():
        errors.append("reviewer_or_date_missing")
    if set(submitted) != expected:
        errors.append("review_case_ids_incomplete_or_extra")
    scores = []
    for case_id in sorted(expected & set(submitted)):
        values = []
        for dimension in dimensions:
            value = submitted[case_id].get(dimension)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
                errors.append(f"invalid_score:{case_id}:{dimension}")
            else:
                values.append(value)
                scores.append(value)
        if values and min(values) <= 2:
            errors.append(f"severe_quality_defect:{case_id}")
    if scores and mean(scores) < 4:
        errors.append("mean_human_score_below_4")
    return {"status": "passed" if not errors else "failed", "errors": errors,
            "mean_score": round(mean(scores), 2) if scores else None,
            "reviewed_cases": len(expected & set(submitted))}
