"""Regrade saved evidence without starting a new provider conversation."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from types import SimpleNamespace

from notas.application.ai_intake.evaluation_quality import (
    HUMAN_QUALITY_CRITERIA,
    QUALITY_ANNOTATIONS_VERSION,
    grade_validation_reports,
)


def _trajectories(payload):
    if payload.get("version") != "ai_assistant.evaluation_lab.v2":
        raise ValueError("Unsupported evaluation report version.")
    reports = payload.get("live_validations") or []
    if payload.get("mode") != "live_provider" or not reports:
        raise ValueError("Review requires saved live-provider evidence.")
    seen = set()
    for report in reports:
        for scenario in report["scenarios"]:
            key = f"{report['run_id']}/{scenario['key']}"
            if key in seen:
                raise ValueError(f"Duplicate trajectory: {key}")
            seen.add(key)
            evidence = {"run_id": report["run_id"], "provider": report["provider"],
                        "model": report["model"], "scenario": scenario}
            digest = hashlib.sha256(json.dumps(evidence, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            yield key, digest, scenario
    if not seen:
        raise ValueError("Report contains no trajectories to review.")


def saved_review_template(payload):
    return {
        "version": QUALITY_ANNOTATIONS_VERSION,
        "report_run_id": payload.get("run_id"),
        "instructions": "Review the exact saved trajectory. Agent reviews do not count as human approval.",
        "reviews": {
            key: {
                "scenario": scenario["key"],
                "evidence_sha256": digest,
                "reviewer_kind": "human",
                "reviewer": "",
                "criteria": dict.fromkeys(HUMAN_QUALITY_CRITERIA, "pending"),
                "notes": "",
            }
            for key, digest, scenario in _trajectories(payload)
        },
    }


def review_saved_report(payload, annotations):
    template = saved_review_template(payload)
    if annotations.get("report_run_id") != payload["run_id"]:
        raise ValueError("Annotations belong to a different report.")
    reviews = annotations.get("reviews", {})
    if not isinstance(reviews, dict) or set(reviews) - set(template["reviews"]):
        raise ValueError("Annotations contain unknown trajectories.")
    for key, review in reviews.items():
        if not isinstance(review, dict) or review.get("evidence_sha256") != template["reviews"][key]["evidence_sha256"]:
            raise ValueError(f"Evidence changed or review is unbound: {key}")
    reports = []
    for report in payload["live_validations"]:
        results = []
        for scenario in report["scenarios"]:
            if not scenario.get("checks") or not scenario.get("turns"):
                raise ValueError("Saved trajectory is missing checks or turns.")
            results.append(SimpleNamespace(
                scenario=SimpleNamespace(key=scenario["key"], expected_outcome=scenario["expected_outcome"]),
                checks=tuple(SimpleNamespace(**check) for check in scenario["checks"]),
            ))
        reports.append(SimpleNamespace(run_id=report["run_id"], scenarios=results))
    quality = grade_validation_reports(reports, annotations=annotations)
    result = deepcopy(payload)
    result["quality_evaluation"] = quality
    # Review cannot erase fixture, billing, dataset or hard execution failures.
    if payload["status"] in {"passed", "awaiting_quality_review", "quality_regression"}:
        result["status"] = {
            "awaiting_human_review": "awaiting_quality_review",
            "not_run": "awaiting_quality_review",
        }.get(quality["status"], quality["status"])
    result["passed"] = result["status"] == "passed"
    result["review_provenance"] = {
        "source_run_id": payload["run_id"],
        "provider_calls": 0,
        "evidence": {key: value["evidence_sha256"] for key, value in template["reviews"].items()},
    }
    return result
