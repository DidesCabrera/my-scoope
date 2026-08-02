from __future__ import annotations

from typing import Any, Mapping

TOOL_GOVERNANCE_VERSION = "ai_assistant_tool_governance.v1"
TOOL_SELECTION_REASON_ARGUMENT = "reason"


def system_tool_restraint_lines() -> tuple[str, ...]:
    return (
        "Usa tools solo ante intención operacional clara; ‘¿qué pasó?’, ‘¿y eso?’ o ‘¿por qué?’ no autorizan lecturas, cambios ni cards. Si hay más de un referente o acción plausible, aclara brevemente sin tools.",
    )


def developer_tool_governance_policy() -> dict[str, Any]:
    return {
        "ambiguous": "clarify_without_tools",
        "reason_required": False,
    }


def add_provider_tool_selection_reason(provider_spec: Mapping[str, Any]) -> dict[str, Any]:
    """Return the provider schema unchanged.

    Selection reasoning is observable from the selected tool and its validated
    arguments. Requiring the model to repeat a synthetic ``reason`` argument
    made valid calls fail for reasons unrelated to the requested outcome.
    """

    return dict(provider_spec or {})


def extract_provider_tool_selection_reason(
    arguments: Mapping[str, Any],
    *,
    tool_name: str = "",
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """Remove and normalize the provider-only selection reason."""

    local_arguments = dict(arguments or {})
    supplied_summary = _normalize_summary(local_arguments.pop(TOOL_SELECTION_REASON_ARGUMENT, ""))
    reason_code = _reason_code_for_tool(tool_name)
    summary = supplied_summary or reason_code.replace("_", " ")
    metadata: dict[str, Any] = {
        "tool_governance_version": TOOL_GOVERNANCE_VERSION,
        "selection_reason_required": False,
        "selection_reason_valid": True,
        "selection_reason_code": reason_code,
        "selection_reason_summary": summary,
        "selection_reason_source": (
            "provider_native_argument" if supplied_summary else "tool_selection_inference"
        ),
    }
    return local_arguments, summary, metadata


def tool_selection_reason_error(metadata: Mapping[str, Any]) -> str:
    """Selection observability never blocks an otherwise valid tool call."""

    return ""


def safe_tool_selection_observability(metadata: Mapping[str, Any]) -> dict[str, str]:
    """Return bounded non-sensitive selection metadata for turn observability."""

    payload = dict(metadata or {})
    observed = {
        "reason_code": str(payload.get("selection_reason_code") or ""),
        "summary": _normalize_summary(payload.get("selection_reason_summary")),
        "status": "valid" if payload.get("selection_reason_valid") is True else "blocked",
    }
    error = str(payload.get("selection_reason_error") or "")
    if error:
        observed["error_code"] = error
    return {key: value for key, value in observed.items() if value}


def _reason_code_for_tool(tool_name: str) -> str:
    name = "_".join(str(tool_name or "").strip().lower().split())
    if name.startswith("share_"):
        return "explicit_card_request"
    if name.startswith("update_"):
        return "new_or_corrected_user_facts"
    if name.startswith("compare_"):
        return "explicit_validation_request"
    if name.startswith("create_") or name.startswith("iterate_"):
        return "explicit_proposal_request"
    if name.startswith("commit_"):
        return "explicit_commit_approval"
    if name.startswith(("read_", "list_", "search_", "preview_")):
        return "explicit_read_request"
    return "clear_operational_request"


def _normalize_summary(value: Any) -> str:
    return " ".join(str(value or "").split())[:180]
