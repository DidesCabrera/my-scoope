"""Semantic extraction helpers for nutrition intake.

The nutrition chat should not depend on literal form-like keywords. This module
keeps field meanings and common Spanish variants close to the AI Assistant app,
so the visible chat can stay human while the backend still persists reliable
state.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class IntakeSemanticExtraction:
    """Semantic facts detected in a free-form nutrition intake message."""

    subject_source: str | None = None
    goal: str | None = None
    meals_per_day: int | None = None
    training_frequency: int | None = None
    activity_level: str | None = None
    style_preferences: tuple[str, ...] = field(default_factory=tuple)
    complexity_level: str | None = None
    budget_level: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_updates(self) -> dict[str, object]:
        updates: dict[str, object] = {}
        for field_name in (
            "subject_source",
            "goal",
            "meals_per_day",
            "training_frequency",
            "activity_level",
            "complexity_level",
            "budget_level",
        ):
            value = getattr(self, field_name)
            if value is not None:
                updates[field_name] = value
        if self.style_preferences:
            updates["style_preferences"] = list(self.style_preferences)
        if self.notes:
            updates["notes"] = list(self.notes)
        return updates


GOAL_DEFINITIONS: dict[str, tuple[str, ...]] = {
    "fat_loss": (
        "bajar grasa",
        "perder grasa",
        "perdida de grasa",
        "quemar grasa",
        "reducir grasa",
        "disminuir grasa",
        "definir",
        "definicion",
        "bajar de peso",
        "perder peso",
        "adelgazar",
        "cut",
    ),
    "muscle_gain": (
        "ganar masa",
        "ganra masa",
        "ganra de masa",
        "ganra musculer",
        "ganar masa musculer",
        "gnarna masa",
        "gnarna de masa",
        "gnar masa",
        "garnar masa",
        "aumentar de masa",
        "aumentar masa",
        "aumentar mi masa",
        "aumentar de masa",
        "aumentar masa muscular",
        "subir masa",
        "masa muscular",
        "ganar musculo",
        "aumentar musculo",
        "subir musculo",
        "hipertrofia",
        "volumen",
        "bulk",
    ),
    "maintenance": (
        "mantencion",
        "mantener",
        "mantenimiento",
        "mantenerme",
        "conservar peso",
    ),
    "performance": (
        "rendimiento",
        "performance",
        "deporte",
        "mejorar marcas",
        "rendir mejor",
        "energia para entrenar",
    ),
    "healthy_eating": (
        "comer mejor",
        "alimentacion saludable",
        "ordenar mi alimentacion",
        "mejorar mi dieta",
    ),
}

SUBJECT_SELF_PROFILE_ALIASES = (
    "mi ficha",
    "mis datos",
    "datos de mi ficha",
    "usa mi perfil",
    "usar mi perfil",
    "usa mi ficha",
    "usar mi ficha",
    "usemos mi ficha",
    "usar mis datos",
    "usemos mis datos",
    "con mi ficha",
    "desde mi ficha",
    "para mi",
    "par mi",
    "para mí",
    "es para mi",
    "es par mi",
    "soy yo",
)

SUBJECT_EXTERNAL_ALIASES = (
    "otra persona",
    "alguien mas",
    "un cliente",
    "una clienta",
    "mi cliente",
    "mi clienta",
    "para el",
    "para ella",
    "mi hermano",
    "mi hermana",
    "mi amigo",
    "mi amiga",
)

STYLE_DEFINITIONS: dict[str, tuple[str, ...]] = {
    "simple": ("simple", "facil", "rapido", "sencillo", "practico", "sin complicarme"),
    "budget": ("barato", "economico", "presupuesto", "bajo costo", "ahorrar"),
    "varied": ("variado", "variedad", "no repetir", "distinto"),
    "low_prep": ("poco tiempo", "sin cocinar", "meal prep", "preparar rapido", "preparacion rapida"),
}

NUMBER_WORDS = {
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
}


def extract_nutrition_intake_semantics(
    message: str,
    *,
    subject_source_self_profile: str = "self_profile",
    subject_source_external_chat_data: str = "external_chat_data",
) -> IntakeSemanticExtraction:
    """Extract slot-like facts from natural Spanish intake messages.

    This helper is intentionally forgiving with accents, typos-adjacent wording
    and common user phrasing. It does not call an LLM; the LLM may still write
    the answer, but persistent state should not depend on the answer prose.
    """

    text = normalize_intake_text(message)
    notes: list[str] = []
    training_frequency = detect_training_frequency(text)
    activity_level = detect_activity_level(text, training_frequency=training_frequency)
    training_note = detect_training_note(text)
    if training_note:
        notes.append(training_note)

    return IntakeSemanticExtraction(
        subject_source=detect_subject_source(
            text,
            self_profile_value=subject_source_self_profile,
            external_value=subject_source_external_chat_data,
        ),
        goal=detect_goal(text),
        meals_per_day=detect_meals_per_day(text),
        training_frequency=training_frequency,
        activity_level=activity_level,
        style_preferences=tuple(detect_styles(text)),
        complexity_level=detect_complexity(text),
        budget_level=detect_budget(text),
        notes=tuple(notes),
    )


def normalize_intake_text(value: str) -> str:
    text = " ".join(str(value or "").strip().lower().split())
    text = "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )
    return text


def detect_goal(text: str) -> str | None:
    if "grasa" in text and contains_any(text, GOAL_DEFINITIONS["fat_loss"]):
        return "fat_loss"
    if "masa" in text and contains_any(text, GOAL_DEFINITIONS["muscle_gain"]):
        return "muscle_gain"
    for goal, aliases in GOAL_DEFINITIONS.items():
        if contains_any(text, aliases):
            return goal
    return None


def detect_subject_source(text: str, *, self_profile_value: str, external_value: str) -> str | None:
    if contains_any(text, SUBJECT_SELF_PROFILE_ALIASES):
        return self_profile_value
    if contains_any(text, SUBJECT_EXTERNAL_ALIASES):
        return external_value
    return None


def detect_meals_per_day(text: str) -> int | None:
    patterns = (
        r"\b([1-8])\s*(?:comidas|comida)\b",
        r"\b(?:comidas|comida)\D{0,18}([1-8])\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            if len(match.groups()) >= 2 and match.group(2):
                return int(match.group(2))
            return int(match.group(1))

    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\s*(?:comidas|comida)\b", text):
            return value
    return None


def detect_training_frequency(text: str) -> int | None:
    activity_words = r"(?:entreno|entrenar|entrenamiento|ejercicio|actividad|gym|gimnasio|pesas|fuerza|cardio|deporte)"
    patterns = (
        rf"\b([1-7])\s*(?:a|-|o)\s*([1-7])\s*(?:veces|dias|dia|x)\D{{0,24}}{activity_words}\b",
        rf"\b([1-7])\s*(?:veces|dias|dia|x)\D{{0,24}}{activity_words}\b",
        rf"\b([1-7])\s*(?:veces|dias|dia|x)\D{{0,24}}(?:semana|semanal)\b",
        rf"\b([1-7])\s*x\s*(?:semana|semanal)\b",
        rf"\b{activity_words}\D{{0,18}}([1-7])\s*(?:veces|dias|dia|x)(?!\s*(?:comidas|comida))\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            if len(match.groups()) >= 2 and match.group(2):
                return int(match.group(2))
            return int(match.group(1))

    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{activity_words}\D{{0,24}}{word}\s*(?:veces|dias|dia)\b", text):
            return value
        if re.search(rf"\b{word}\s*(?:veces|dias|dia)\D{{0,24}}{activity_words}\b", text):
            return value
    return None


def detect_activity_level(text: str, *, training_frequency: int | None = None) -> str | None:
    if contains_any(text, ("sedentario", "sedentaria", "actividad baja", "poco activo", "poco activa")):
        return "sedentary"
    if contains_any(text, ("actividad ligera", "ligera", "camino", "activo leve")):
        return "light"
    if contains_any(text, ("actividad moderada", "moderada", "moderado")):
        return "moderate"
    if contains_any(text, (
        "actividad alta",
        "alta intensidad",
        "intensidad",
        "intesidad",
        "intenso",
        "intensa",
        "intensamente",
        "intesamente",
        "fuerte",
        "muy activo",
        "muy activa",
    )):
        return "high"
    if contains_any(text, ("actividad muy alta", "muy alta", "doble turno", "todos los dias", "todos los días")):
        return "very_high"

    if training_frequency is None:
        return None
    if training_frequency <= 1:
        return "light"
    if training_frequency <= 3:
        return "moderate"
    if training_frequency <= 5:
        return "high"
    return "very_high"


def detect_training_note(text: str) -> str | None:
    fragments: list[str] = []
    if contains_any(text, ("fuerza", "pesas", "hipertrofia")):
        fragments.append("fuerza")
    if contains_any(text, ("cardio", "correr", "running", "bicicleta")):
        fragments.append("cardio")
    if contains_any(text, ("alta intensidad", "intensidad", "intesidad", "intenso", "intensa", "intensamente", "intesamente", "fuerte")):
        fragments.append("alta intensidad")
    if not fragments:
        return None
    return "Entrenamiento mencionado: " + ", ".join(dict.fromkeys(fragments)) + "."


def detect_styles(text: str) -> list[str]:
    styles: list[str] = []
    for style, aliases in STYLE_DEFINITIONS.items():
        if contains_any(text, aliases):
            styles.append(style)
    return styles


def detect_complexity(text: str) -> str | None:
    if contains_any(text, ("simple", "facil", "pocas cosas", "pocos alimentos", "sencillo")):
        return "low"
    if contains_any(text, ("variado", "variedad", "no repetir")):
        return "high"
    return None


def detect_budget(text: str) -> str | None:
    if contains_any(text, ("barato", "economico", "bajo presupuesto", "bajo costo")):
        return "low"
    return None


def contains_any(text: str, aliases: Iterable[str]) -> bool:
    return any(normalize_intake_text(alias) in text for alias in aliases)
