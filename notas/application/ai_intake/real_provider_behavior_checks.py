"""Pure behavioral evaluations used by the real-provider validation harness."""

from __future__ import annotations

import re

_VISIBLE_CLARIFICATION_PATTERN = re.compile(
    r"(?:\?|\b(?:dime|cuentame|aclara(?:me)?|especifica(?:me)?|"
    r"necesito que me digas|que estas viendo|que te preocupa|que quieres)\b)",
    re.IGNORECASE,
)


def evaluate_visible_facts(scenario, turns):
    failures = []
    turns_by_index = {turn.index: turn for turn in turns}
    for index, expected_fragments in scenario.expected_visible_fragments_by_turn.items():
        turn = turns_by_index.get(index)
        if turn is None:
            failures.append(f"turn {index}: missing")
            continue
        visible = turn.assistant_message.casefold()
        missing = [
            fragment
            for fragment in expected_fragments
            if fragment and fragment.casefold() not in visible
        ]
        if missing:
            failures.append(f"turn {index}: missing {missing}")
    detail = (
        f"{len(scenario.expected_visible_fragments_by_turn)} turn(s) matched persisted facts"
        if not failures
        else f"visible fact mismatch: {failures}"
    )
    return not failures, detail


def evaluate_behavioral_surface(scenario, turns):
    actual_tools = {name for turn in turns for name in turn.tool_names}
    forbidden_tools = sorted(set(scenario.forbidden_tool_names).intersection(actual_tools))
    visible_blob = "\n".join(turn.assistant_message.lower() for turn in turns)
    leaked_fragments = [
        fragment
        for fragment in scenario.forbidden_visible_fragments
        if fragment and fragment.lower() in visible_blob
    ]
    tool_call_count = sum(len(turn.tool_names) for turn in turns)
    too_many_tools = scenario.max_tool_calls is not None and tool_call_count > scenario.max_tool_calls
    details = []
    if forbidden_tools:
        details.append(f"forbidden tools executed: {', '.join(forbidden_tools)}")
    if leaked_fragments:
        details.append(f"forbidden visible fragments: {', '.join(leaked_fragments)}")
    if too_many_tools:
        details.append(f"tool calls {tool_call_count} exceeded maximum {scenario.max_tool_calls}")
    if not details:
        details.append("tool restraint and product-language boundary were respected")
    return not forbidden_tools and not leaked_fragments and not too_many_tools, "; ".join(details)


def evaluate_response_repetition(scenario, turns):
    limit = scenario.max_repeated_opening_count
    if limit is None:
        return True, "scenario does not define an opening repetition limit"
    openings = []
    for turn in turns:
        text = " ".join(str(turn.assistant_message or "").strip().split())
        if text:
            openings.append(text.split(".", 1)[0].strip().lower()[:80])
    counts = {opening: openings.count(opening) for opening in set(openings)}
    repeated = {opening: count for opening, count in counts.items() if count > limit}
    detail = (
        "assistant openings stayed within the configured repetition limit"
        if not repeated
        else "repeated openings: "
        + ", ".join(f"{opening!r} x{count}" for opening, count in sorted(repeated.items()))
    )
    return not repeated, detail


def evaluate_tool_result_grounding(turns):
    unavailable_markers = (
        "no tengo ejecución de herramientas",
        "no tengo herramientas disponibles",
        "no puedo ejecutar herramientas",
        "no puedo usar la herramienta",
        "no tengo acceso a herramientas",
    )
    failures = []
    for turn in turns:
        if not turn.tool_results:
            continue
        normalized = " ".join(turn.assistant_message.lower().split())
        if any(marker in normalized for marker in unavailable_markers):
            failures.append(f"turn {turn.index}: contradicted executed tool result")
    detail = (
        "assistant text remained grounded in available tool results"
        if not failures
        else f"tool grounding failures: {failures}"
    )
    return not failures, detail


def evaluate_expected_outcome(scenario, turns, *, state_before, state_after):
    """Verify that the trajectory reached the requested product outcome type."""

    expected = str(getattr(scenario, "expected_outcome", "response_only") or "response_only")
    successful_tools = {
        str(item.get("tool_name") or "")
        for turn in turns
        for item in turn.tool_results
        if str(item.get("status") or "") == "ok"
    }
    final_turn = turns[-1] if turns else None
    deltas = {
        key: int(state_after.get(key, 0) or 0) - int(state_before.get(key, 0) or 0)
        for key in set(state_before).union(state_after)
    }

    if expected == "nutrition_proposal":
        passed = deltas.get("nutrition_proposals", 0) > 0
        detail = "a reviewable nutrition proposal was created"
    elif expected == "prepared_patch":
        passed = deltas.get("prepared_actions", 0) > 0
        detail = "a prepared workspace patch was created"
    elif expected == "workspace_query":
        passed = any(
            name.startswith(("query_", "read_", "list_", "search_", "compare_"))
            for name in successful_tools
        )
        detail = "workspace information was read through a controlled capability"
    elif expected == "workspace_advanced":
        passed = any(
            name.startswith("update_") or name.startswith("share_")
            for name in successful_tools
        )
        detail = "the typed conversational workspace advanced"
    elif expected == "clarification_required":
        visible_question = bool(
            final_turn
            and _VISIBLE_CLARIFICATION_PATTERN.search(
                str(final_turn.assistant_message or "")
            )
        )
        semantic_missing = bool(final_turn and tuple(final_turn.semantic_missing_slots or ()))
        no_review_artifact = (
            deltas.get("nutrition_proposals", 0) <= 0
            and deltas.get("prepared_actions", 0) <= 0
        )
        passed = no_review_artifact and (visible_question or semantic_missing)
        detail = "the assistant requested clarification without creating a review artifact"
    else:
        passed = (
            deltas.get("nutrition_proposals", 0) <= 0
            and deltas.get("prepared_actions", 0) <= 0
        )
        detail = "the assistant responded without creating an unexpected review artifact"

    if passed:
        return True, detail
    return (
        False,
        f"expected outcome {expected!r} was not reached; "
        f"successful_tools={sorted(successful_tools)}, state_deltas={deltas}",
    )
