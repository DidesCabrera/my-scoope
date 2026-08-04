from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from statistics import mean

from django.db.models import Count, Q
from django.utils import timezone

from admin_analytics.filters import AdminAnalyticsFilters
from food_catalog.models import CatalogFood
from notas.domain.model_modules.proposals import NutritionProposal
from notas.domain.models import Food
from nutrition_solver.application.contracts import DEFAULT_OPTIMIZATION_SCORING_CONFIG
from nutrition_solver.application.portion_solver import DEFAULT_PORTION_SOLVER_CONFIG
from nutrition_solver.application.validators import (
    DEFAULT_ERROR_TOLERANCE_PERCENT,
    DEFAULT_REASONABLE_MAX_PORTION_G_BY_ROLE,
    DEFAULT_WARNING_TOLERANCE_PERCENT,
)

SOLVER_SUMMARY_KEY = "nutrition_solver"
ENGINE_VALIDATION_KEY = "engine_validation"
PAYLOAD_VALIDATION_KEY = "payload_validation"
TARGET_COMPARISON_KEY = "target_comparison"


def get_nutrition_solver_metrics(*, now=None, analytics_filters: AdminAnalyticsFilters | None = None, top_limit: int = 10) -> dict:
    """Return ADM07 read-only Nutrition Solver quality metrics.

    Nutrition Solver is currently a pure/application app without database models.
    This selector therefore observes solver quality through persisted proposal
    validation summaries and readiness signals in operational/catalog food data.
    """

    now = now or timezone.now()
    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    since_7d = analytics_filters.since(now=now)
    since_30d = now - timedelta(days=30)

    proposals = NutritionProposal.objects.all()
    proposals_7d = proposals.filter(created_at__gte=since_7d)
    proposals_30d = proposals.filter(created_at__gte=since_30d)

    solver_rows = []
    engine_rows = []
    payload_rows = []
    target_rows = []

    for proposal in proposals.only("id", "source", "status", "created_at", "validation_summary"):
        summary = proposal.validation_summary or {}
        if not isinstance(summary, dict):
            continue
        if isinstance(summary.get(SOLVER_SUMMARY_KEY), dict):
            solver_rows.append(_build_solver_row(proposal, summary[SOLVER_SUMMARY_KEY]))
        if isinstance(summary.get(ENGINE_VALIDATION_KEY), dict):
            engine_rows.append(_build_engine_row(proposal, summary[ENGINE_VALIDATION_KEY]))
        if isinstance(summary.get(PAYLOAD_VALIDATION_KEY), dict):
            payload_rows.append(_build_payload_row(proposal, summary[PAYLOAD_VALIDATION_KEY]))
        if isinstance(summary.get(TARGET_COMPARISON_KEY), dict):
            target_rows.append(_build_target_row(proposal, summary[TARGET_COMPARISON_KEY]))

    solver_7d = [row for row in solver_rows if row["created_at"] and row["created_at"] >= since_7d]
    solver_30d = [row for row in solver_rows if row["created_at"] and row["created_at"] >= since_30d]
    engine_7d = [row for row in engine_rows if row["created_at"] and row["created_at"] >= since_7d]
    engine_30d = [row for row in engine_rows if row["created_at"] and row["created_at"] >= since_30d]
    payload_7d = [row for row in payload_rows if row["created_at"] and row["created_at"] >= since_7d]

    operational_foods = Food.objects.all()
    operational_solver_foods = operational_foods.filter(is_active=True, solver_enabled=True)
    operational_verified_solver_foods = operational_solver_foods.filter(is_verified=True)
    operational_missing_macro = operational_solver_foods.none()
    operational_no_group = operational_solver_foods.filter(food_group="")
    operational_unknown_preparation = operational_solver_foods.filter(preparation_state=Food.PREPARATION_UNKNOWN)

    catalog_foods = CatalogFood.objects.all()
    catalog_solver_candidates = catalog_foods.filter(
        solver_enabled=True,
        status__in=[CatalogFood.STATUS_PUBLISHED, CatalogFood.STATUS_VERIFIED],
    )
    catalog_solver_with_bounds = catalog_solver_candidates.filter(
        solver_min_portion_g__isnull=False,
        solver_max_portion_g__isnull=False,
    )
    catalog_solver_high_quality = catalog_solver_candidates.filter(data_quality_score__gte=80)

    return {
        "generated_at": now,
        "period_label": analytics_filters.period_label,
        "proposals": {
            "total": proposals.count(),
            "created_7d": proposals_7d.count(),
            "created_30d": proposals_30d.count(),
            "with_solver_summary_total": len(solver_rows),
            "with_solver_summary_7d": len(solver_7d),
            "with_solver_summary_30d": len(solver_30d),
            "with_engine_validation_total": len(engine_rows),
            "with_engine_validation_7d": len(engine_7d),
            "with_engine_validation_30d": len(engine_30d),
            "payload_validation_total": len(payload_rows),
            "payload_validation_7d": len(payload_7d),
            "payload_valid_total": sum(1 for row in payload_rows if row["is_valid"] is True),
            "payload_invalid_total": sum(1 for row in payload_rows if row["is_valid"] is False),
            "target_comparison_total": len(target_rows),
        },
        "solver_quality": {
            "status_rows": _counter_rows(solver_rows, "solver_status", label_key="status"),
            "status_rows_7d": _counter_rows(solver_7d, "solver_status", label_key="status"),
            "reason_rows": _counter_rows(solver_rows, "reason_code", label_key="reason_code", top_limit=top_limit),
            "worst_macro_rows": _counter_rows(solver_rows, "worst_macro", label_key="macro"),
            "source_rows": _source_rows(solver_rows),
            "avg_score": _avg(row["score"] for row in solver_rows),
            "avg_iterations": _avg(row["iterations"] for row in solver_rows),
            "avg_candidate_count": _avg(row["candidate_count"] for row in solver_rows),
            "avg_worst_deviation_percent": _avg(row["worst_deviation_percent"] for row in solver_rows),
            "warning_count": sum(row["warning_count"] for row in solver_rows),
            "error_count": sum(row["error_count"] for row in solver_rows),
            "empty_candidate_count": sum(1 for row in solver_rows if row["candidate_count"] == 0),
        },
        "engine_validation": {
            "status_rows": _counter_rows(engine_rows, "status", label_key="status"),
            "status_rows_7d": _counter_rows(engine_7d, "status", label_key="status"),
            "issue_rows": _issue_rows(engine_rows, top_limit=top_limit),
            "metric_rows": _target_metric_rows(target_rows),
            "valid_total": sum(1 for row in engine_rows if row["is_valid"] is True),
            "invalid_total": sum(1 for row in engine_rows if row["is_valid"] is False),
            "warnings_total": sum(1 for row in engine_rows if row["has_warnings"] is True),
            "errors_total": sum(1 for row in engine_rows if row["has_errors"] is True),
        },
        "candidate_readiness": {
            "operational_foods_total": operational_foods.count(),
            "operational_solver_enabled": operational_solver_foods.count(),
            "operational_verified_solver_enabled": operational_verified_solver_foods.count(),
            "operational_missing_macro": operational_missing_macro.count(),
            "operational_no_group": operational_no_group.count(),
            "operational_unknown_preparation": operational_unknown_preparation.count(),
            "catalog_solver_candidates": catalog_solver_candidates.count(),
            "catalog_solver_high_quality": catalog_solver_high_quality.count(),
            "catalog_solver_with_bounds": catalog_solver_with_bounds.count(),
            "catalog_status_rows": list(
                catalog_foods.filter(solver_enabled=True)
                .values("status")
                .annotate(total=Count("id"), high_quality=Count("id", filter=Q(data_quality_score__gte=80)))
                .order_by("status")
            ),
            "operational_group_rows": list(
                operational_solver_foods.values("food_group")
                .annotate(total=Count("id"), verified=Count("id", filter=Q(is_verified=True)))
                .order_by("food_group")[:top_limit]
            ),
        },
        "config": {
            "portion_solver": {
                "max_iterations": DEFAULT_PORTION_SOLVER_CONFIG.max_iterations,
                "protein_weight": DEFAULT_PORTION_SOLVER_CONFIG.protein_weight,
                "carbs_weight": DEFAULT_PORTION_SOLVER_CONFIG.carbs_weight,
                "fat_weight": DEFAULT_PORTION_SOLVER_CONFIG.fat_weight,
                "kcal_weight": DEFAULT_PORTION_SOLVER_CONFIG.kcal_weight,
                "overshoot_penalty_weight": DEFAULT_PORTION_SOLVER_CONFIG.overshoot_penalty_weight,
                "undershoot_penalty_weight": DEFAULT_PORTION_SOLVER_CONFIG.undershoot_penalty_weight,
                "optional_food_penalty_weight": DEFAULT_PORTION_SOLVER_CONFIG.optional_food_penalty_weight,
            },
            "optimization_scoring": DEFAULT_OPTIMIZATION_SCORING_CONFIG.as_dict(),
            "warning_tolerance_percent": dict(DEFAULT_WARNING_TOLERANCE_PERCENT),
            "error_tolerance_percent": dict(DEFAULT_ERROR_TOLERANCE_PERCENT),
            "reasonable_max_portion_g_by_role": dict(DEFAULT_REASONABLE_MAX_PORTION_G_BY_ROLE),
        },
    }


def _build_solver_row(proposal, solver_summary: dict) -> dict:
    result = _safe_dict(solver_summary.get("result"))
    diagnostics = _safe_dict(result.get("diagnostics"))
    assessment = _safe_dict(diagnostics.get("assessment"))
    candidate_preview = _safe_dict(solver_summary.get("candidate_preview"))
    metadata = _safe_dict(diagnostics.get("metadata"))
    issue_counts = _safe_dict(diagnostics.get("issue_counts"))
    return {
        "proposal_id": proposal.id,
        "source": proposal.source,
        "proposal_status": proposal.status,
        "created_at": proposal.created_at,
        "solver_status": str(solver_summary.get("status") or result.get("status") or "unknown"),
        "reason_code": str(assessment.get("reason_code") or "unknown"),
        "worst_macro": str(assessment.get("worst_macro") or "unknown"),
        "worst_deviation_percent": _to_float(assessment.get("worst_deviation_percent")),
        "score": _to_float(result.get("score") or diagnostics.get("score")),
        "iterations": _to_float(metadata.get("iterations")),
        "candidate_count": _to_float(candidate_preview.get("count")),
        "warning_count": int(issue_counts.get("warnings") or len(diagnostics.get("warnings") or [])),
        "error_count": int(issue_counts.get("errors") or len(diagnostics.get("errors") or [])),
    }


def _build_engine_row(proposal, engine_validation: dict) -> dict:
    return {
        "proposal_id": proposal.id,
        "source": proposal.source,
        "proposal_status": proposal.status,
        "created_at": proposal.created_at,
        "status": str(engine_validation.get("status") or "unknown"),
        "is_valid": engine_validation.get("is_valid"),
        "has_warnings": engine_validation.get("has_warnings"),
        "has_errors": engine_validation.get("has_errors"),
        "issues": engine_validation.get("issues") or [],
    }


def _build_payload_row(proposal, payload_validation: dict) -> dict:
    return {
        "proposal_id": proposal.id,
        "source": proposal.source,
        "proposal_status": proposal.status,
        "created_at": proposal.created_at,
        "intent": str(payload_validation.get("intent") or "unknown"),
        "is_valid": payload_validation.get("is_valid"),
    }


def _build_target_row(proposal, target_comparison: dict) -> dict:
    return {
        "proposal_id": proposal.id,
        "source": proposal.source,
        "proposal_status": proposal.status,
        "created_at": proposal.created_at,
        "comparison": target_comparison,
    }


def _source_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = defaultdict(lambda: {"source": "unknown", "total": 0, "optimal": 0, "acceptable": 0, "partial": 0, "impossible": 0, "avg_score_values": []})
    for row in rows:
        source = row.get("source") or "unknown"
        target = grouped[source]
        target["source"] = source
        target["total"] += 1
        status = row.get("solver_status") or "unknown"
        if status in {"optimal", "acceptable", "partial", "impossible"}:
            target[status] += 1
        if row.get("score") is not None:
            target["avg_score_values"].append(row["score"])
    result = []
    for row in grouped.values():
        values = row.pop("avg_score_values")
        row["avg_score"] = mean(values) if values else None
        result.append(row)
    return sorted(result, key=lambda item: (-item["total"], item["source"]))


def _issue_rows(rows: list[dict], *, top_limit: int) -> list[dict]:
    counter: Counter[tuple[str, str, str]] = Counter()
    for row in rows:
        for issue in row.get("issues") or []:
            if not isinstance(issue, dict):
                continue
            key = (
                str(issue.get("severity") or "unknown"),
                str(issue.get("code") or "unknown"),
                str(issue.get("metric") or "—"),
            )
            counter[key] += 1
    return [
        {"severity": severity, "code": code, "metric": metric, "total": total}
        for (severity, code, metric), total in counter.most_common(top_limit)
    ]


def _target_metric_rows(rows: list[dict]) -> list[dict]:
    metrics = ["total_kcal", "kcal", "protein", "carbs", "fat"]
    result = []
    for metric in metrics:
        values = []
        for row in rows:
            comparison = row.get("comparison") or {}
            metric_summary = comparison.get(metric)
            if not isinstance(metric_summary, dict):
                continue
            diff_percent = metric_summary.get("diff_percent")
            if diff_percent is not None:
                values.append(abs(float(diff_percent)))
        if values:
            result.append({"metric": metric, "samples": len(values), "avg_abs_diff_percent": mean(values), "max_abs_diff_percent": max(values)})
    return result


def _counter_rows(rows: list[dict], field: str, *, label_key: str, top_limit: int | None = None) -> list[dict]:
    counter = Counter(str(row.get(field) or "unknown") for row in rows)
    most_common = counter.most_common(top_limit)
    return [{label_key: label, "total": total} for label, total in most_common]


def _avg(values) -> float | None:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None
    return mean(clean)


def _safe_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
