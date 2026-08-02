from __future__ import annotations

import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe


register = template.Library()

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_CODE_RE = re.compile(r"`([^`\n]+)`")
_UNORDERED_RE = re.compile(r"^\s*[-*]\s+(.+)$")
_ORDERED_RE = re.compile(r"^\s*\d+[.)]\s+(.+)$")


def _inline_markup(value: str) -> str:
    safe = str(escape(value))
    safe = _BOLD_RE.sub(r"<strong>\1</strong>", safe)
    return _CODE_RE.sub(r"<code>\1</code>", safe)


@register.filter(is_safe=True)
def assistant_text(value: object) -> str:
    """Render a safe, deliberately small Markdown subset for chat bubbles."""

    lines = str(value or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    rendered: list[str] = []
    list_kind = ""

    def close_list() -> None:
        nonlocal list_kind
        if list_kind:
            rendered.append(f"</{list_kind}>")
            list_kind = ""

    for line in lines:
        unordered = _UNORDERED_RE.match(line)
        ordered = _ORDERED_RE.match(line)
        if unordered or ordered:
            wanted_kind = "ul" if unordered else "ol"
            if list_kind != wanted_kind:
                close_list()
                rendered.append(f"<{wanted_kind}>")
                list_kind = wanted_kind
            match = unordered or ordered
            rendered.append(f"<li>{_inline_markup(match.group(1))}</li>")
            continue

        close_list()
        if line.strip():
            rendered.append(f"<p>{_inline_markup(line.strip())}</p>")

    close_list()
    return mark_safe("".join(rendered))
