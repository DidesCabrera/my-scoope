"""CLI: python -m nutrition_solver.evaluation_lab --out /tmp/solver-lab."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from nutrition_solver.evaluation_lab.metrics import assess_human_review, compare_runs
from nutrition_solver.evaluation_lab.runner import run_suite


def gate(run):
    summary = run["summary"]
    failures = []
    if summary["feasibility_rate"] is not None and summary["feasibility_rate"] < .90:
        failures.append("feasibility_rate_below_90pct")
    if summary["p95_latency_ms"] is not None and summary["p95_latency_ms"] > 6000:
        failures.append("p95_latency_above_6s")
    if summary["hard_violation_cases"]:
        failures.append("hard_constraint_violation")
    if summary["unexplained_infeasible"]:
        failures.append("unexplained_infeasibility")
    for case in run["cases"]:
        if case["expected"] == "feasible" and not case["feasible"]:
            failures.append(f"expected_feasible_failed:{case['id']}")
        if case["feasible"] and case["metrics"]["nutrition_score_existing"] < 80:
            failures.append(f"nutrition_score_below_80:{case['id']}")
    return {"automatic_gate": "passed" if not failures else "failed", "failures": failures,
            "release_readiness": "requires_human_culinary_review_and_end_to_end_evidence"}


def markdown(run, assessment, comparison=None, human=None):
    summary = run["summary"]
    lines = ["# Nutrition Solver evaluation lab", "",
             f"Run `{run['run_id']}` · fixture `{run['fixture_provenance']['snapshot_version']}`",
             f"Cases: {summary['case_count']} · feasible: {summary['feasible_count']} · "
             f"p95: {summary['p95_latency_ms']} ms · automatic gate: **{assessment['automatic_gate']}**", "",
             "The automatic gate does not certify culinary quality, nutrition policy or a production release.", "",
             "| ID | Feasible | Candidates | Alternatives | Nutrition | Hard violations | Culinary signals | Repetition | Time ms | Reason |",
             "|---|---|---:|---:|---:|---:|---|---:|---:|---|"]
    for case in run["cases"]:
        metrics = case["metrics"] or {}
        culinary = metrics.get("culinary_signals") or {}
        variety = metrics.get("variety") or {}
        signals = f"affinity {len(culinary.get('affinity_mismatches', []))}; raw/dry {len(culinary.get('raw_or_dry_food_ids', []))}" if metrics else "—"
        nutrition = f"{metrics['nutrition_score_existing']:.1f}" if metrics else "—"
        lines.append(f"| {case['id']} | {case['feasible']} | {case['candidate_count']} | {case['alternative_count']} | "
                     f"{nutrition} | {len(metrics.get('hard_violations', [])) if metrics else '—'} | "
                     f"{signals} | {variety.get('max_daily_repetitions', '—')} | {case['latency_ms']} | {case['reason_code'] or '—'} |")
    lines += ["", "## Automatic gate findings", ""]
    lines += [f"- {failure}" for failure in assessment["failures"]] or ["- None"]
    lines += ["", "## Human review queue", "",
              "Review meal coherence, preparation, portion realism, local relevance and practical usefulness. "
              "A numerical score cannot substitute for this review.", ""]
    lines += [f"- {case_id}" for case_id in summary["human_review_required"]]
    if comparison:
        lines += ["", "## Baseline comparison", "",
                  f"New infeasible: {', '.join(comparison['new_infeasible']) or 'none'}; "
                  f"new hard violation cases: {', '.join(comparison['new_hard_violation_cases']) or 'none'}."]
    if human:
        lines += ["", "## Human review result", "",
                  f"Status: {human['status']}; mean: {human['mean_score']}; "
                  f"errors: {', '.join(human['errors']) or 'none'}."]
    lines += ["", "## Selected alternatives for review", ""]
    for case in run["cases"]:
        lines += [f"### {case['id']} · {case['label']}", ""]
        if not case["feasible"]:
            lines += [f"No solution · candidates {case['candidate_count']} · reason `{case['reason_code']}`.", ""]
            continue
        selected = case["alternatives"][0]
        lines += [f"Nutrition {selected['nutrition_score']:.1f}/100 · "
                  f"alternatives {case['alternative_count']} · "
                  f"stability {case['stability'] or 'not probed'}.", ""]
        for meal in selected["meals"]:
            portions = ", ".join(f"{item['name']} ({item['quantity_g']:g} g)" for item in meal["portions"])
            lines.append(f"- {meal['slot_id']}: {portions}.")
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cases", help="Comma-separated scenario IDs; default is all 30")
    parser.add_argument("--alternatives", type=int, default=3)
    parser.add_argument("--time-limit-ms", type=int, default=1500)
    parser.add_argument("--no-stability", action="store_true")
    parser.add_argument("--compare", type=Path, help="Prior run JSON with matching fixtures and configuration")
    parser.add_argument("--review", type=Path, help="Completed human review JSON for this run")
    args = parser.parse_args()
    run = run_suite(case_ids=set(args.cases.split(",")) if args.cases else None,
                    alternatives=args.alternatives, time_limit_ms=args.time_limit_ms,
                    stability=not args.no_stability)
    assessment = gate(run)
    run["gate"] = assessment
    comparison = compare_runs(json.loads(args.compare.read_text()), run) if args.compare else None
    human = assess_human_review(run, json.loads(args.review.read_text())) if args.review else None
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n")
    if comparison:
        (args.out / "comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n")
    if human:
        (args.out / "human_review_result.json").write_text(json.dumps(human, ensure_ascii=False, indent=2) + "\n")
    (args.out / "report.md").write_text(markdown(run, assessment, comparison, human))
    review = {"run_id": run["run_id"], "reviewer": "", "reviewed_at": "",
              "scale": "1=poor, 5=excellent", "cases": [
                  {"id": item["id"], "coherence": None, "portion_realism": None,
                   "preparation": None, "practicality": None, "local_relevance": None,
                   "notes": ""} for item in run["cases"] if item["feasible"]]}
    (args.out / "human_review_template.json").write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n")
    print(f"{args.out / 'report.md'}: {assessment['automatic_gate']}; "
          f"{run['summary']['feasible_count']}/{run['summary']['case_count']} feasible")


if __name__ == "__main__":
    main()
