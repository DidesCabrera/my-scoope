from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from math import isfinite
from typing import Iterable

from notas.application.nutrition_engine.models import MacroTarget

STATUS_OK = "ok"
STATUS_WARNING = "warning"
STATUS_ERROR = "error"

STATUS_ORDER = {
    STATUS_OK: 0,
    STATUS_WARNING: 1,
    STATUS_ERROR: 2,
}

METRIC_LABELS = {
    "kcal": "Kcal",
    "protein": "Proteína",
    "carbs": "Carbohidratos",
    "fat": "Grasa",
}

DEFAULT_WARNING_TOLERANCE_PERCENT = {
    "kcal": 5.0,
    "protein": 10.0,
    "carbs": 10.0,
    "fat": 10.0,
}

DEFAULT_ERROR_TOLERANCE_PERCENT = {
    "kcal": 12.0,
    "protein": 20.0,
    "carbs": 25.0,
    "fat": 25.0,
}

DEFAULT_REASONABLE_MAX_PORTION_G_BY_ROLE = {
    "protein": 350.0,
    "carb": 420.0,
    "fat": 120.0,
    "vegetable": 350.0,
    "unknown": 500.0,
}


@dataclass(frozen=True)
class NutritionValidationIssue:
    severity: str
    code: str
    message: str
    metric: str | None = None
    value: float | int | str | None = None
    target: float | int | str | None = None
    diff_percent: float | None = None
    context: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "metric": self.metric,
            "value": self.value,
            "target": self.target,
            "diff_percent": round(self.diff_percent, 2) if self.diff_percent is not None else None,
            "context": dict(self.context),
        }


@dataclass(frozen=True)
class PortionValidationInput:
    food_id: int
    food_name: str
    quantity_g: float
    role: str = "unknown"
    minimum_g: float | None = None
    maximum_g: float | None = None

    def as_dict(self) -> dict:
        return {
            "food_id": int(self.food_id),
            "food_name": self.food_name,
            "quantity_g": round(float(self.quantity_g), 2),
            "role": self.role,
            "minimum_g": round(float(self.minimum_g), 2) if self.minimum_g is not None else None,
            "maximum_g": round(float(self.maximum_g), 2) if self.maximum_g is not None else None,
        }


@dataclass(frozen=True)
class StrictNutritionValidationConfig:
    warning_tolerance_percent: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_WARNING_TOLERANCE_PERCENT)
    )
    error_tolerance_percent: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_ERROR_TOLERANCE_PERCENT)
    )
    reasonable_max_portion_g_by_role: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_REASONABLE_MAX_PORTION_G_BY_ROLE)
    )
    tiny_portion_warning_g: float = 5.0


@dataclass(frozen=True)
class NutritionValidationResult:
    target: MacroTarget
    actual: MacroTarget
    comparison: dict[str, dict]
    is_within_initial_tolerance: bool
    notes: list[str]

    def as_dict(self) -> dict:
        return {
            "target": self.target.as_dict(),
            "actual": self.actual.as_dict(),
            "comparison": self.comparison,
            "is_within_initial_tolerance": self.is_within_initial_tolerance,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class StrictNutritionValidationResult:
    target: MacroTarget
    actual: MacroTarget
    comparison: dict[str, dict]
    status: str
    issues: list[NutritionValidationIssue]
    notes: list[str]
    summary: str

    @property
    def is_valid(self) -> bool:
        return self.status != STATUS_ERROR

    @property
    def has_warnings(self) -> bool:
        return any(issue.severity == STATUS_WARNING for issue in self.issues)

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == STATUS_ERROR for issue in self.issues)

    def as_dict(self) -> dict:
        return {
            "target": self.target.as_dict(),
            "actual": self.actual.as_dict(),
            "comparison": self.comparison,
            "status": self.status,
            "is_valid": self.is_valid,
            "has_warnings": self.has_warnings,
            "has_errors": self.has_errors,
            "issues": [issue.as_dict() for issue in self.issues],
            "notes": list(self.notes),
            "summary": self.summary,
        }


def compare_macro_targets(
    *,
    target: MacroTarget,
    actual: MacroTarget,
    kcal_tolerance_percent: float = 5,
    macro_tolerance_percent: float = 10,
) -> NutritionValidationResult:
    comparison = {
        "kcal": _metric_comparison(actual=actual.kcal, target=target.kcal),
        "protein": _metric_comparison(actual=actual.protein, target=target.protein),
        "carbs": _metric_comparison(actual=actual.carbs, target=target.carbs),
        "fat": _metric_comparison(actual=actual.fat, target=target.fat),
    }
    is_within = (
        abs(comparison["kcal"]["diff_percent"] or 0) <= kcal_tolerance_percent
        and abs(comparison["protein"]["diff_percent"] or 0) <= macro_tolerance_percent
        and abs(comparison["carbs"]["diff_percent"] or 0) <= macro_tolerance_percent
        and abs(comparison["fat"]["diff_percent"] or 0) <= macro_tolerance_percent
    )
    notes = []
    if is_within:
        notes.append("La propuesta está dentro de la tolerancia inicial del motor nutricional.")
    else:
        notes.append("La propuesta requiere ajuste fino antes de aplicarse como plan final.")

    return NutritionValidationResult(
        target=target,
        actual=actual,
        comparison=comparison,
        is_within_initial_tolerance=is_within,
        notes=notes,
    )


def validate_generated_dailyplan(
    *,
    target: MacroTarget,
    actual: MacroTarget,
    expected_meals_count: int | None = None,
    actual_meals_count: int | None = None,
    excluded_terms: Iterable[str] = (),
    portions: Iterable[PortionValidationInput | dict] = (),
    config: StrictNutritionValidationConfig | None = None,
) -> StrictNutritionValidationResult:
    """Run strict validation for a generated DailyPlan proposal.

    This validator is intentionally independent from Django models and the chat
    UI. It receives calculated nutrition, structural expectations and concrete
    portions, then returns a serializable report that can be stored in
    NutritionProposal.validation_summary, displayed by the UI or exposed through
    MCP/API tools.
    """
    config = config or StrictNutritionValidationConfig()
    comparison = _strict_metric_comparison(
        target=target,
        actual=actual,
        config=config,
    )
    issues: list[NutritionValidationIssue] = []
    issues.extend(_build_macro_issues(comparison))
    issues.extend(
        _build_meal_count_issues(
            expected_meals_count=expected_meals_count,
            actual_meals_count=actual_meals_count,
        )
    )
    normalized_portions = [_normalize_portion(portion) for portion in portions]
    issues.extend(
        _build_exclusion_issues(
            portions=normalized_portions,
            excluded_terms=excluded_terms,
        )
    )
    issues.extend(
        _build_portion_issues(
            portions=normalized_portions,
            config=config,
        )
    )

    status = _highest_status(issue.severity for issue in issues)
    notes = _build_strict_notes(status=status, issues=issues)

    return StrictNutritionValidationResult(
        target=target,
        actual=actual,
        comparison=comparison,
        status=status,
        issues=issues,
        notes=notes,
        summary=_build_summary(status=status, issues=issues),
    )


def _strict_metric_comparison(
    *,
    target: MacroTarget,
    actual: MacroTarget,
    config: StrictNutritionValidationConfig,
) -> dict[str, dict]:
    comparison = {
        "kcal": _metric_comparison(actual=actual.kcal, target=target.kcal),
        "protein": _metric_comparison(actual=actual.protein, target=target.protein),
        "carbs": _metric_comparison(actual=actual.carbs, target=target.carbs),
        "fat": _metric_comparison(actual=actual.fat, target=target.fat),
    }

    for metric, metric_comparison in comparison.items():
        diff_percent = metric_comparison["diff_percent"]
        warning_tolerance = config.warning_tolerance_percent.get(metric, 10.0)
        error_tolerance = config.error_tolerance_percent.get(metric, warning_tolerance * 2)
        status = _status_for_diff_percent(
            diff_percent=diff_percent,
            warning_tolerance=warning_tolerance,
            error_tolerance=error_tolerance,
        )
        metric_comparison.update(
            {
                "status": status,
                "warning_tolerance_percent": round(float(warning_tolerance), 2),
                "error_tolerance_percent": round(float(error_tolerance), 2),
            }
        )

    return comparison


def _build_macro_issues(comparison: dict[str, dict]) -> list[NutritionValidationIssue]:
    issues = []
    for metric, metric_comparison in comparison.items():
        status = metric_comparison["status"]
        if status == STATUS_OK:
            continue

        diff = metric_comparison["diff"]
        diff_label = "sobre" if diff > 0 else "bajo"
        tolerance_key = "error_tolerance_percent" if status == STATUS_ERROR else "warning_tolerance_percent"
        issues.append(
            NutritionValidationIssue(
                severity=status,
                code=f"{metric}_outside_{status}_tolerance",
                metric=metric,
                value=metric_comparison["actual"],
                target=metric_comparison["target"],
                diff_percent=metric_comparison["diff_percent"],
                message=(
                    f"{METRIC_LABELS.get(metric, metric)} queda {diff_label} el objetivo "
                    f"por {abs(metric_comparison['diff_percent'] or 0):.2f}% "
                    f"(límite {metric_comparison[tolerance_key]:.2f}%)."
                ),
            )
        )
    return issues


def _build_meal_count_issues(
    *,
    expected_meals_count: int | None,
    actual_meals_count: int | None,
) -> list[NutritionValidationIssue]:
    if expected_meals_count is None or actual_meals_count is None:
        return []

    if int(expected_meals_count) == int(actual_meals_count):
        return []

    return [
        NutritionValidationIssue(
            severity=STATUS_ERROR,
            code="meal_count_mismatch",
            metric="meals_per_day",
            value=int(actual_meals_count),
            target=int(expected_meals_count),
            message=(
                f"La propuesta contiene {actual_meals_count} comidas, "
                f"pero el brief exige {expected_meals_count}."
            ),
        )
    ]


def _build_exclusion_issues(
    *,
    portions: list[PortionValidationInput],
    excluded_terms: Iterable[str],
) -> list[NutritionValidationIssue]:
    normalized_exclusions = _normalize_terms(excluded_terms)
    if not normalized_exclusions:
        return []

    issues = []
    for portion in portions:
        matched_terms = [
            term
            for term in normalized_exclusions
            if term and term in _normalize_text(portion.food_name)
        ]
        if not matched_terms:
            continue

        issues.append(
            NutritionValidationIssue(
                severity=STATUS_ERROR,
                code="excluded_food_used",
                value=portion.food_name,
                message=(
                    f"La propuesta usa '{portion.food_name}', que coincide con exclusiones "
                    f"del brief: {', '.join(matched_terms)}."
                ),
                context={
                    "food_id": portion.food_id,
                    "matched_terms": matched_terms,
                },
            )
        )
    return issues


def _build_portion_issues(
    *,
    portions: list[PortionValidationInput],
    config: StrictNutritionValidationConfig,
) -> list[NutritionValidationIssue]:
    issues = []
    for portion in portions:
        quantity = float(portion.quantity_g)
        context = portion.as_dict()

        if quantity <= 0:
            issues.append(
                NutritionValidationIssue(
                    severity=STATUS_ERROR,
                    code="portion_must_be_positive",
                    value=quantity,
                    target="> 0",
                    message=f"La porción de '{portion.food_name}' debe ser mayor a 0 g.",
                    context=context,
                )
            )
            continue

        if portion.minimum_g is not None and quantity < float(portion.minimum_g):
            issues.append(
                NutritionValidationIssue(
                    severity=STATUS_ERROR,
                    code="portion_below_minimum",
                    value=quantity,
                    target=float(portion.minimum_g),
                    message=(
                        f"La porción de '{portion.food_name}' ({quantity:.2f} g) queda bajo "
                        f"el mínimo permitido ({float(portion.minimum_g):.2f} g)."
                    ),
                    context=context,
                )
            )

        if portion.maximum_g is not None and quantity > float(portion.maximum_g):
            issues.append(
                NutritionValidationIssue(
                    severity=STATUS_ERROR,
                    code="portion_above_maximum",
                    value=quantity,
                    target=float(portion.maximum_g),
                    message=(
                        f"La porción de '{portion.food_name}' ({quantity:.2f} g) supera "
                        f"el máximo permitido ({float(portion.maximum_g):.2f} g)."
                    ),
                    context=context,
                )
            )
            continue

        reasonable_max = config.reasonable_max_portion_g_by_role.get(
            portion.role,
            config.reasonable_max_portion_g_by_role["unknown"],
        )
        if quantity > reasonable_max:
            issues.append(
                NutritionValidationIssue(
                    severity=STATUS_WARNING,
                    code="portion_unusually_high",
                    value=quantity,
                    target=reasonable_max,
                    message=(
                        f"La porción de '{portion.food_name}' ({quantity:.2f} g) parece alta "
                        f"para el rol {portion.role}."
                    ),
                    context=context,
                )
            )

        if 0 < quantity < config.tiny_portion_warning_g:
            issues.append(
                NutritionValidationIssue(
                    severity=STATUS_WARNING,
                    code="portion_unusually_low",
                    value=quantity,
                    target=config.tiny_portion_warning_g,
                    message=(
                        f"La porción de '{portion.food_name}' ({quantity:.2f} g) es muy baja "
                        "para una propuesta revisable."
                    ),
                    context=context,
                )
            )

    return issues


def _normalize_portion(portion: PortionValidationInput | dict) -> PortionValidationInput:
    if isinstance(portion, PortionValidationInput):
        return portion

    return PortionValidationInput(
        food_id=int(portion.get("food_id") or 0),
        food_name=str(portion.get("food_name") or portion.get("name") or "Alimento"),
        quantity_g=float(portion.get("quantity_g") or portion.get("quantity") or 0),
        role=str(portion.get("role") or "unknown"),
        minimum_g=_optional_float(portion.get("minimum_g")),
        maximum_g=_optional_float(portion.get("maximum_g")),
    )


def _optional_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _metric_comparison(*, actual: float, target: float) -> dict:
    diff = float(actual) - float(target)
    return {
        "target": round(float(target), 2),
        "actual": round(float(actual), 2),
        "diff": round(diff, 2),
        "diff_percent": _round_or_none(_diff_percent(actual=actual, target=target)),
    }


def _status_for_diff_percent(
    *,
    diff_percent: float | None,
    warning_tolerance: float,
    error_tolerance: float,
) -> str:
    if diff_percent is None:
        return STATUS_WARNING

    absolute_diff = abs(float(diff_percent))
    if absolute_diff > float(error_tolerance):
        return STATUS_ERROR
    if absolute_diff > float(warning_tolerance):
        return STATUS_WARNING
    return STATUS_OK


def _highest_status(severities: Iterable[str]) -> str:
    status = STATUS_OK
    for severity in severities:
        if STATUS_ORDER.get(severity, 0) > STATUS_ORDER[status]:
            status = severity
    return status


def _diff_percent(*, actual: float, target: float) -> float | None:
    if not target:
        return None
    value = ((float(actual) - float(target)) / float(target)) * 100
    if not isfinite(value):
        return None
    return value


def _round_or_none(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _build_strict_notes(*, status: str, issues: list[NutritionValidationIssue]) -> list[str]:
    if status == STATUS_OK:
        return [
            "La propuesta cumple la validación nutricional estricta inicial.",
            "No se detectaron desviaciones relevantes, exclusiones incumplidas ni porciones fuera de rango.",
        ]

    error_count = sum(1 for issue in issues if issue.severity == STATUS_ERROR)
    warning_count = sum(1 for issue in issues if issue.severity == STATUS_WARNING)
    notes = []
    if error_count:
        notes.append(f"Se detectaron {error_count} error(es) que deben corregirse antes de considerar la propuesta estable.")
    if warning_count:
        notes.append(f"Se detectaron {warning_count} advertencia(s) para revisión humana o ajuste fino.")
    notes.append("La propuesta sigue siendo revisable, pero el motor deja explícitas sus desviaciones.")
    return notes


def _build_summary(*, status: str, issues: list[NutritionValidationIssue]) -> str:
    if status == STATUS_OK:
        return "Validación estricta OK: macros, estructura, exclusiones y porciones dentro de rango."

    error_count = sum(1 for issue in issues if issue.severity == STATUS_ERROR)
    warning_count = sum(1 for issue in issues if issue.severity == STATUS_WARNING)
    return (
        f"Validación estricta con estado {status}: "
        f"{error_count} error(es), {warning_count} advertencia(s)."
    )


def _normalize_terms(values: Iterable[str]) -> list[str]:
    return [
        _normalize_text(value)
        for value in values
        if _normalize_text(value)
    ]


def _normalize_text(value: str) -> str:
    text = " ".join(str(value or "").strip().lower().split())
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )
