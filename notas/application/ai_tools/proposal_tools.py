from notas.application.ai_tools.runtime import run_ai_tool
from notas.application.ai_intake.dailyplan_generator import (
    generate_dailyplan_proposal_from_brief_proposal,
)
from notas.application.dto.proposal_iteration_trace import extract_plan_iteration_trace
from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    deserialize_brief,
    serialize_brief,
)
from notas.application.ai_intake.plan_iteration import create_iterated_dailyplan_proposal
from notas.application.ai_intake.proposal_from_brief import create_nutrition_brief_proposal
from notas.application.queries.proposal_queries import (
    get_proposal_detail,
    list_dailyplan_proposals,
    list_user_proposals,
    search_proposals,
)
from notas.application.services.commands.proposal_commands import (
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