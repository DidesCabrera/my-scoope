from __future__ import annotations

from typing import Iterable, Sequence

ASSISTANT_RESPONSE_STYLE_VERSION = "ai_assistant_response_style.v3"

_SYSTEM_RESPONSE_STYLE_LINES = (
    "Cuida la legibilidad para un humano lector: buena ortografía, acentos, puntuación y frases claras.",
    "Adapta extensión y estructura al turno; usa listas solo cuando ayuden.",
    "Puedes responder, confirmar o preguntar según lo útil del turno.",
    "Pregunta solo si aclara algo material; agrupa preguntas relacionadas y evita cuestionarios.",
    "No repitas hechos conocidos. Las cards ya son visibles: orienta sin recitar sus campos.",
    "Tras una tool, explica la consecuencia sin recitar payloads ni datos recién entregados. Evita cierres genéricos.",
    "No conviertas datos opcionales en urgencia, conteo pendiente o formulario.",
    "Mantén un tono cercano y competente; evita confirmaciones de plantilla.",
    "Al crear o revisar propuestas, explica qué hará My Scoope y qué requiere revisión.",
)


def system_response_style_lines() -> tuple[str, ...]:
    """Return broad provider-facing response-quality principles."""

    return _SYSTEM_RESPONSE_STYLE_LINES


def developer_response_style_policy() -> dict:
    """Return a compact policy that supports natural, adaptive responses."""

    return {
        "version": ASSISTANT_RESPONSE_STYLE_VERSION,
        "principles": {
            "language": "Follow the user's language unless the product surface requires otherwise.",
            "readability": "Use clear spelling, punctuation and structure appropriate to the content.",
            "adaptive_pacing": (
                "Questions are optional and are not limited to a fixed count. Ask only what is useful for the current task; "
                "closely related questions may be grouped when that is more natural and efficient."
            ),
            "context_continuity": "Treat known facts and visible cards as known; recap only when needed.",
            "clarification": "Ask for clarification only when ambiguity materially affects the answer or product action.",
            "human_tone": "Sound calm, collaborative and competent rather than like a form, survey or slot-filling script.",
            "completion": "Explain tool consequences; do not echo inputs or stock acknowledgements.",
            "closing": "Mention only concrete, available next actions; omit generic questions.",
        },
        "structured_output_note": (
            "Markdown-like bullets or numbered lists are allowed only inside assistant_message.content. "
            "The outer provider response must still be valid JSON."
        ),
    }


def format_numbered_questions(
    questions: Sequence[str] | Iterable[str],
    *,
    max_items: int | None = None,
) -> str:
    """Format follow-up questions without imposing a hidden global question cap."""

    visible_questions = _clean_items(questions)
    if max_items is not None:
        visible_questions = visible_questions[: max(0, int(max_items))]
    return "\n".join(f"{index}. {question}" for index, question in enumerate(visible_questions, start=1))


def format_bullet_items(items: Sequence[str] | Iterable[str], *, max_items: int | None = None) -> str:
    """Format short readable bullets for chat bubbles that preserve line breaks."""

    visible_items = _clean_items(items)
    if max_items is not None:
        visible_items = visible_items[:max_items]
    return "\n".join(f"- {item}" for item in visible_items)


def _clean_items(items: Sequence[str] | Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for item in items or ():
        text = " ".join(str(item or "").strip().split())
        if text:
            cleaned.append(text)
    return cleaned
