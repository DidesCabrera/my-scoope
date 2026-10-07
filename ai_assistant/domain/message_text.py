from __future__ import annotations

from typing import Any


def normalize_visible_message_content(value: Any, *, max_chars: int | None = None) -> str:
    """Normalize chat text while preserving its Markdown block structure.

    Spaces within a line and repeated blank lines are bounded, but meaningful
    line boundaries survive every transport and persistence layer.
    """

    raw_text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.strip().split()) for line in raw_text.split("\n")]

    normalized_lines: list[str] = []
    previous_blank = False
    for line in lines:
        if not line:
            if normalized_lines and not previous_blank:
                normalized_lines.append("")
            previous_blank = True
            continue
        normalized_lines.append(line)
        previous_blank = False

    normalized = "\n".join(normalized_lines).strip()
    if max_chars is not None:
        return normalized[: max(0, int(max_chars))]
    return normalized
