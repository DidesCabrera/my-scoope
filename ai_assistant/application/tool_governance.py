from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

TOOL_GOVERNANCE_VERSION = "ai_assistant_tool_governance.v1"
TOOL_SELECTION_REASON_ARGUMENT = "reason"


def system_tool_restraint_lines() -> tuple[str, ...]:
    return (
        "Usa tools solo ante intención operacional clara; ‘¿qué pasó?’, ‘¿y eso?’ o ‘¿por qué?’ no autorizan lecturas, cambios ni cards. Si hay más de un referente o acción plausible, aclara brevemente sin tools.",
        "Cada function call debe incluir reason: una justificación operacional breve, no una cadena de pensamiento.",
    )


def developer_tool_governance_policy() -> dict[str, Any]:
    return {
        "ambiguous": "clarify_without_tools",
        "reason_required": True,
    }


def add_provider_tool_selection_reason(provider_spec: Mapping[str, Any]) -> dict[str, Any]:
    """Attach a compact provider-only selection reason to one function schema."""

    spec = deepcopy(dict(provider_spec or {}))
    parameters = deepcopy(dict(spec.get("parameters") or {}))
    if parameters.get("type") != "object":
        return spec

    properties = deepcopy(dict(parameters.get("properties") or {}))
    properties[TOOL_SELECTION_REASON_ARGUMENT] = {"type": "string"}
    required = [str(item) for item in parameters.get("required") or ()]
    if TOOL_SELECTION_REASON_ARGUMENT not in required:
        required.append(TOOL_SELECTION_REASON_ARGUMENT)

    parameters["properties"] = properties
    parameters["required"] = required
    spec["parameters"] = parameters
    return spec


def extract_provider_tool_selection_reason(
    arguments: Mapping[str, Any],
    *,
    tool_name: str = "",
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """Remove and normalize the provider-only selection reason."""

    local_arguments = deepcopy(dict(arguments or {}))
    summary = _normalize_summary(local_arguments.pop(TOOL_SELECTION_REASON_ARGUMENT, ""))
    reason_code = _reason_code_for_tool(tool_name)
    metadata: dict[str, Any] = {
        "tool_governance_version": TOOL_GOVERNANCE_VERSION,
        "selection_reason_required": True,
        "selection_reason_valid": bool(summary),
        "selection_reason_code": reason_code,
        "selection_reason_summary": summary,
        "selection_reason_source": "provider_native_argument",
    }
    if not summary:
        metadata["selection_reason_error"] = "missing_tool_selection_reason"
        return local_arguments, "Provider-native tool selection reason was not reported.", metadata
    return local_arguments, summary, metadata


def tool_selection_reason_error(metadata: Mapping[str, Any]) -> str:
    """Return a stable BA03 block code for one native tool request, if any."""

    payload = dict(metadata or {})
    if payload.get("provider_transport") != "native_function_call.v1":
        return ""
    if payload.get("selection_reason_valid") is True:
        return ""
    return str(payload.get("selection_reason_error") or "missing_tool_selection_reason")


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
