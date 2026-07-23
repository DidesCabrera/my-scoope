from collections.abc import Mapping
from typing import Any

from notas.application.ai_tools.runtime import run_ai_tool
from notas.application.ai_intake.dailyplan_generator import (
    generate_dailyplan_proposal_from_brief_proposal,
)
from notas.application.dto.proposal_iteration_trace import extract_plan_iteration_trace
from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    build_required_follow_up_questions,
    deserialize_brief,
    is_brief_ready_for_proposal,
    serialize_brief,
)
from notas.application.dto.nutrition_subject_context_dto import (
    SUBJECT_SOURCE_MANUAL_CHAT_DATA,
    SUBJECT_SOURCE_SELF_PROFILE,
)
from notas.application.ai_intake.plan_iteration import create_iterated_dailyplan_proposal
from notas.application.ai_intake.proposal_from_brief import create_nutrition_brief_proposal
from notas.application.proposals.solver_meal_proposals import (
    create_solver_generated_meal_proposal,
)
from notas.application.queries.proposal_queries import (
    get_proposal_detail,
    list_dailyplan_proposals,
    list_user_proposals,
    search_proposals,
)
from notas.application.services.commands.proposal_commands import (
    create_proportional_dailyplan_calorie_proposal,
    create_validated_dailyplan_build_proposal,
    create_validated_dailyplan_proposal,
    create_validated_meal_proposal,
)

from notas.domain.models import NutritionProposal


def _serialize_dto_list(items) -> list[dict]:
    return [
        item.as_dict()
        for item in items
    ]


def _ensure_payload_is_valid_for_tool(
    proposed_payload: dict | None,
) -> None:
    if proposed_payload is not None and not isinstance(proposed_payload, dict):
        raise ValueError("tool_proposed_payload_must_be_object")


def _ensure_targets_are_valid_for_tool(
    targets: dict,
) -> None:
    if not isinstance(targets, dict):
        raise ValueError("tool_targets_must_be_object")

    if not targets:
        raise ValueError("tool_targets_required")


def _ensure_tolerances_are_valid_for_tool(
    tolerances: dict | None,
) -> None:
    if tolerances is not None and not isinstance(tolerances, dict):
        raise ValueError("tool_tolerances_must_be_object")


def _ensure_title_is_valid_for_tool(
    title: str,
) -> None:
    if not isinstance(title, str):
        raise ValueError("tool_title_must_be_string")

    if not title.strip():
        raise ValueError("tool_title_required")


def _create_validated_dailyplan_proposal_data(
    user,
    dailyplan_id: int,
    title: str,
    targets: dict,
    proposed_payload: dict | None = None,
    tolerances: dict | None = None,
    summary: str = "",
) -> dict:
    _ensure_title_is_valid_for_tool(title)
    _ensure_targets_are_valid_for_tool(targets)
    _ensure_tolerances_are_valid_for_tool(tolerances)
    _ensure_payload_is_valid_for_tool(proposed_payload)

    result = create_validated_dailyplan_proposal(
        user=user,
        dailyplan_id=dailyplan_id,
        title=title,
        summary=summary,
        source=NutritionProposal.SOURCE_AI,
        targets=targets,
        tolerances=tolerances,
        proposed_payload=proposed_payload,
    )

    proposal = get_proposal_detail(
        user,
        result.proposal.id,
    ).as_dict()

    return {
        "proposal": proposal,
    }


def _create_validated_meal_proposal_data(
    user,
    dailyplan_id: int,
    title: str,
    proposed_payload: dict,
    targets: dict | None = None,
    summary: str = "",
) -> dict:
    _ensure_title_is_valid_for_tool(title)
    _ensure_payload_is_valid_for_tool(proposed_payload)

    result = create_validated_meal_proposal(
        user=user,
        dailyplan_id=dailyplan_id,
        title=title,
        summary=summary,
        source=NutritionProposal.SOURCE_AI,
        targets=targets or {},
        proposed_payload=proposed_payload,
    )

    proposal = get_proposal_detail(
        user,
        result.proposal.id,
    ).as_dict()

    return {
        "proposal": proposal,
    }


def _create_validated_dailyplan_build_proposal_data(
    user,
    dailyplan_id: int,
    title: str,
    proposed_payload: dict,
    targets: dict | None = None,
    summary: str = "",
) -> dict:
    _ensure_title_is_valid_for_tool(title)
    _ensure_payload_is_valid_for_tool(proposed_payload)

    result = create_validated_dailyplan_build_proposal(
        user=user,
        dailyplan_id=dailyplan_id,
        title=title,
        summary=summary,
        source=NutritionProposal.SOURCE_AI,
        targets=targets or {},
        proposed_payload=proposed_payload,
    )

    proposal = get_proposal_detail(
        user,
        result.proposal.id,
    ).as_dict()

    return {
        "proposal": proposal,
    }


def _ensure_nutrition_brief_payload_is_valid_for_tool(
    nutrition_brief: dict,
) -> NutritionBrief:
    if not isinstance(nutrition_brief, dict):
        raise ValueError("tool_nutrition_brief_must_be_object")

    brief = deserialize_brief(nutrition_brief)
    if brief is None:
        raise ValueError("tool_nutrition_brief_required")

    return brief


def _ensure_user_message_is_valid_for_tool(
    user_message: str,
) -> None:
    if not isinstance(user_message, str):
        raise ValueError("tool_user_message_must_be_string")

    if not user_message.strip():
        raise ValueError("tool_user_message_required")


def build_nutrition_brief_from_ai_drafts(
    *,
    profile_draft: Mapping[str, Any] | None = None,
    preference_draft: Mapping[str, Any] | None = None,
    proposal_preferences: Mapping[str, Any] | None = None,
    current_nutrition_brief: Mapping[str, Any] | None = None,
    raw_prompt: str = "",
) -> NutritionBrief:
    """Compose the proposal-ready NutritionBrief from AI Assistant draft objects.

    The LLM is the assistant that fills typed draft objects through tools. This
    function is the product boundary that converts those drafts into the legacy
    NutritionBrief contract consumed by the internal proposal engine. It does not
    persist profile or preference data.
    """

    current = deserialize_brief(dict(current_nutrition_brief or {})) if isinstance(current_nutrition_brief, Mapping) else None
    payload = serialize_brief(current) if current is not None else serialize_brief(NutritionBrief(raw_prompt=str(raw_prompt or "")))
    if raw_prompt:
        payload["raw_prompt"] = _join_text(payload.get("raw_prompt"), raw_prompt)

    profile = _as_mapping(profile_draft)
    preferences = _as_mapping(preference_draft)
    proposal = _as_mapping(proposal_preferences)

    profile_sources = _as_mapping(profile.get("field_sources"))
    proposal_sources = _as_mapping(proposal.get("field_sources"))
    preference_sources = _as_mapping(preferences.get("field_sources"))
    field_sources = dict(payload.get("field_sources") or {})

    for field_name in ("weight_kg", "height_cm", "age_years", "sex", "activity_level", "training_frequency"):
        if not _missing(profile.get(field_name)):
            payload[field_name] = profile.get(field_name)
            if field_name in {"weight_kg", "height_cm", "age_years", "sex", "activity_level"}:
                field_sources[field_name] = str(profile_sources.get(field_name) or "chat_draft")

    if not payload.get("subject_source") and _has_profile_body_data(profile):
        payload["subject_source"] = (
            SUBJECT_SOURCE_SELF_PROFILE
            if any(str(source) == "profile" for source in profile_sources.values())
            else SUBJECT_SOURCE_MANUAL_CHAT_DATA
        )

    for field_name in (
        "goal",
        "requested_entity",
        "meals_per_day",
        "energy_adjustment",
        "calorie_target",
        "protein_target",
        "carb_target",
        "fat_target",
    ):
        if not _missing(proposal.get(field_name)):
            payload[field_name] = proposal.get(field_name)

    if _missing(payload.get("meals_per_day")) and not _missing(preferences.get("preferred_meals_per_day")):
        payload["meals_per_day"] = preferences.get("preferred_meals_per_day")

    excluded_foods = _merge_text_lists(payload.get("excluded_foods"), preferences.get("avoided_foods"))
    excluded_foods = _merge_text_lists(excluded_foods, preferences.get("allergies_or_intolerances"))
    preferred_foods = _merge_text_lists(payload.get("preferred_foods"), preferences.get("preferred_foods"))
    payload["excluded_foods"] = excluded_foods
    payload["preferred_foods"] = preferred_foods

    if _missing(payload.get("budget_level")) and not _missing(preferences.get("budget_preference")):
        payload["budget_level"] = preferences.get("budget_preference")
    if _missing(payload.get("complexity_level")) and not _missing(preferences.get("simplicity_preference")):
        payload["complexity_level"] = "low" if _truthy_preference(preferences.get("simplicity_preference")) else payload.get("complexity_level")
    if _missing(payload.get("complexity_level")) and not _missing(preferences.get("variety_preference")):
        payload["complexity_level"] = "high" if _truthy_preference(preferences.get("variety_preference")) else payload.get("complexity_level")

    styles = list(payload.get("style_preferences") or [])
    if _truthy_preference(preferences.get("cooking_time_preference")) and "low_prep" not in styles:
        styles.append("low_prep")
    if _truthy_preference(preferences.get("simplicity_preference")) and "simple" not in styles:
        styles.append("simple")
    if _truthy_preference(preferences.get("budget_preference")) and "budget" not in styles:
        styles.append("budget")
    if _truthy_preference(preferences.get("variety_preference")) and "varied" not in styles:
        styles.append("varied")
    payload["style_preferences"] = styles

    notes = _merge_text_lists(payload.get("notes"), proposal.get("notes"))
    dietary_pattern = preferences.get("dietary_pattern")
    if not _missing(dietary_pattern):
        notes = _merge_text_lists(notes, [f"Patrón alimentario declarado: {dietary_pattern}"])
    payload["notes"] = notes

    if field_sources:
        payload["field_sources"] = field_sources

    brief = deserialize_brief(payload)
    if brief is None:  # pragma: no cover - defensive boundary
        raise ValueError("nutrition_brief_from_drafts_invalid")
    return brief


def _create_nutrition_engine_dailyplan_proposal_from_drafts_data(
    user,
    profile_draft: Mapping[str, Any],
    proposal_preferences: Mapping[str, Any],
    preference_draft: Mapping[str, Any] | None = None,
    current_nutrition_brief: Mapping[str, Any] | None = None,
    raw_prompt: str = "",
) -> dict:
    brief = build_nutrition_brief_from_ai_drafts(
        profile_draft=profile_draft,
        preference_draft=preference_draft,
        proposal_preferences=proposal_preferences,
        current_nutrition_brief=current_nutrition_brief,
        raw_prompt=raw_prompt,
    )
    if not is_brief_ready_for_proposal(brief):
        raise ValueError("nutrition_brief_has_pending_questions")

    response = _create_nutrition_engine_dailyplan_proposal_data(
        user=user,
        nutrition_brief=serialize_brief(brief),
    )
    response["nutrition_brief"] = serialize_brief(brief)
    response["draft_sources"] = {
        "profile_draft_used": True,
        "preference_draft_used": bool(preference_draft),
        "proposal_preferences_used": True,
        "persistent_profile_updated": False,
        "persistent_preferences_updated": False,
    }
    response["source_boundary"] = {
        "object": "proposal_from_ai_drafts",
        "writes_allowed": False,
        "applies_changes": False,
        "creates_reviewable_proposal": True,
        "requires_human_review": True,
    }
    return response


def create_nutrition_engine_dailyplan_proposal_from_drafts_tool(
    user,
    profile_draft: Mapping[str, Any],
    proposal_preferences: Mapping[str, Any],
    preference_draft: Mapping[str, Any] | None = None,
    current_nutrition_brief: Mapping[str, Any] | None = None,
    raw_prompt: str = "",
):
    return run_ai_tool(
        _create_nutrition_engine_dailyplan_proposal_from_drafts_data,
        user,
        profile_draft,
        proposal_preferences,
        preference_draft,
        current_nutrition_brief,
        raw_prompt,
        user=user,
    )


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return not bool(value)
    return False


def _has_profile_body_data(value: Mapping[str, Any]) -> bool:
    return any(not _missing(value.get(field_name)) for field_name in ("weight_kg", "height_cm", "age_years", "sex", "activity_level"))


def _merge_text_lists(*groups: Any) -> list[str]:
    merged: list[str] = []
    for group in groups:
        if _missing(group):
            continue
        values = group.replace(";", ",").split(",") if isinstance(group, str) else list(group)
        for item in values:
            text = " ".join(str(item or "").strip().split())
            if text and text not in merged:
                merged.append(text)
    return merged


def _truthy_preference(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = " ".join(str(value or "").strip().lower().split())
    return bool(text) and text not in {"false", "no", "none", "ninguno", "pendiente"}


def _join_text(*values: Any) -> str:
    return "\n".join(str(value or "").strip() for value in values if str(value or "").strip())


def _serialize_iteration_trace(proposal) -> dict | None:
    trace = extract_plan_iteration_trace(proposal)
    if trace is None:
        return None

    return trace.as_dict()


def _generated_dailyplan_response_payload(
    *,
    user,
    source_proposal,
    proposal,
    brief: NutritionBrief,
) -> dict:
    generated_proposal = get_proposal_detail(
        user,
        proposal.id,
    ).as_dict()
    source_proposal_data = get_proposal_detail(
        user,
        source_proposal.id,
    ).as_dict()
    validation_summary = generated_proposal.get("validation_summary") or {}

    return {
        "proposal": generated_proposal,
        "source_proposal": source_proposal_data,
        "nutrition_brief": serialize_brief(brief),
        "engine_validation": validation_summary.get("engine_validation") or {},
        "target_comparison": validation_summary.get("target_comparison") or {},
        "iteration_trace": _serialize_iteration_trace(proposal),
    }


def _create_nutrition_engine_dailyplan_proposal_data(
    user,
    nutrition_brief: dict,
) -> dict:
    brief = _ensure_nutrition_brief_payload_is_valid_for_tool(nutrition_brief)

    source_result = create_nutrition_brief_proposal(
        user=user,
        brief=brief,
        source=NutritionProposal.SOURCE_MCP,
    )
    generated_result = generate_dailyplan_proposal_from_brief_proposal(
        user=user,
        source_proposal=source_result.proposal,
        source=NutritionProposal.SOURCE_MCP,
    )

    return _generated_dailyplan_response_payload(
        user=user,
        source_proposal=source_result.proposal,
        proposal=generated_result.proposal,
        brief=brief,
    )


def create_nutrition_engine_dailyplan_proposal_tool(
    user,
    nutrition_brief: dict,
):
    return run_ai_tool(
        _create_nutrition_engine_dailyplan_proposal_data,
        user,
        nutrition_brief,
        user=user,
    )



def _create_nutrition_solver_meal_proposal_data(
    user,
    dailyplan_id: int,
    title: str,
    target: dict,
    search: str | None = None,
    limit: int = 40,
    include_extended: bool = True,
    meal_slot: str = "Solver meal",
    summary: str = "",
) -> dict:
    _ensure_title_is_valid_for_tool(title)
    _ensure_targets_are_valid_for_tool(target)

    result = create_solver_generated_meal_proposal(
        user=user,
        dailyplan_id=dailyplan_id,
        title=title,
        target=target,
        search=search,
        limit=limit,
        include_extended=include_extended,
        meal_slot=meal_slot,
        summary=summary,
        source=NutritionProposal.SOURCE_MCP,
    )

    proposal = get_proposal_detail(
        user,
        result.proposal.id,
    ).as_dict()

    return {
        "proposal": proposal,
        "nutrition_solver": {
            "candidate_count": result.candidate_count,
            "optimization_result": result.optimization_result.as_dict(),
            "applies_changes": False,
            "requires_human_review": True,
        },
    }


def create_nutrition_solver_meal_proposal_tool(
    user,
    dailyplan_id: int,
    title: str,
    target: dict,
    search: str | None = None,
    limit: int = 40,
    include_extended: bool = True,
    meal_slot: str = "Solver meal",
    summary: str = "",
):
    return run_ai_tool(
        _create_nutrition_solver_meal_proposal_data,
        user,
        dailyplan_id,
        title,
        target,
        search,
        limit,
        include_extended,
        meal_slot,
        summary,
        user=user,
    )

def _iterate_nutrition_engine_dailyplan_proposal_data(
    user,
    previous_proposal_id: int,
    nutrition_brief: dict,
    user_message: str,
) -> dict:
    brief = _ensure_nutrition_brief_payload_is_valid_for_tool(nutrition_brief)
    _ensure_user_message_is_valid_for_tool(user_message)

    previous_proposal = (
        NutritionProposal.objects
        .filter(created_by=user)
        .get(pk=previous_proposal_id)
    )
    iteration_result = create_iterated_dailyplan_proposal(
        user=user,
        brief=brief,
        previous_proposal=previous_proposal,
        user_message=user_message,
        source=NutritionProposal.SOURCE_MCP,
    )

    return _generated_dailyplan_response_payload(
        user=user,
        source_proposal=iteration_result.source_proposal,
        proposal=iteration_result.proposal,
        brief=brief,
    )


def iterate_nutrition_engine_dailyplan_proposal_tool(
    user,
    previous_proposal_id: int,
    nutrition_brief: dict,
    user_message: str,
):
    return run_ai_tool(
        _iterate_nutrition_engine_dailyplan_proposal_data,
        user,
        previous_proposal_id,
        nutrition_brief,
        user_message,
        user=user,
    )


def create_validated_meal_proposal_tool(
    user,
    dailyplan_id: int,
    title: str,
    proposed_payload: dict,
    targets: dict | None = None,
    summary: str = "",
):
    return run_ai_tool(
        _create_validated_meal_proposal_data,
        user,
        dailyplan_id,
        title,
        proposed_payload,
        targets,
        summary,
        user=user,
    )


def create_validated_dailyplan_build_proposal_tool(
    user,
    dailyplan_id: int,
    title: str,
    proposed_payload: dict,
    targets: dict | None = None,
    summary: str = "",
):
    return run_ai_tool(
        _create_validated_dailyplan_build_proposal_data,
        user,
        dailyplan_id,
        title,
        proposed_payload,
        targets,
        summary,
        user=user,
    )


def create_validated_dailyplan_proposal_tool(
    user,
    dailyplan_id: int,
    title: str,
    targets: dict,
    proposed_payload: dict | None = None,
    tolerances: dict | None = None,
    summary: str = "",
):
    return run_ai_tool(
        _create_validated_dailyplan_proposal_data,
        user,
        dailyplan_id,
        title,
        targets,
        proposed_payload,
        tolerances,
        summary,
        user=user,
    )


def _create_proportional_dailyplan_calorie_proposal_data(
    user,
    dailyplan_id: int,
    calorie_delta: float,
    title: str = "",
    summary: str = "",
) -> dict:
    result = create_proportional_dailyplan_calorie_proposal(
        user=user,
        dailyplan_id=dailyplan_id,
        calorie_delta=calorie_delta,
        title=title,
        summary=summary,
        source=NutritionProposal.SOURCE_AI,
    )
    return {
        "proposal": get_proposal_detail(user, result.proposal.id).as_dict(),
        "adjustment": {
            "dailyplan_id": dailyplan_id,
            "calorie_delta": float(calorie_delta),
            "preserve_foods": True,
            "requires_human_review": True,
        },
    }


def create_proportional_dailyplan_calorie_proposal_tool(
    user,
    dailyplan_id: int,
    calorie_delta: float,
    title: str = "",
    summary: str = "",
):
    return run_ai_tool(
        _create_proportional_dailyplan_calorie_proposal_data,
        user,
        dailyplan_id,
        calorie_delta,
        title,
        summary,
        user=user,
    )


def _list_user_proposals_data(user) -> dict:
    return {
        "proposals": _serialize_dto_list(
            list_user_proposals(user),
        ),
    }


def list_user_proposals_tool(user):
    return run_ai_tool(
        _list_user_proposals_data,
        user,
        user=user,
    )


def _list_dailyplan_proposals_data(user, dailyplan_id: int) -> dict:
    return {
        "dailyplan_id": dailyplan_id,
        "proposals": _serialize_dto_list(
            list_dailyplan_proposals(
                user,
                dailyplan_id,
            ),
        ),
    }


def list_dailyplan_proposals_tool(user, dailyplan_id: int):
    return run_ai_tool(
        _list_dailyplan_proposals_data,
        user,
        dailyplan_id,
        user=user,
    )


def _search_proposals_data(user, query: str) -> dict:
    return {
        "proposals": _serialize_dto_list(
            search_proposals(
                user,
                query,
            ),
        ),
        "query": query,
    }


def search_proposals_tool(user, query: str):
    return run_ai_tool(
        _search_proposals_data,
        user,
        query,
        user=user,
    )


def _read_proposal_data(user, proposal_id: int) -> dict:
    return {
        "proposal": get_proposal_detail(
            user,
            proposal_id,
        ).as_dict(),
    }


def read_proposal_tool(user, proposal_id: int):
    return run_ai_tool(
        _read_proposal_data,
        user,
        proposal_id,
        user=user,
    )
