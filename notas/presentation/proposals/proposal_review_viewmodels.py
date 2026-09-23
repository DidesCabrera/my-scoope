from dataclasses import asdict, dataclass
from typing import Any

from django.urls import reverse

from notas.application.dto.proposal_iteration_trace import extract_plan_iteration_trace
from notas.application.proposals.contracts import (
    AI_NUTRITION_BRIEF_INTENT,
    CREATE_DAILYPLAN_INTENT,
    CREATE_MEAL_INTENT,
    can_apply_proposal,
    get_proposal_intent_contract,
    proposal_status_label,
    resolve_proposal_intent,
)
from notas.application.proposals.subject_context_warnings import (
    build_proposal_subject_context_warning,
)
from notas.domain.services.nutrition import macro_kcal_distribution
from notas.presentation.viewmodels.programs import (
    FULL_DAY_LABELS,
    build_program_metric_chart,
    build_week_day_nutrition_rows,
    build_week_kpi_ranges,
)


@dataclass(frozen=True)
class ProposalReviewStatusVM:
    status: str
    label: str
    is_reviewable: bool
    is_final: bool
    is_approved: bool
    is_applied: bool

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ProposalReviewFoodVM:
    food_id: int | None
    food_name: str
    quantity: float | None
    unit: str
    protein: float | None
    carbs: float | None
    fat: float | None
    total_kcal: float | None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ProposalReviewKpisVM:
    total_kcal: float | None
    protein: float | None
    carbs: float | None
    fat: float | None
    ppk: float | None
    alloc_protein: float | None
    alloc_carbs: float | None
    alloc_fat: float | None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ProposalReviewMealVM:
    name: str
    foods: list[ProposalReviewFoodVM]
    kpis: ProposalReviewKpisVM | None
    card: dict[str, Any]

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "foods": [
                food.as_dict()
                for food in self.foods
            ],
            "kpis": self.kpis.as_dict() if self.kpis else None,
            "card": self.card,
        }


@dataclass(frozen=True)
class ProposalReviewDailyPlanMealVM:
    hour: str | None
    note: str
    meal: ProposalReviewMealVM

    def as_dict(self) -> dict:
        return {
            "hour": self.hour,
            "note": self.note,
            "meal": self.meal.as_dict(),
        }


@dataclass(frozen=True)
class ProposalReviewDailyPlanVM:
    name: str
    meals: list[ProposalReviewDailyPlanMealVM]
    kpis: ProposalReviewKpisVM | None
    card: dict[str, Any]

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "meals": [
                meal.as_dict()
                for meal in self.meals
            ],
            "kpis": self.kpis.as_dict() if self.kpis else None,
            "card": self.card,
        }


@dataclass(frozen=True)
class ProposalAppliedResultVM:
    kind: str | None
    object_id: int | None
    object_name: str
    detail_url_name: str | None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ProposalIterationTraceVM:
    previous_proposal_id: int | None
    previous_proposal_url: str | None
    user_message: str
    command_labels: list[str]
    command_count: int
    short_label: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ProposalSubjectContextWarningVM:
    requires_warning: bool
    source: str
    source_label: str
    ppk_weight_source: str
    ppk_weight_source_label: str
    calculation_weight_kg: float | None
    calculation_weight_label: str
    title: str
    message: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ProposalReviewPayloadVM:
    intent: str | None
    entity_title: str
    attachments: list[dict[str, str]]
    is_create_meal: bool
    is_create_dailyplan: bool
    is_apply_supported: bool
    proposed_payload: dict[str, Any]
    simulation: dict[str, Any] | None
    targets: dict[str, Any]
    meal: ProposalReviewMealVM | None
    dailyplan: ProposalReviewDailyPlanVM | None
    program: dict[str, Any] | None = None

    def as_dict(self) -> dict:
        payload = {
            "intent": self.intent,
            "entity_title": self.entity_title,
            "attachments": self.attachments,
            "is_create_meal": self.is_create_meal,
            "is_create_dailyplan": self.is_create_dailyplan,
            "is_apply_supported": self.is_apply_supported,
            "proposed_payload": self.proposed_payload,
            "simulation": self.simulation,
            "targets": self.targets,
            "meal": self.meal.as_dict() if self.meal else None,
            "dailyplan": self.dailyplan.as_dict() if self.dailyplan else None,
        }
        if self.intent == "create_program":
            payload.update({"is_create_program": True, "program": self.program})
        return payload


@dataclass(frozen=True)
class ProposalReviewVM:
    proposal_id: int
    title: str
    summary: str
    dailyplan_id: int | None
    dailyplan_name: str
    created_by_username: str | None
    reviewed_by_username: str | None
    received_at_label: str
    is_read: bool
    status: ProposalReviewStatusVM
    payload: ProposalReviewPayloadVM
    can_apply: bool
    subject_context_warning: ProposalSubjectContextWarningVM
    applied_result: ProposalAppliedResultVM | None
    iteration_trace: ProposalIterationTraceVM | None
    alternatives: list[dict[str, Any]]
    selected_alternative_id: str

    def as_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "summary": self.summary,
            "dailyplan_id": self.dailyplan_id,
            "dailyplan_name": self.dailyplan_name,
            "created_by_username": self.created_by_username,
            "reviewed_by_username": self.reviewed_by_username,
            "received_at_label": self.received_at_label,
            "is_read": self.is_read,
            "status": self.status.as_dict(),
            "payload": self.payload.as_dict(),
            "can_apply": self.can_apply,
            "subject_context_warning": self.subject_context_warning.as_dict(),
            "applied_result": (
                self.applied_result.as_dict()
                if self.applied_result
                else None
            ),
            "iteration_trace": (
                self.iteration_trace.as_dict()
                if self.iteration_trace
                else None
            ),
            "alternatives": self.alternatives,
            "selected_alternative_id": self.selected_alternative_id,
        }


def build_proposal_review_vm(
    proposal: dict[str, Any],
) -> ProposalReviewVM:
    proposed_payload = _safe_dict(
        proposal.get("proposed_payload"),
    )
    validation_summary = _safe_dict(
        proposal.get("validation_summary"),
    )
    solver_summary = _safe_dict(
        _safe_dict(proposal.get("current_snapshot")).get("nutrition_solver")
    )

    intent = resolve_proposal_intent(proposed_payload)
    simulation = _extract_simulation(validation_summary)
    if intent == "create_program" and simulation and simulation.get("program"):
        warnings = list(dict.fromkeys(
            str(issue.get("message")) for day in validation_summary.get("days", [])
            for issue in day.get("engine_validation", {}).get("issues", []) if issue.get("message")
        ))
        warnings.extend(validation_summary.get("warnings", []))
        specification = _safe_dict(proposal.get("targets")).get("program_specification", {})
        simulation = {**simulation, "program": {**simulation["program"], "warnings": warnings,
                      "nutrition_specification": specification,
                      "requirement_evidence": validation_summary.get("requirements", {})}}

    status = _safe_str(proposal.get("status"))
    intent_contract = get_proposal_intent_contract(intent)
    can_apply = can_apply_proposal(
        status=status,
        intent=intent,
        applied_at=proposal.get("applied_at"),
    )

    return ProposalReviewVM(
        proposal_id=proposal.get("id"),
        title=proposal.get("title", ""),
        summary=proposal.get("summary", ""),
        dailyplan_id=proposal.get("dailyplan_id"),
        dailyplan_name=proposal.get("dailyplan_name", ""),
        created_by_username=proposal.get("created_by_username"),
        reviewed_by_username=proposal.get("reviewed_by_username"),
        received_at_label=proposal.get("received_at_label", ""),
        is_read=bool(proposal.get("is_read")),
        status=ProposalReviewStatusVM(
            status=status,
            label=proposal_status_label(status),
            is_reviewable=bool(proposal.get("is_reviewable")),
            is_final=bool(proposal.get("is_final")),
            is_approved=status == "approved",
            is_applied=status == "applied",
        ),
        payload=ProposalReviewPayloadVM(
            intent=intent,
            entity_title=intent_contract.entity_title,
            attachments=_build_review_attachments(
                intent=intent,
                proposed_payload=proposed_payload,
                proposal=proposal,
            ),
            is_create_meal=intent_contract.is_create_meal,
            is_create_dailyplan=intent_contract.is_create_dailyplan,
            is_apply_supported=intent_contract.is_apply_supported,
            proposed_payload=proposed_payload,
            simulation=simulation,
            targets=_safe_dict(proposal.get("targets")),
            meal=_build_meal_review_vm(
                intent=intent,
                simulation=simulation,
                proposal_id=proposal.get("id"),
            ),
            dailyplan=_build_dailyplan_review_vm(
                intent=intent,
                simulation=simulation,
                proposal_id=proposal.get("id"),
            ),
            program=_build_program_review_vm(
                intent=intent,
                simulation=simulation,
                proposal_id=proposal.get("id"),
            ),
        ),
        can_apply=can_apply,
        subject_context_warning=_build_subject_context_warning_vm(proposal),
        applied_result=_build_applied_result_vm(
            proposal=proposal,
            intent=intent,
            status=status,
        ),
        iteration_trace=_build_iteration_trace_vm(proposal),
        alternatives=_build_solver_alternatives_vm(solver_summary),
        selected_alternative_id=_safe_str(solver_summary.get("selected_alternative_id")),
    )


def _build_solver_alternatives_vm(solver_summary: dict[str, Any]) -> list[dict[str, Any]]:
    alternatives = []
    for item in solver_summary.get("alternatives") or ():
        if not isinstance(item, dict) or not item.get("alternative_id"):
            continue
        quality = _safe_dict(item.get("quality"))
        result = _safe_dict(item.get("result"))
        totals = _safe_dict(result.get("daily_totals"))
        alternatives.append(
            {
                "alternative_id": _safe_str(item.get("alternative_id")),
                "label": _safe_str(item.get("label"), default="Alternativa"),
                "rank": item.get("rank"),
                "status": _safe_str(result.get("status")),
                "nutritional_score": quality.get("nutritional_score"),
                "functional_score": quality.get("functional_score"),
                "total_kcal": totals.get("kcal"),
                "protein": totals.get("protein"),
                "carbs": totals.get("carbs"),
                "fat": totals.get("fat"),
            }
        )
    return alternatives



def _build_subject_context_warning_vm(
    proposal: dict[str, Any],
) -> ProposalSubjectContextWarningVM:
    warning = build_proposal_subject_context_warning(proposal).as_dict()

    return ProposalSubjectContextWarningVM(
        requires_warning=bool(warning.get("requires_warning")),
        source=_safe_str(warning.get("source")),
        source_label=_safe_str(warning.get("source_label")),
        ppk_weight_source=_safe_str(warning.get("ppk_weight_source")),
        ppk_weight_source_label=_safe_str(warning.get("ppk_weight_source_label")),
        calculation_weight_kg=warning.get("calculation_weight_kg"),
        calculation_weight_label=_safe_str(warning.get("calculation_weight_label")),
        title=_safe_str(warning.get("title")),
        message=_safe_str(warning.get("message")),
    )

def _build_iteration_trace_vm(
    proposal: dict[str, Any],
) -> ProposalIterationTraceVM | None:
    trace = extract_plan_iteration_trace(proposal)
    if trace is None:
        return None

    previous_proposal_id = trace.previous_proposal_id

    return ProposalIterationTraceVM(
        previous_proposal_id=previous_proposal_id,
        previous_proposal_url=(
            reverse("proposal_detail", args=[previous_proposal_id])
            if previous_proposal_id
            else None
        ),
        user_message=trace.user_message,
        command_labels=trace.command_labels,
        command_count=trace.command_count,
        short_label=trace.short_label,
    )


def _build_review_attachments(
    *,
    intent: str | None,
    proposed_payload: dict[str, Any],
    proposal: dict[str, Any],
) -> list[dict[str, str]]:
    intent_contract = get_proposal_intent_contract(intent)
    if intent == "create_program":
        return [{"kind": "program", "label": "Programa semanal", "name": proposed_payload.get("program", {}).get("name", ""), "icon": "calendar-days"}]

    if intent == CREATE_MEAL_INTENT:
        meal = _safe_dict(proposed_payload.get("meal"))
        return [
            {
                "kind": intent_contract.attachment_kind,
                "label": intent_contract.attachment_label,
                "name": _safe_str(meal.get("name")) or proposal.get("title", ""),
                "icon": intent_contract.attachment_icon,
            },
        ]

    if intent == CREATE_DAILYPLAN_INTENT:
        dailyplan = _safe_dict(proposed_payload.get("dailyplan"))
        return [
            {
                "kind": intent_contract.attachment_kind,
                "label": intent_contract.attachment_label,
                "name": (
                    _safe_str(dailyplan.get("name"))
                    or proposal.get("dailyplan_name", "")
                    or proposal.get("title", "")
                ),
                "icon": intent_contract.attachment_icon,
            },
        ]

    if intent == AI_NUTRITION_BRIEF_INTENT:
        brief = _safe_dict(proposed_payload.get("nutrition_brief"))
        requested_entity = _safe_str(brief.get("requested_entity"), default="daily_plan")
        entity_label = "Programa semanal" if requested_entity == "program" else "Plan diario"
        return [
            {
                "kind": intent_contract.attachment_kind,
                "label": intent_contract.attachment_label,
                "name": f"Brief para {entity_label}",
                "icon": intent_contract.attachment_icon,
            },
        ]

    return [
        {
            "kind": "dailyplan",
            "label": "DailyPlan asociado",
            "name": proposal.get("dailyplan_name", "") or "Sin entidad asociada",
            "icon": "clipboard-list",
        },
    ]

def _build_applied_result_vm(
    *,
    proposal: dict[str, Any],
    intent: str | None,
    status: str,
) -> ProposalAppliedResultVM | None:
    if status != "applied":
        return None

    metadata = _extract_applied_metadata(proposal)
    if intent == "create_program":
        program_id = _safe_int_or_none(metadata.get("program_id"))
        return ProposalAppliedResultVM(kind="program", object_id=program_id,
            object_name=_safe_str(metadata.get("program_name")), detail_url_name="program_detail" if program_id else None)

    if intent == CREATE_MEAL_INTENT:
        meal_id = _safe_int_or_none(metadata.get("meal_id"))

        return ProposalAppliedResultVM(
            kind="meal",
            object_id=meal_id,
            object_name=_safe_str(metadata.get("meal_name")),
            detail_url_name="meal_detail" if meal_id else None,
        )

    if intent == CREATE_DAILYPLAN_INTENT:
        dailyplan_id = _safe_int_or_none(metadata.get("dailyplan_id"))

        return ProposalAppliedResultVM(
            kind="dailyplan",
            object_id=dailyplan_id,
            object_name=_safe_str(metadata.get("dailyplan_name")),
            detail_url_name="dailyplan_detail" if dailyplan_id else None,
        )

    return None


def _extract_applied_metadata(
    proposal: dict[str, Any],
) -> dict[str, Any]:
    audit_events = _safe_list(
        proposal.get("audit_events"),
    )

    for event in reversed(audit_events):
        if not isinstance(event, dict):
            continue

        if event.get("action") != "applied":
            continue

        return _safe_dict(event.get("metadata"))

    return {}


def _empty_program_totals() -> dict[str, Any]:
    return {
        "total_kcal": 0.0,
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0,
        "kcal_protein": 0.0,
        "kcal_carbs": 0.0,
        "kcal_fat": 0.0,
        "alloc": {"protein": 0.0, "carbs": 0.0, "fat": 0.0},
    }


def _finalize_program_totals(totals: dict[str, Any]) -> dict[str, Any]:
    totals["alloc"] = macro_kcal_distribution(
        totals["kcal_protein"],
        totals["kcal_carbs"],
        totals["kcal_fat"],
    )
    return totals


def _add_program_totals(total: dict[str, Any], snapshot: dict[str, Any]) -> None:
    for key in ("total_kcal", "protein", "carbs", "fat", "kcal_protein", "kcal_carbs", "kcal_fat"):
        total[key] += _safe_number(snapshot.get(key))


def _proposal_dailyplan_snapshot(dailyplan: dict[str, Any]) -> dict[str, Any]:
    kpis = _safe_dict(dailyplan.get("kpis"))
    protein = _safe_number(kpis.get("protein"))
    carbs = _safe_number(kpis.get("carbs"))
    fat = _safe_number(kpis.get("fat"))
    kcal_protein = protein * 4
    kcal_carbs = carbs * 4
    kcal_fat = fat * 9
    total_kcal = _safe_number(kpis.get("total_kcal")) or kcal_protein + kcal_carbs + kcal_fat
    explicit_alloc = {
        "protein": _safe_float_or_none(kpis.get("alloc_protein")),
        "carbs": _safe_float_or_none(kpis.get("alloc_carbs")),
        "fat": _safe_float_or_none(kpis.get("alloc_fat")),
    }
    fallback_alloc = macro_kcal_distribution(kcal_protein, kcal_carbs, kcal_fat)
    return {
        "total_kcal": total_kcal,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "kcal_protein": kcal_protein,
        "kcal_carbs": kcal_carbs,
        "kcal_fat": kcal_fat,
        "alloc": {
            key: explicit_alloc[key] if explicit_alloc[key] is not None else fallback_alloc[key]
            for key in ("protein", "carbs", "fat")
        },
    }


def _proposal_program_food_rows(
    days: list[dict[str, Any]],
    *,
    parent_totals: dict[str, Any],
    reference_weight: float | None,
    week_number: int,
) -> list[dict[str, Any]]:
    aggregated: dict[str, dict[str, Any]] = {}
    for day in days:
        dailyplan = _safe_dict(day.get("dailyplan"))
        for meal_item in _safe_list(dailyplan.get("meals")):
            meal = _safe_dict(_safe_dict(meal_item).get("meal"))
            for raw_food in _safe_list(meal.get("foods")):
                food = _safe_dict(raw_food)
                food_id = _safe_int_or_none(food.get("food_id"))
                name = _safe_str(food.get("food_name"), default="Alimento")
                unit = _safe_str(food.get("unit"), default="g")
                key = f"id:{food_id}" if food_id is not None else f"name:{name.casefold()}:{unit}"
                current = aggregated.setdefault(key, {
                    "food_id": food_id,
                    "name": name,
                    "unit": unit,
                    "quantity": 0.0,
                    "total_kcal": 0.0,
                    "protein": 0.0,
                    "carbs": 0.0,
                    "fat": 0.0,
                })
                current["quantity"] += _safe_number(food.get("quantity"))
                current["total_kcal"] += _safe_number(food.get("total_kcal"))
                current["protein"] += _safe_number(food.get("protein"))
                current["carbs"] += _safe_number(food.get("carbs"))
                current["fat"] += _safe_number(food.get("fat"))

    rows = []
    for index, food in enumerate(sorted(aggregated.values(), key=lambda item: (-item["quantity"], item["name"]))):
        kcal_protein = food["protein"] * 4
        kcal_carbs = food["carbs"] * 4
        kcal_fat = food["fat"] * 9
        total_kcal = food["total_kcal"] or kcal_protein + kcal_carbs + kcal_fat
        rows.append({
            "child": {"id": food["food_id"]},
            "rel": {
                "id": f"proposal-week-{week_number}-food-{index}",
                "quantity": food["quantity"],
                "quantity_unit": food["unit"],
                "name": food["name"],
                "total_kcal": total_kcal,
                "kcal_share": _percentage(total_kcal, parent_totals["total_kcal"]),
                "kcal_distribution": macro_kcal_distribution(kcal_protein, kcal_carbs, kcal_fat),
                "g_protein": food["protein"],
                "ppk": food["protein"] / reference_weight if reference_weight and food["protein"] else None,
                "g_carbs": food["carbs"],
                "g_fat": food["fat"],
                "alloc_protein": _percentage(kcal_protein, parent_totals["kcal_protein"]),
                "alloc_carbs": _percentage(kcal_carbs, parent_totals["kcal_carbs"]),
                "alloc_fat": _percentage(kcal_fat, parent_totals["kcal_fat"]),
            },
        })
    return rows


def _program_week_requirements(specification: dict[str, Any], week_number: int) -> list[dict[str, str]]:
    target = next(
        (_safe_dict(item) for item in _safe_list(specification.get("weeks")) if _safe_int_or_none(_safe_dict(item).get("week")) == week_number),
        {},
    )
    if not target:
        return []
    weight_basis = "proyectado" if specification.get("weight_basis") == "projected" else "medido"
    return [
        {"label": "Energía diaria", "value": f"{_safe_number(target.get('kcal')):.0f} kcal"},
        {"label": "Proteína diaria", "value": f"{_safe_number(target.get('protein_min_g')):.1f}–{_safe_number(target.get('protein_max_g')):.1f} g"},
        {"label": "Proteína por peso", "value": f"{_safe_number(specification.get('protein_min_ppk')):.1f}–{_safe_number(specification.get('protein_max_ppk')):.1f} g/kg"},
        {"label": "Grasa máxima", "value": f"{_safe_number(specification.get('fat_max_percent')):.0f}% de las calorías"},
        {"label": "Peso de referencia", "value": f"{_safe_number(target.get('reference_weight_kg')):.1f} kg · {weight_basis}"},
    ]


def _program_objective_groups(specification: dict[str, Any]) -> list[dict[str, Any]]:
    if not specification:
        return []

    weeks = [_safe_dict(item) for item in _safe_list(specification.get("weeks")) if isinstance(item, dict)]
    first_week = weeks[0] if weeks else {}
    last_week = weeks[-1] if weeks else {}
    duration_weeks = _safe_int_or_none(specification.get("duration_weeks")) or len(weeks)
    weight_basis = "Proyectado por semana" if specification.get("weight_basis") == "projected" else "Peso medido"

    planning = [
        {"label": "Duración", "value": f"{duration_weeks} semanas"},
        {"label": "Comidas diarias", "value": f"{_safe_number(specification.get('meals_per_day')):.0f}"},
    ]
    if first_week and last_week:
        planning.extend([
            {
                "label": "Energía diaria",
                "value": f"{_safe_number(first_week.get('kcal')):.0f} → {_safe_number(last_week.get('kcal')):.0f} kcal",
                "hint": "Desde la primera hasta la última semana",
            },
            {
                "label": "Peso de referencia",
                "value": f"{_safe_number(first_week.get('reference_weight_kg')):.1f} → {_safe_number(last_week.get('reference_weight_kg')):.1f} kg",
                "hint": weight_basis,
            },
        ])

    nutrition = [
        {
            "label": "Proteína",
            "value": f"{_safe_number(specification.get('protein_min_ppk')):.1f}–{_safe_number(specification.get('protein_max_ppk')):.1f} g/kg",
        },
        {"label": "Grasa máxima", "value": f"{_safe_number(specification.get('fat_max_percent')):.0f}% de las calorías"},
        {"label": "Verduras", "value": f"Mín. {_safe_number(specification.get('vegetable_min_g')):.0f} g/día"},
        {"label": "Frutas", "value": f"Mín. {_safe_number(specification.get('fruit_min_g')):.0f} g/día"},
    ]
    validation = [
        {"label": "Tolerancia calórica", "value": f"±{_safe_number(specification.get('calorie_tolerance_percent')):.0f}%"},
        {"label": "Tolerancia de macros", "value": f"±{_safe_number(specification.get('macro_tolerance_percent')):.0f}%"},
        {"label": "Variedad de verduras", "value": f"{_safe_number(specification.get('weekly_vegetable_species')):.0f} especies/semana"},
        {"label": "Variedad de frutas", "value": f"{_safe_number(specification.get('weekly_fruit_species')):.0f} especies/semana"},
    ]
    return [
        {"title": "Planificación", "icon": "calendar-range", "facts": planning},
        {"title": "Nutrición diaria", "icon": "activity", "facts": nutrition},
        {"title": "Criterios de validación", "icon": "badge-check", "facts": validation},
    ]


def _build_program_review_vm(
    *,
    intent: str | None,
    simulation: dict[str, Any] | None,
    proposal_id: int | None,
) -> dict[str, Any] | None:
    if intent != "create_program" or not isinstance(simulation, dict):
        return None
    program = _safe_dict(simulation.get("program"))
    if not program:
        return None

    duration_weeks = _safe_int_or_none(program.get("duration_weeks")) or 0
    source_days = [_safe_dict(day) for day in _safe_list(program.get("days")) if isinstance(day, dict)]
    slots = {
        (_safe_int_or_none(day.get("week_number")), _safe_int_or_none(day.get("day_number"))): day
        for day in source_days
    }
    specification = _safe_dict(program.get("nutrition_specification"))
    week_targets = {
        _safe_int_or_none(_safe_dict(item).get("week")): _safe_dict(item)
        for item in _safe_list(specification.get("weeks"))
        if isinstance(item, dict)
    }
    weeks = []
    previous_average_kcal = None
    unique_program_foods: set[str] = set()

    for week_number in range(1, duration_weeks + 1):
        target = week_targets.get(week_number, {})
        reference_weight = _safe_float_or_none(target.get("reference_weight_kg"))
        week_totals = _empty_program_totals()
        week_source_days = []
        days = []
        meals_count = 0

        for day_number in range(1, 8):
            source_day = slots.get((week_number, day_number), {})
            dailyplan = _safe_dict(source_day.get("dailyplan"))
            snapshot = _proposal_dailyplan_snapshot(dailyplan) if dailyplan else None
            card = None
            if dailyplan:
                meals = [
                    _build_dailyplan_meal_review_vm(_safe_dict(meal), proposal_id=proposal_id)
                    for meal in _safe_list(dailyplan.get("meals"))
                    if isinstance(meal, dict)
                ]
                kpis = _build_kpis_review_vm(_safe_dict(dailyplan.get("kpis")))
                card = _build_dailyplan_card_payload(
                    name=_safe_str(dailyplan.get("name")),
                    meals=meals,
                    kpis=kpis,
                    proposal_id=proposal_id,
                )
                card_id = f"proposal-program-{proposal_id or 'new'}-week-{week_number}-day-{day_number}"
                detail_url = reverse(
                    "proposal_program_dailyplan_detail",
                    args=[proposal_id, week_number, day_number],
                ) if proposal_id else ""
                card.update({
                    "id": card_id,
                    "main_id": card_id,
                    "actions": [{
                        "key": "open_proposed_dailyplan",
                        "label": "Explorar plan diario",
                        "icon": "arrow-right",
                        "url": detail_url,
                        "method": "get",
                        "desktop_position": "inline",
                        "mobile_position": "inline",
                    }] if detail_url else [],
                })
                meals_count += len(meals)
                _add_program_totals(week_totals, snapshot)
                week_source_days.append(source_day)
                for meal in _safe_list(dailyplan.get("meals")):
                    for food in _safe_list(_safe_dict(_safe_dict(meal).get("meal")).get("foods")):
                        food = _safe_dict(food)
                        identity = _safe_int_or_none(food.get("food_id"))
                        unique_program_foods.add(f"id:{identity}" if identity is not None else f"name:{_safe_str(food.get('food_name')).casefold()}:{_safe_str(food.get('unit'))}")
            days.append({
                "day_number": day_number,
                "day_label": FULL_DAY_LABELS[day_number][:3],
                "program_day": {"id": f"proposal-{week_number}-{day_number}"} if dailyplan else None,
                "dailyplan": {"id": None, "name": _safe_str(dailyplan.get("name"))} if dailyplan else None,
                "dailyplan_card": card,
                "dailyplan_detail": {
                    "name": _safe_str(dailyplan.get("name")),
                    "card": card,
                    "meals": [meal.as_dict() for meal in meals],
                } if dailyplan else None,
                "snapshot": snapshot,
                "reference_weight_kg": reference_weight,
            })

        _finalize_program_totals(week_totals)
        assigned_count = sum(1 for day in days if day["program_day"])
        average_kcal = week_totals["total_kcal"] / assigned_count if assigned_count else 0.0
        previous_ratio = (
            (average_kcal - previous_average_kcal) / previous_average_kcal * 100
            if previous_average_kcal is not None and previous_average_kcal > 0
            else None
        )
        previous_average_kcal = average_kcal
        food_rows = _proposal_program_food_rows(
            week_source_days,
            parent_totals=week_totals,
            reference_weight=reference_weight,
            week_number=week_number,
        )
        week = {
            "week_number": week_number,
            "days": days,
            "totals": week_totals,
            "assigned_dailyplans_count": assigned_count,
            "filled_days_count": assigned_count,
            "meals_count": meals_count,
            "foods_count": len(food_rows),
            "foods_aggregation_table": food_rows,
            "foods_panel_id": f"proposal-program-{proposal_id or 'new'}-week-{week_number}",
            "average_kcal_per_assigned_day": average_kcal,
            "average_ppk_per_assigned_day": (
                week_totals["protein"] / assigned_count / reference_weight
                if assigned_count and reference_weight
                else None
            ),
            "previous_week_average_ratio": previous_ratio,
            "reference_weight_kg": reference_weight,
            "requirement_facts": _program_week_requirements(specification, week_number),
        }
        week["chart"] = build_program_metric_chart(
            [week],
            title=f"Variación diaria · Semana {week_number}",
            subtitle="Detalle diario de calorías, macros, alloc y PPK de esta semana.",
            axis_mode="days",
        )
        week["kpi_ranges"] = build_week_kpi_ranges(week, current_weight=reference_weight)
        week["day_nutrition_rows"] = build_week_day_nutrition_rows(week, current_weight=reference_weight)
        weeks.append(week)

    return {
        **program,
        "name": _safe_str(program.get("name"), default="Programa propuesto"),
        "duration_weeks": duration_weeks,
        "weeks": weeks,
        "program_chart": build_program_metric_chart(weeks),
        "filled_days_count": sum(week["assigned_dailyplans_count"] for week in weeks),
        "program_foods_count": len(unique_program_foods),
        "objective_groups": _program_objective_groups(specification),
        "warnings": list(dict.fromkeys(_safe_str(warning) for warning in _safe_list(program.get("warnings")) if warning)),
    }


def _build_meal_review_vm(
    intent: str | None,
    simulation: dict[str, Any] | None,
    proposal_id: int | None,
) -> ProposalReviewMealVM | None:
    if intent != CREATE_MEAL_INTENT:
        return None

    if not isinstance(simulation, dict):
        return None

    meal = simulation.get("meal")

    if not isinstance(meal, dict):
        return None

    return _build_meal_from_simulation(
        meal,
        proposal_id=proposal_id,
    )


def _build_dailyplan_review_vm(
    intent: str | None,
    simulation: dict[str, Any] | None,
    proposal_id: int | None,
) -> ProposalReviewDailyPlanVM | None:
    if intent != CREATE_DAILYPLAN_INTENT:
        return None

    if not isinstance(simulation, dict):
        return None

    dailyplan = simulation.get("dailyplan")

    if not isinstance(dailyplan, dict):
        return None

    meals = [
        _build_dailyplan_meal_review_vm(
            meal_payload,
            proposal_id=proposal_id,
        )
        for meal_payload in _safe_list(dailyplan.get("meals"))
        if isinstance(meal_payload, dict)
    ]
    kpis = _build_kpis_review_vm(
        _safe_dict(dailyplan.get("kpis")),
    )

    return ProposalReviewDailyPlanVM(
        name=_safe_str(dailyplan.get("name")),
        meals=meals,
        kpis=kpis,
        card=_build_dailyplan_card_payload(
            name=_safe_str(dailyplan.get("name")),
            meals=meals,
            kpis=kpis,
            proposal_id=proposal_id,
        ),
    )


def _build_dailyplan_meal_review_vm(
    payload: dict[str, Any],
    proposal_id: int | None,
) -> ProposalReviewDailyPlanMealVM:
    return ProposalReviewDailyPlanMealVM(
        hour=_safe_optional_str(payload.get("hour")),
        note=_safe_str(payload.get("note")),
        meal=_build_meal_from_simulation(
            _safe_dict(payload.get("meal")),
            proposal_id=proposal_id,
        ),
    )


def _build_meal_from_simulation(
    meal: dict[str, Any],
    proposal_id: int | None,
) -> ProposalReviewMealVM:
    foods = [
        _build_food_review_vm(food)
        for food in _safe_list(meal.get("foods"))
        if isinstance(food, dict)
    ]
    kpis = _build_kpis_review_vm(
        _safe_dict(meal.get("kpis")),
    )

    return ProposalReviewMealVM(
        name=_safe_str(meal.get("name")),
        foods=foods,
        kpis=kpis,
        card=_build_meal_card_payload(
            name=_safe_str(meal.get("name")),
            foods=foods,
            kpis=kpis,
            proposal_id=proposal_id,
        ),
    )


def _build_food_review_vm(
    food: dict[str, Any],
) -> ProposalReviewFoodVM:
    return ProposalReviewFoodVM(
        food_id=_safe_int_or_none(food.get("food_id")),
        food_name=_safe_str(food.get("food_name")),
        quantity=_safe_float_or_none(food.get("quantity")),
        unit=_safe_str(food.get("unit"), default="g"),
        protein=_safe_float_or_none(food.get("protein")),
        carbs=_safe_float_or_none(food.get("carbs")),
        fat=_safe_float_or_none(food.get("fat")),
        total_kcal=_safe_float_or_none(food.get("total_kcal")),
    )


def _build_kpis_review_vm(
    kpis: dict[str, Any],
) -> ProposalReviewKpisVM | None:
    if not kpis:
        return None

    return ProposalReviewKpisVM(
        total_kcal=_safe_float_or_none(kpis.get("total_kcal")),
        protein=_safe_float_or_none(kpis.get("protein")),
        carbs=_safe_float_or_none(kpis.get("carbs")),
        fat=_safe_float_or_none(kpis.get("fat")),
        ppk=_safe_float_or_none(kpis.get("ppk")),
        alloc_protein=_safe_float_or_none(kpis.get("alloc_protein")),
        alloc_carbs=_safe_float_or_none(kpis.get("alloc_carbs")),
        alloc_fat=_safe_float_or_none(kpis.get("alloc_fat")),
    )


def _build_dailyplan_card_payload(
    *,
    name: str,
    meals: list[ProposalReviewDailyPlanMealVM],
    kpis: ProposalReviewKpisVM | None,
    proposal_id: int | None,
) -> dict[str, Any]:
    total_kcal = _kpi_total_kcal(kpis)

    return {
        "id": f"proposal-dailyplan-{proposal_id or 'new'}",
        "main_id": f"proposal-dailyplan-{proposal_id or 'new'}",
        "titulo": {
            "name": name,
            "label": "DailyPlan",
            "icon": "clipboard-list",
            "category_badge": None,
            "classes": [],
            "structural_indicators": {
                "meals_count": len(meals),
                "foods_count": sum(len(meal.meal.foods) for meal in meals),
            },
        },
        "kpis": _build_card_kpis(kpis),
        "menu": {
            "meals": [
                {
                    "meal_name": dailyplan_meal.meal.name,
                    "hour": dailyplan_meal.hour,
                    "foods": [
                        food.food_name
                        for food in dailyplan_meal.meal.foods
                    ],
                }
                for dailyplan_meal in meals
            ],
        },
        "table": {
            "items": [
                _build_meal_table_row(
                    dailyplan_meal.meal,
                    parent_total_kcal=total_kcal,
                    parent_kpis=kpis,
                )
                for dailyplan_meal in meals
            ],
        },
        "metadata": {
            "owner": "AI",
            "author": "AI",
            "fork_from": None,
        },
        "actions": _build_proposal_entity_actions(proposal_id),
    }


def _build_meal_card_payload(
    *,
    name: str,
    foods: list[ProposalReviewFoodVM],
    kpis: ProposalReviewKpisVM | None,
    proposal_id: int | None,
) -> dict[str, Any]:
    total_kcal = _kpi_total_kcal(kpis)

    return {
        "id": f"proposal-meal-{proposal_id or 'new'}",
        "main_id": f"proposal-meal-{proposal_id or 'new'}",
        "titulo": {
            "name": name,
            "label": "Meal",
            "icon": "utensils",
            "category_badge": None,
            "classes": [],
            "structural_indicators": {
                "foods_count": len(foods),
            },
        },
        "kpis": _build_card_kpis(kpis),
        "foods_aggregation": [
            {
                "display_name": food.food_name,
            }
            for food in foods
        ],
        "table": {
            "items": [
                _build_food_table_row(
                    food,
                    parent_total_kcal=total_kcal,
                    parent_kpis=kpis,
                )
                for food in foods
            ],
        },
        "metadata": {
            "owner": "AI",
            "author": "AI",
            "fork_from": None,
        },
        "actions": _build_proposal_entity_actions(proposal_id),
    }


def _build_proposal_entity_actions(proposal_id: int | None) -> list[dict[str, Any]]:
    if not proposal_id:
        return []

    return [
        {
            "key": "proposal_entity_detail",
            "label": "Ver entidad propuesta",
            "icon": "arrow-right",
            "url": f"/app/proposals/{proposal_id}/entity/",
            "method": "get",
            "desktop_position": "inline",
            "mobile_position": "inline",
        },
    ]


def _build_meal_table_row(
    meal: ProposalReviewMealVM,
    *,
    parent_total_kcal: float,
    parent_kpis: ProposalReviewKpisVM | None,
) -> dict[str, Any]:
    meal_total_kcal = _kpi_total_kcal(meal.kpis)
    protein = _kpi_value(meal.kpis, "protein")
    carbs = _kpi_value(meal.kpis, "carbs")
    fat = _kpi_value(meal.kpis, "fat")

    return {
        "rel": {
            "name": meal.name,
            "total_kcal": meal_total_kcal,
            "kcal_share": _percentage(meal_total_kcal, parent_total_kcal),
            "kcal_distribution": macro_kcal_distribution(
                protein * 4,
                carbs * 4,
                fat * 9,
            ),
            "g_protein": protein,
            "g_carbs": carbs,
            "g_fat": fat,
            "alloc_protein": _percentage(
                protein * 4,
                _kpi_value(parent_kpis, "protein") * 4,
            ),
            "alloc_carbs": _percentage(
                carbs * 4,
                _kpi_value(parent_kpis, "carbs") * 4,
            ),
            "alloc_fat": _percentage(
                fat * 9,
                _kpi_value(parent_kpis, "fat") * 9,
            ),
        },
    }


def _build_food_table_row(
    food: ProposalReviewFoodVM,
    *,
    parent_total_kcal: float,
    parent_kpis: ProposalReviewKpisVM | None,
) -> dict[str, Any]:
    total_kcal = _safe_number(food.total_kcal)
    protein = _safe_number(food.protein)
    carbs = _safe_number(food.carbs)
    fat = _safe_number(food.fat)

    return {
        "rel": {
            "name": food.food_name,
            "quantity": _safe_number(food.quantity),
            "quantity_unit": food.unit or "g",
            "total_kcal": total_kcal,
            "kcal_share": _percentage(total_kcal, parent_total_kcal),
            "kcal_distribution": macro_kcal_distribution(
                protein * 4,
                carbs * 4,
                fat * 9,
            ),
            "g_protein": protein,
            "g_carbs": carbs,
            "g_fat": fat,
            "alloc_protein": _percentage(
                protein * 4,
                _kpi_value(parent_kpis, "protein") * 4,
            ),
            "alloc_carbs": _percentage(
                carbs * 4,
                _kpi_value(parent_kpis, "carbs") * 4,
            ),
            "alloc_fat": _percentage(
                fat * 9,
                _kpi_value(parent_kpis, "fat") * 9,
            ),
        },
    }


def _build_card_kpis(
    kpis: ProposalReviewKpisVM | None,
) -> dict[str, Any]:
    protein = _kpi_value(kpis, "protein")
    carbs = _kpi_value(kpis, "carbs")
    fat = _kpi_value(kpis, "fat")

    return {
        "ppk": _kpi_value(kpis, "ppk"),
        "tot_kcal": _kpi_total_kcal(kpis),
        "g_protein": protein,
        "g_carbs": carbs,
        "g_fat": fat,
        "kcal_protein": protein * 4,
        "kcal_carbs": carbs * 4,
        "kcal_fat": fat * 9,
        "alloc_protein": _macro_alloc(kpis, "protein"),
        "alloc_carbs": _macro_alloc(kpis, "carbs"),
        "alloc_fat": _macro_alloc(kpis, "fat"),
    }


def _kpi_total_kcal(kpis: ProposalReviewKpisVM | None) -> float:
    if not kpis:
        return 0.0

    return _safe_number(kpis.total_kcal)


def _kpi_value(
    kpis: ProposalReviewKpisVM | None,
    key: str,
) -> float:
    if not kpis:
        return 0.0

    return _safe_number(getattr(kpis, key, None))


def _macro_alloc(
    kpis: ProposalReviewKpisVM | None,
    key: str,
) -> float:
    if not kpis:
        return 0.0

    explicit_value = getattr(kpis, f"alloc_{key}", None)

    if explicit_value is not None:
        return _safe_number(explicit_value)

    grams = _kpi_value(kpis, key)
    total_kcal = _kpi_total_kcal(kpis)
    kcal_factor = 9 if key == "fat" else 4

    return _percentage(grams * kcal_factor, total_kcal)


def _percentage(value: float, total: float) -> float:
    if not total:
        return 0.0

    return round((value / total) * 100, 2)


def _safe_number(value: Any) -> float:
    if isinstance(value, bool) or value is None:
        return 0.0

    if isinstance(value, int | float):
        return float(value)

    return 0.0


def _extract_simulation(
    validation_summary: dict[str, Any],
) -> dict[str, Any] | None:
    simulation = validation_summary.get("simulation")

    if isinstance(simulation, dict):
        return simulation

    return None


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value

    return []


def _safe_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value

    if value is None:
        return default

    return str(value)


def _safe_optional_str(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None

    return str(value)


def _safe_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    return None


def _safe_float_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int | float):
        return float(value)

    return None
