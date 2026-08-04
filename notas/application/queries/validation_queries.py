from notas.application.dto.validation_dto import (
    DailyPlanValidationSummaryDTO,
    ValidationMetricDTO,
)
from notas.application.queries.dailyplan_queries import get_dailyplan_detail

SUPPORTED_DAILYPLAN_TARGETS = {
    "total_kcal",
    "protein",
    "carbs",
    "fat",
    "ppk",
}


DEFAULT_DAILYPLAN_TARGET_TOLERANCES = {
    "total_kcal": 100.0,
    "protein": 10.0,
    "carbs": 10.0,
    "fat": 10.0,
    "ppk": 0.1,
}


def _validate_supported_targets(targets: dict) -> None:
    unsupported_targets = set(targets.keys()) - SUPPORTED_DAILYPLAN_TARGETS

    if unsupported_targets:
        unsupported = ", ".join(sorted(unsupported_targets))
        supported = ", ".join(sorted(SUPPORTED_DAILYPLAN_TARGETS))

        raise ValueError(
            f"Unsupported target metrics: {unsupported}. "
            f"Supported metrics are: {supported}."
        )


def _get_tolerance_for_metric(
    metric: str,
    tolerances: dict | None,
) -> float:
    if tolerances and metric in tolerances:
        return float(tolerances[metric])

    return DEFAULT_DAILYPLAN_TARGET_TOLERANCES[metric]


def _get_metric_status(delta: float, within_tolerance: bool) -> str:
    if within_tolerance:
        return "within_tolerance"

    if delta < 0:
        return "under_target"

    return "over_target"


def compare_dailyplan_to_targets(
    user,
    dailyplan_id: int,
    targets: dict,
    tolerances: dict | None = None,
) -> DailyPlanValidationSummaryDTO:
    """
    Compara un DailyPlan visible para el usuario contra targets numéricos.

    Esta query es read-only y serializable. Está pensada para web/API/MCP/IA.
    No modifica el plan y no crea propuestas.
    """
    targets = targets or {}
    tolerances = tolerances or {}

    _validate_supported_targets(targets)

    dailyplan = get_dailyplan_detail(
        user,
        dailyplan_id,
    )

    kpis = dailyplan.kpis

    actual_values = {
        "total_kcal": float(kpis.total_kcal),
        "protein": float(kpis.protein),
        "carbs": float(kpis.carbs),
        "fat": float(kpis.fat),
        "ppk": float(kpis.ppk),
    }

    metrics = []

    for metric, target_value in targets.items():
        target = float(target_value)
        actual = actual_values[metric]
        delta = actual - target
        tolerance = _get_tolerance_for_metric(
            metric,
            tolerances,
        )
        within_tolerance = abs(delta) <= tolerance

        metrics.append(
            ValidationMetricDTO(
                metric=metric,
                target=target,
                actual=actual,
                delta=delta,
                tolerance=tolerance,
                within_tolerance=within_tolerance,
                status=_get_metric_status(
                    delta,
                    within_tolerance,
                ),
            )
        )

    return DailyPlanValidationSummaryDTO(
        dailyplan_id=dailyplan.id,
        dailyplan_name=dailyplan.name,
        targets={
            metric.metric: metric.target
            for metric in metrics
        },
        actual={
            metric.metric: metric.actual
            for metric in metrics
        },
        delta={
            metric.metric: metric.delta
            for metric in metrics
        },
        tolerances={
            metric.metric: metric.tolerance
            for metric in metrics
        },
        within_tolerance=all(
            metric.within_tolerance
            for metric in metrics
        ),
        metrics=metrics,
    )
    