from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Callable

from ai_assistant.application.product_ports import AIProductBindings
from ai_assistant.application.tools import (
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
    TOOL_UPDATE_PREFERENCE_DRAFT,
    TOOL_UPDATE_PROFILE_DRAFT,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
    AssistantToolCategory,
    get_tool_spec,
)
from ai_assistant.domain import AssistantToolResult, AssistantTurnRequest

ProviderToolSpecProvider = Callable[[], list[dict[str, Any]]]


_EXPANDED_PRODUCT_TOOL_DOMAINS = {
    "read_food": ("alimento", "food"),
    "read_meal": ("comida", "meal"),
    "list_user_foods": ("alimento", "food"),
    "list_user_meals": ("comida", "meal"),
    "search_user_meals": ("comida", "meal"),
    "list_user_dailyplans": ("plan", "dailyplan"),
    "search_user_dailyplans": ("plan", "dailyplan"),
    "list_user_programs": ("programa", "program", "semana"),
    "read_program": ("programa", "program", "semana"),
    "read_calendarization": ("calendario", "calendar", "pausar", "reanudar"),
    "list_inbox_items": ("inbox", "compartid", "recibid", "enviad"),
    "read_account_billing_context": (
        "cuenta",
        "crédito",
        "credito",
        "suscripción",
        "suscripcion",
        "pago",
        "billing",
        "plan comercial",
    ),
    "create_proportional_dailyplan_calorie_proposal": (
        "caloría",
        "caloria",
        "kcal",
        "cantidad",
        "manteniendo los mismos alimentos",
    ),
    "prepare_product_action": (
        "crear",
        "crea",
        "actualizar",
        "actualiza",
        "cambiar",
        "cambia",
        "renombr",
        "elimin",
        "borr",
        "paus",
        "reanud",
        "cancel",
        "aprobar",
        "aprueba",
        "rechaz",
        "aplicar",
        "aplica",
        "duplic",
    ),
}

_MEAL_PROPOSAL_TOOLS = {
    "create_validated_meal_proposal",
    "create_nutrition_solver_meal_proposal",
}
_DAILYPLAN_PROPOSAL_TOOLS = {
    "create_validated_dailyplan_proposal",
    "create_validated_dailyplan_build_proposal",
    "create_nutrition_engine_dailyplan_proposal",
    "create_nutrition_engine_dailyplan_proposal_from_drafts",
    "iterate_nutrition_engine_dailyplan_proposal",
}
_AI_NUTRITION_INTAKE_CORE_TOOLS = {
    TOOL_UPDATE_PROFILE_DRAFT,
    TOOL_UPDATE_PREFERENCE_DRAFT,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
}


def select_provider_tools(
    request: AssistantTurnRequest,
    *,
    available: Sequence[Mapping[str, Any]],
    enable_reviewable_proposal_tools: bool,
) -> tuple[Mapping[str, Any], ...]:
    """Select executable capabilities without inferring a conversational step."""

    available = tuple(available)
    user_text = str(request.user_message.content or "").strip().lower()
    if (
        str(request.context.get("surface") or "") == "ai_nutrition_intake"
        and not _requests_existing_product_operation(user_text)
    ):
        work_progress = _intake_work_progress(request.context)
        if (
            enable_reviewable_proposal_tools
            and _work_progress_has_active_proposal_objective(work_progress)
            and not tuple(work_progress.get("blocking_fields") or ())
        ):
            proposal_tool = provider_tool_by_name(
                available,
                TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
            )
            return (proposal_tool,) if proposal_tool is not None else ()

        return tuple(
            provider_spec
            for provider_spec in available
            if str(provider_spec.get("name") or "") in _AI_NUTRITION_INTAKE_CORE_TOOLS
            and (
                enable_reviewable_proposal_tools
                or str(provider_spec.get("name") or "")
                != TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS
            )
        )

    selected = []
    for provider_spec in available:
        name = str(provider_spec.get("name") or "")
        if not _expanded_product_tool_relevant(name, user_text=user_text):
            continue
        if not _reviewable_proposal_tool_relevant(name, user_text=user_text):
            continue
        if not enable_reviewable_proposal_tools:
            try:
                local_spec = get_tool_spec(name)
            except ValueError:
                local_spec = None
            if local_spec is not None and local_spec.category == AssistantToolCategory.PROPOSAL:
                continue
        selected.append(provider_spec)
    return tuple(selected)


def initial_tool_choice(
    request: AssistantTurnRequest,
    tools: Sequence[Mapping[str, Any]],
) -> str | None:
    if not tools:
        return None
    work_progress = _intake_work_progress(request.context)
    if (
        _work_progress_has_active_proposal_objective(work_progress)
        and not tuple(work_progress.get("blocking_fields") or ())
        and provider_tool_by_name(
            tools,
            TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
        )
        is not None
    ):
        return "required"
    return "auto"


def proposal_ready_after_tool_results(
    request: AssistantTurnRequest,
    tool_results: Sequence[AssistantToolResult],
    *,
    enable_reviewable_proposal_tools: bool,
    product_bindings: AIProductBindings,
) -> bool:
    work_progress = _intake_work_progress(request.context)
    if not _work_progress_has_active_proposal_objective(work_progress):
        return False
    if not enable_reviewable_proposal_tools:
        return False

    workspace = _intake_workspace(request.context)
    try:
        brief = product_bindings.build_nutrition_brief_from_ai_drafts(
            profile_draft=_latest_draft_for_tool(
                "profile_draft",
                context=request.context,
                prior_tool_results=tool_results,
            ),
            preference_draft=_latest_draft_for_tool(
                "preference_draft",
                context=request.context,
                prior_tool_results=tool_results,
            ),
            proposal_preferences=_latest_draft_for_tool(
                "proposal_preferences",
                context=request.context,
                prior_tool_results=tool_results,
            ),
            current_nutrition_brief=dict(workspace.get("current_nutrition_brief") or {}),
            raw_prompt=request.user_message.content,
        )
    except (TypeError, ValueError):
        return False
    return not product_bindings.required_proposal_fields(brief)


def provider_tool_by_name(
    tools: Sequence[Mapping[str, Any]],
    tool_name: str,
) -> Mapping[str, Any] | None:
    return next(
        (tool for tool in tuple(tools or ()) if str(tool.get("name") or "") == tool_name),
        None,
    )


def _expanded_product_tool_relevant(tool_name: str, *, user_text: str) -> bool:
    keywords = _EXPANDED_PRODUCT_TOOL_DOMAINS.get(tool_name)
    if keywords is None:
        return True
    if tool_name == "prepare_product_action" and (
        "propuesta" in user_text or "proposal" in user_text
    ):
        return False
    return any(keyword in user_text for keyword in keywords)


def _reviewable_proposal_tool_relevant(tool_name: str, *, user_text: str) -> bool:
    if tool_name == "create_validated_dailyplan_proposal" and not any(
        keyword in user_text
        for keyword in ("objetiv", "target", "ajust", "cantidad", "calor", "kcal")
    ):
        return False
    proposal_names = _MEAL_PROPOSAL_TOOLS | _DAILYPLAN_PROPOSAL_TOOLS
    if tool_name not in proposal_names:
        return True
    mentions_meal = any(keyword in user_text for keyword in ("meal", "comida"))
    mentions_plan = any(
        keyword in f" {user_text} "
        for keyword in ("dailyplan", "plan diario", " plan ")
    )
    if mentions_meal and not mentions_plan:
        return tool_name in _MEAL_PROPOSAL_TOOLS
    if mentions_plan and not mentions_meal:
        return tool_name in _DAILYPLAN_PROPOSAL_TOOLS
    return True


def _intake_workspace(context: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict((context or {}).get("metadata") or {})
    workspace = metadata.get("tool_oriented_intake")
    return dict(workspace) if isinstance(workspace, Mapping) else {}


def _intake_work_progress(context: Mapping[str, Any]) -> dict[str, Any]:
    progress = _intake_workspace(context).get("work_progress")
    return dict(progress) if isinstance(progress, Mapping) else {}


def _work_progress_has_active_proposal_objective(
    work_progress: Mapping[str, Any],
) -> bool:
    return str(work_progress.get("active_objective") or "") in {
        "create_reviewable_dailyplan_proposal",
        "create_dailyplan_proposal",
    }


def _requests_existing_product_operation(user_text: str) -> bool:
    text = f" {str(user_text or '').strip().lower()} "
    identifies_existing_object = any(
        marker in text
        for marker in (
            " mi plan ",
            " este plan ",
            " dailyplan ",
            " propuesta ",
            " programa ",
            " calendario ",
        )
    )
    requests_change_or_lookup = any(
        marker in text
        for marker in (
            " cambia ",
            " cambiar ",
            " ajusta ",
            " ajustar ",
            " aumenta ",
            " aumentar ",
            " reduce ",
            " reducir ",
            " renombra ",
            " elimina ",
            " borra ",
            " busca ",
            " muestra ",
            " revisa ",
            " compara ",
            " aplica ",
            " aprueba ",
            " rechaza ",
        )
    )
    return identifies_existing_object and requests_change_or_lookup


def _latest_draft_for_tool(
    draft_key: str,
    *,
    context: Mapping[str, Any],
    prior_tool_results: Sequence[AssistantToolResult],
) -> dict[str, Any]:
    metadata = dict((context or {}).get("metadata") or {})
    tool_oriented = dict(metadata.get("tool_oriented_intake") or {})
    current_drafts = dict(tool_oriented.get("current_drafts") or {})
    candidate = current_drafts.get(draft_key)
    draft = dict(candidate) if isinstance(candidate, Mapping) else {}
    for tool_result in tuple(prior_tool_results or ()):
        if not getattr(tool_result, "ok", False):
            continue
        candidate = dict(tool_result.data or {}).get(draft_key)
        if isinstance(candidate, Mapping) and candidate:
            draft = dict(candidate)
    return draft
