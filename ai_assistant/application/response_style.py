from __future__ import annotations

from typing import Iterable, Sequence

ASSISTANT_RESPONSE_STYLE_VERSION = "ai_assistant_response_style.v2"

_SYSTEM_RESPONSE_STYLE_LINES = (
    "Cuida la legibilidad para un humano lector: buena ortografía, acentos, puntuación y frases claras.",
    "Adapta la extensión y la estructura de la respuesta a lo que el usuario acaba de pedir; usa párrafos, viñetas o números solo cuando ayuden.",
    "El ritmo de la conversación es flexible: puedes responder, confirmar, preguntar o combinar esas acciones según lo que resulte más útil en ese turno.",
    "Pregunta únicamente cuando una aclaración aporte valor real. Puedes agrupar preguntas estrechamente relacionadas si eso reduce fricción; evita convertir datos ausentes en un cuestionario mecánico.",
    "Usa el contexto ya conocido sin repetirlo innecesariamente y señala con claridad cualquier supuesto relevante.",
    "No cierres cada respuesta con una pregunta genérica cuando la solicitud ya quedó resuelta o existe una acción clara disponible.",
    "Evita frases de escasez artificial, urgencia o conteo de datos pendientes que hagan sentir al usuario dentro de un formulario.",
    "Mantén un tono cercano, colaborativo y competente, sin sacrificar precisión ni límites del producto.",
    "Si el usuario pide crear, modificar o revisar una propuesta, explica con naturalidad qué hará My Scoope y qué seguirá sujeto a revisión.",
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
            "context_continuity": "Use already known facts without mechanically recapping or requesting them again.",
            "clarification": "Ask for clarification only when ambiguity materially affects the answer or product action.",
            "human_tone": "Sound calm, collaborative and competent rather than like a form, survey or slot-filling script.",
            "completion": "Do not manufacture urgency or treat every absent optional field as a blocker.",
            "closing": "Do not add a generic closing question when the user's request is already resolved.",
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
