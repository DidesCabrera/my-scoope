"""Pure behavioral evaluations used by the real-provider validation harness."""

from __future__ import annotations


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
