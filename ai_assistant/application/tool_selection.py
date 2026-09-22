from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any, Callable

from ai_assistant.application.intake_semantics import (
    extract_nutrition_intake_semantics,
    normalize_intake_text,
)
from ai_assistant.application.product_ports import AIProductBindings
from ai_assistant.application.tools import (
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS,
    TOOL_PROPOSE_WORKSPACE_PATCH,
    TOOL_QUERY_WORKSPACE,
    TOOL_READ_USER_PREFERENCE_CONTEXT,
    TOOL_READ_USER_PROFILE_CONTEXT,
    TOOL_SHARE_PREFERENCE_DRAFT_CARD,
    TOOL_SHARE_PROFILE_DRAFT_CARD,
    TOOL_SHARE_PROPOSAL_PREFERENCES_CARD,
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
    "read_calendarization": (
        "calendario",
        "calendar",
        "pausar",
        "reanudar",
        "programa activo",
        "programa en curso",
        "en curso",
    ),
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
    TOOL_PROPOSE_WORKSPACE_PATCH: (
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
_AI_NUTRITION_INTAKE_OPERATIONAL_TOOLS = {
    *_MEAL_PROPOSAL_TOOLS,
    *_DAILYPLAN_PROPOSAL_TOOLS,
    "create_proportional_dailyplan_calorie_proposal",
    "list_inbox_items",
    "read_account_billing_context",
    "preview_nutrition_solver_candidates",
    "compare_dailyplan_to_targets",
    TOOL_PROPOSE_WORKSPACE_PATCH,
}


def select_provider_tools(
    request: AssistantTurnRequest,
    *,
    available: Sequence[Mapping[str, Any]],
    enable_reviewable_proposal_tools: bool,
) -> tuple[Mapping[str, Any], ...]:
    """Select executable capabilities without inferring a conversational step."""

    available = tuple(available)
    user_text = _routing_text(request)
    if str(request.context.get("surface") or "") == "ai_nutrition_intake":
        return _select_intake_provider_tools(
            request,
            available=available,
            user_text=user_text,
            enable_reviewable_proposal_tools=enable_reviewable_proposal_tools,
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


def _select_intake_provider_tools(
    request: AssistantTurnRequest,
    *,
    available: Sequence[Mapping[str, Any]],
    user_text: str,
    enable_reviewable_proposal_tools: bool,
) -> tuple[Mapping[str, Any], ...]:
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

    # Keep a compact core and add only the capabilities required by the
    # structured active objective or an explicit semantic reference. This
    # leaves the model room to choose without paying for the full catalog.
    selected_names = set(_AI_NUTRITION_INTAKE_CORE_TOOLS)
    selected_names.update(_requested_intake_presentation_tools(user_text))
    selected_names.update(_requested_intake_memory_tools(user_text))
    active_work = dict(work_progress.get("active_work") or {})
    expected_outcome = str(active_work.get("expected_outcome") or "")
    resource = str(active_work.get("resource") or "")
    if expected_outcome == "workspace_query":
        selected_names.add(TOOL_QUERY_WORKSPACE)
        if resource == "profile":
            selected_names.add(TOOL_READ_USER_PROFILE_CONTEXT)
        elif resource == "preferences":
            selected_names.add(TOOL_READ_USER_PREFERENCE_CONTEXT)
    elif expected_outcome == "prepared_patch":
        selected_names.update({TOOL_QUERY_WORKSPACE, TOOL_PROPOSE_WORKSPACE_PATCH})
    if expected_outcome == "nutrition_proposal" and resource == "meal":
        selected_names.update(_MEAL_PROPOSAL_TOOLS)
    if _requests_existing_product_operation(user_text):
        selected_names.add(TOOL_QUERY_WORKSPACE)
        selected_names.update(
            str(provider_spec.get("name") or "")
            for provider_spec in available
            if str(provider_spec.get("name") or "")
            in _AI_NUTRITION_INTAKE_OPERATIONAL_TOOLS
            and _expanded_product_tool_relevant(
                str(provider_spec.get("name") or ""),
                user_text=user_text,
            )
            and _reviewable_proposal_tool_relevant(
                str(provider_spec.get("name") or ""),
                user_text=user_text,
            )
        )
    elif _requests_workspace_query(user_text):
        selected_names.add(TOOL_QUERY_WORKSPACE)
    return tuple(
        provider_spec
        for provider_spec in available
        if str(provider_spec.get("name") or "") in selected_names
        and (
            enable_reviewable_proposal_tools
            or str(provider_spec.get("name") or "")
            != TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL_FROM_DRAFTS
        )
    )


def _requested_intake_presentation_tools(user_text: str) -> set[str]:
    """Add optional card rendering only when the user explicitly asks to see it."""

    text = _normalized_intent_text(user_text)
    if not any(marker in text for marker in ("muestra", "revisa", "card", "tarjeta")):
        return set()
    selected: set[str] = set()
    if any(marker in text for marker in ("ficha", "perfil", "datos personales")):
        selected.add(TOOL_SHARE_PROFILE_DRAFT_CARD)
    if any(marker in text for marker in ("preferencia", "alimentacion", "alergia")):
        selected.add(TOOL_SHARE_PREFERENCE_DRAFT_CARD)
    if any(marker in text for marker in ("propuesta", "objetivo", "caloria", "macro")):
        selected.add(TOOL_SHARE_PROPOSAL_PREFERENCES_CARD)
    return selected


def _requested_intake_memory_tools(user_text: str) -> set[str]:
    """Expose persisted memory for explicit or indirect references to known context."""

    text = _normalized_intent_text(user_text)
    selected: set[str] = set()
    if any(marker in text for marker in ("ficha", "perfil", "mis datos", "sabes de mi")):
        selected.add(TOOL_READ_USER_PROFILE_CONTEXT)
    if any(
        marker in text
        for marker in ("preferencia", "alergia", "restriccion", "sabes de mi")
    ):
        selected.add(TOOL_READ_USER_PREFERENCE_CONTEXT)
    if "sabes de mi" in text and any(
        marker in text for marker in ("organiza", "organizado", "mejora")
    ):
        selected.add(TOOL_PROPOSE_WORKSPACE_PATCH)
    return selected


def _requests_workspace_query(user_text: str) -> bool:
    text = _normalized_intent_text(user_text)
    resource = re.search(
        r"\b(?:planes?|dailyplans?|propuestas?|programas?|calendarios?|"
        r"bibliotecas?|alimentos?|comidas?|foods?|meals?)\b",
        text,
    )
    query = "?" in str(user_text or "") or re.search(
        r"\b(?:que|cual(?:es)?|cuanto(?:s)?|lista\w*|muestra\w*|busca\w*|dime)\b",
        text,
    )
    return resource is not None and query is not None


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
    if _requests_existing_product_operation(_routing_text(request)):
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


def proposal_fact_capture_required_after_tool_results(
    request: AssistantTurnRequest,
    tool_results: Sequence[AssistantToolResult],
    *,
    enable_reviewable_proposal_tools: bool,
    product_bindings: AIProductBindings,
) -> bool:
    """Require capture when the user already supplied an exact blocking fact.

    This does not persist a heuristic interpretation. It only keeps the model's
    tool loop open so the model records the stated fact through the typed draft
    tool instead of claiming the requested proposal already exists.
    """

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
    stated = _explicit_proposal_values(request.user_message.content)
    for field_name, expected in stated.items():
        actual = getattr(brief, field_name, None)
        if not _brief_value_matches_explicit_value(
            brief,
            field_name=field_name,
            actual=actual,
            expected=expected,
        ):
            return True
    return False


def _brief_value_matches_explicit_value(
    brief: Any,
    *,
    field_name: str,
    actual: Any,
    expected: Any,
) -> bool:
    if field_name != "macro_distribution":
        return actual == expected

    actual_distribution = dict(actual or {})
    if not actual_distribution:
        calories = float(getattr(brief, "calorie_target", 0) or 0)
        protein = float(getattr(brief, "protein_target", 0) or 0)
        carbs = float(getattr(brief, "carb_target", 0) or 0)
        fat = float(getattr(brief, "fat_target", 0) or 0)
        if calories > 0 and protein > 0 and carbs > 0 and fat > 0:
            actual_distribution = {
                "protein": protein * 4 / calories * 100,
                "carbs": carbs * 4 / calories * 100,
                "fat": fat * 9 / calories * 100,
            }
    if set(actual_distribution) != {"protein", "carbs", "fat"}:
        return False
    return all(
        abs(float(actual_distribution[key]) - float(expected[key])) <= 0.25
        for key in ("protein", "carbs", "fat")
    )


def _explicit_proposal_values(user_text: str) -> dict[str, Any]:
    """Detect exact proposal values only to keep their typed capture pending."""

    values = {
        key: value
        for key, value in extract_nutrition_intake_semantics(user_text).as_updates().items()
        if key in {"goal", "meals_per_day", "complexity_level"}
    }
    text = normalize_intake_text(user_text)
    calorie_match = re.search(r"\b([1-6][0-9]{3})\s*(?:kcal|calorias?)\b", text)
    if calorie_match:
        values["calorie_target"] = int(calorie_match.group(1))

    label_patterns = {
        "protein": r"\b([0-9]{1,2}(?:[.,][0-9]+)?)\s*%?\s*(?:proteina|protein)\b",
        "carbs": r"\b([0-9]{1,2}(?:[.,][0-9]+)?)\s*%?\s*(?:carbohidratos?|carbos?|carbs?)\b",
        "fat": r"\b([0-9]{1,2}(?:[.,][0-9]+)?)\s*%?\s*(?:grasas?|fat)\b",
    }
    distribution: dict[str, float] = {}
    for key, pattern in label_patterns.items():
        match = re.search(pattern, text)
        if match:
            distribution[key] = float(match.group(1).replace(",", "."))
    slash_match = re.search(
        r"\b([0-9]{1,2})\s*/\s*([0-9]{1,2})\s*/\s*([0-9]{1,2})\b",
        text,
    )
    if slash_match and not distribution:
        distribution = {
            "protein": float(slash_match.group(1)),
            "carbs": float(slash_match.group(2)),
            "fat": float(slash_match.group(3)),
        }
    if set(distribution) == {"protein", "carbs", "fat"} and abs(
        sum(distribution.values()) - 100
    ) < 0.01:
        values["macro_distribution"] = distribution
    return values


def provider_tool_by_name(
    tools: Sequence[Mapping[str, Any]],
    tool_name: str,
) -> Mapping[str, Any] | None:
    return next(
        (tool for tool in tuple(tools or ()) if str(tool.get("name") or "") == tool_name),
        None,
    )


def _expanded_product_tool_relevant(tool_name: str, *, user_text: str) -> bool:
    if tool_name == "prepare_product_action":
        return False
    keywords = _EXPANDED_PRODUCT_TOOL_DOMAINS.get(tool_name)
    if keywords is None:
        return True
    if tool_name == TOOL_PROPOSE_WORKSPACE_PATCH and (
        "propuesta" in user_text or "proposal" in user_text
    ) and not any(
        marker in user_text
        for marker in ("aprobar", "aprueba", "rechaz", "aplicar", "aplica", "elimin", "borr")
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
    text = _normalized_intent_text(user_text)
    identifies_existing_object = re.search(
        r"\b(?:plan(?:es)?|dailyplans?|propuestas?|programas?|programs?|calendarios?|"
        r"bibliotecas?|librerias?|alimentos?|comidas?|foods?|meals?)\b",
        text,
    ) is not None
    requests_change_or_lookup = re.search(
        r"\b(?:cambi\w*|ajust\w*|aument\w*|reduc\w*|renombr\w*|elimin\w*|"
        r"borr\w*|busc\w*|muestr\w*|revis(?:a|ar|ame|alo|ala|en|emos|ando)|"
        r"compar\w*|aplic\w*|aprob\w*|"
        r"rechaz\w*|crea\w*|agreg\w*|anad\w*|registr\w*|incorpor\w*|guard\w*|"
        r"list\w*|nombr\w*|dime|decir\w*|tengo|hay|exist\w*|curso|activ\w*)\b",
        text,
    ) is not None
    return identifies_existing_object and requests_change_or_lookup


def _routing_text(request: AssistantTurnRequest) -> str:
    """Carry the last operational request across a short acknowledgement.

    Provider history remains the semantic authority. This helper only prevents
    tool availability from disappearing on replies such as ``sí, claro`` after
    the user already stated the actual operation.
    """

    current = str(request.user_message.content or "").strip().lower()
    if not _is_short_continuation(current):
        return current
    for message in reversed(tuple(request.history or ())):
        if message.role.value != "user":
            continue
        previous = str(message.content or "").strip().lower()
        if _requests_existing_product_operation(previous):
            return f"{previous} {current}".strip()
    return current


def _is_short_continuation(value: str) -> bool:
    normalized = _normalized_intent_text(value)
    if len(normalized.split()) > 6:
        return False
    return normalized in {
        "si",
        "si claro",
        "claro",
        "dale",
        "ok",
        "okay",
        "perfecto",
        "continua",
        "continuemos",
        "hazlo",
        "intentalo",
        "la primera",
        "la segunda",
        "la tercera",
    }


def _normalized_intent_text(value: str) -> str:
    """Normalize user phrasing before applying lightweight routing heuristics."""

    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


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
