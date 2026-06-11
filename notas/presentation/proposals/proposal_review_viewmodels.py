from dataclasses import asdict, dataclass
from typing import Any


CREATE_MEAL_INTENT = "create_meal"
CREATE_DAILYPLAN_INTENT = "create_dailyplan"

APPLY_SUPPORTED_INTENTS = {
    CREATE_MEAL_INTENT,
    CREATE_DAILYPLAN_INTENT,
}


@dataclass(frozen=True)
class ProposalReviewStatusVM:
    status: str
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

    def as_dict(self) -> dict:
        return {
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
    status: ProposalReviewStatusVM
    payload: ProposalReviewPayloadVM
    can_apply: bool
    applied_result: ProposalAppliedResultVM | None

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
            "status": self.status.as_dict(),
            "payload": self.payload.as_dict(),
            "can_apply": self.can_apply,
            "applied_result": (
                self.applied_result.as_dict()
                if self.applied_result
                else None
            ),
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

    intent = _extract_intent(proposed_payload)
    simulation = _extract_simulation(validation_summary)

    status = _safe_str(proposal.get("status"))
    is_apply_supported = intent in APPLY_SUPPORTED_INTENTS
    can_apply = _can_apply_proposal(
        status=status,
        is_apply_supported=is_apply_supported,
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
        status=ProposalReviewStatusVM(
            status=status,
            is_reviewable=bool(proposal.get("is_reviewable")),
            is_final=bool(proposal.get("is_final")),
            is_approved=status == "approved",
            is_applied=status == "applied",
        ),
        payload=ProposalReviewPayloadVM(
            intent=intent,
            entity_title=_build_entity_title(intent),
            attachments=_build_review_attachments(
                intent=intent,
                proposed_payload=proposed_payload,
                proposal=proposal,
            ),
            is_create_meal=intent == CREATE_MEAL_INTENT,
            is_create_dailyplan=intent == CREATE_DAILYPLAN_INTENT,
            is_apply_supported=is_apply_supported,
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
        ),
        can_apply=can_apply,
        applied_result=_build_applied_result_vm(
            proposal=proposal,
            intent=intent,
            status=status,
        ),
    )



def _build_entity_title(intent: str | None) -> str:
    if intent == CREATE_MEAL_INTENT:
        return "Comida en la propuesta"

    if intent == CREATE_DAILYPLAN_INTENT:
        return "DailyPlan en la propuesta"

    return "Entidad en la propuesta"


def _build_review_attachments(
    *,
    intent: str | None,
    proposed_payload: dict[str, Any],
    proposal: dict[str, Any],
) -> list[dict[str, str]]:
    if intent == CREATE_MEAL_INTENT:
        meal = _safe_dict(proposed_payload.get("meal"))
        return [
            {
                "kind": "meal",
                "label": "Comida propuesta",
                "name": _safe_str(meal.get("name")) or proposal.get("title", ""),
                "icon": "utensils",
            },
        ]

    if intent == CREATE_DAILYPLAN_INTENT:
        dailyplan = _safe_dict(proposed_payload.get("dailyplan"))
        return [
            {
                "kind": "dailyplan",
                "label": "DailyPlan propuesto",
                "name": (
                    _safe_str(dailyplan.get("name"))
                    or proposal.get("dailyplan_name", "")
                    or proposal.get("title", "")
                ),
                "icon": "clipboard-list",
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

def _can_apply_proposal(
    *,
    status: str,
    is_apply_supported: bool,
    applied_at: Any,
) -> bool:
    return (
        status == "approved"
        and is_apply_supported
        and not applied_at
    )


def _build_applied_result_vm(
    *,
    proposal: dict[str, Any],
    intent: str | None,
    status: str,
) -> ProposalAppliedResultVM | None:
    if status != "applied":
        return None

    metadata = _extract_applied_metadata(proposal)

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
) -> dict[str, Any]:
    meal_total_kcal = _kpi_total_kcal(meal.kpis)

    return {
        "rel": {
            "name": meal.name,
            "total_kcal": meal_total_kcal,
            "kcal_share": _percentage(meal_total_kcal, parent_total_kcal),
            "g_protein": _kpi_value(meal.kpis, "protein"),
            "g_carbs": _kpi_value(meal.kpis, "carbs"),
            "g_fat": _kpi_value(meal.kpis, "fat"),
            "alloc_protein": _macro_alloc(meal.kpis, "protein"),
            "alloc_carbs": _macro_alloc(meal.kpis, "carbs"),
            "alloc_fat": _macro_alloc(meal.kpis, "fat"),
        },
    }


def _build_food_table_row(
    food: ProposalReviewFoodVM,
    *,
    parent_total_kcal: float,
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
            "g_protein": protein,
            "g_carbs": carbs,
            "g_fat": fat,
            "alloc_protein": _percentage(protein * 4, total_kcal),
            "alloc_carbs": _percentage(carbs * 4, total_kcal),
            "alloc_fat": _percentage(fat * 9, total_kcal),
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


def _extract_intent(
    proposed_payload: dict[str, Any],
) -> str | None:
    intent = proposed_payload.get("intent")

    if isinstance(intent, str) and intent.strip():
        return intent.strip()

    return None


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