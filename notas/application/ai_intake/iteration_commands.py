from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class PlanIterationCommand:
    """Structured, serializable command extracted from chat feedback.

    The command layer keeps plan iteration deterministic and audit-friendly:
    chat text is interpreted into a small contract before the generator creates
    a new NutritionProposal revision.
    """

    kind: str
    label: str
    payload: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "label": self.label,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class PlanIterationCommandSet:
    raw_message: str
    normalized_message: str
    commands: tuple[PlanIterationCommand, ...] = ()

    @property
    def has_commands(self) -> bool:
        return bool(self.commands)

    @property
    def labels(self) -> list[str]:
        return [command.label for command in self.commands]

    def as_dict(self) -> dict:
        return {
            "raw_message": self.raw_message,
            "normalized_message": self.normalized_message,
            "commands": [command.as_dict() for command in self.commands],
            "labels": self.labels,
        }


PROTEIN_UP_KEYWORDS = (
    "sube proteina",
    "subir proteina",
    "mas proteina",
    "más proteina",
    "alta en proteina",
    "alto en proteina",
)
PROTEIN_DOWN_KEYWORDS = (
    "baja proteina",
    "bajar proteina",
    "menos proteina",
)
CALORIES_DOWN_KEYWORDS = (
    "menos calorias",
    "menos calorías",
    "baja calorias",
    "baja calorías",
    "menos kcal",
    "baja kcal",
)
CALORIES_UP_KEYWORDS = (
    "mas calorias",
    "más calorías",
    "sube calorias",
    "sube calorías",
    "mas kcal",
    "más kcal",
    "sube kcal",
)
MEALS_DOWN_KEYWORDS = (
    "menos comidas",
    "menos comida",
    "menos meal",
    "menos meals",
)
MEALS_UP_KEYWORDS = (
    "mas comidas",
    "mas comida",
    "más comidas",
    "más comida",
    "agrega comida",
    "agregar comida",
)
SIMPLE_KEYWORDS = (
    "simple",
    "sencillo",
    "facil",
    "fácil",
    "pocas preparaciones",
    "poco tiempo",
)
BUDGET_KEYWORDS = (
    "barato",
    "economico",
    "económico",
    "presupuesto bajo",
    "bajo presupuesto",
)
VARIED_KEYWORDS = (
    "variado",
    "variedad",
    "mas variedad",
    "más variedad",
)

_MACRO_OR_STYLE_TERMS = {
    "caloria",
    "calorias",
    "kcal",
    "proteina",
    "protein",
    "carbohidrato",
    "carbohidratos",
    "carbs",
    "grasa",
    "grasas",
    "fat",
    "comida",
    "comidas",
    "meal",
    "meals",
    "simple",
    "sencillo",
    "facil",
    "barato",
    "economico",
    "variado",
    "variedad",
}

_REPLACEMENT_PATTERNS = (
    re.compile(
        r"\b(?:cambia|cambiar|reemplaza|reemplazar|sustituye|sustituir)\s+"
        r"(?P<source>.+?)\s+por\s+(?P<target>[^,.!?;]+)"
    ),
)
_EXCLUSION_PATTERNS = (
    re.compile(r"\b(?:sin|menos|quita|quitar|saca|sacar|elimina|eliminar)\s+(?P<term>[^,.!?;]+)"),
    re.compile(r"\bno\s+quiero\s+(?P<term>[^,.!?;]+)"),
)
_PREFERENCE_PATTERNS = (
    re.compile(r"\b(?:prefiero|preferir|agrega|agregar|incluye|incluir)\s+(?P<term>[^,.!?;]+)"),
    re.compile(r"\b(?:mas|más)\s+(?P<term>[^,.!?;]+)"),
)
_ARTICLES_RE = re.compile(r"^(?:el|la|los|las|un|una|unos|unas|de|del|al)\s+")
_TRAILING_RE = re.compile(
    r"\s+(?:porfa|por favor|please|en el plan|del plan|en la propuesta|de la propuesta|si se puede)$"
)
_COMMAND_BOUNDARY_RE = re.compile(
    r"\s+y\s+(?:prefiero|quiero|haz|hacerlo|que sea|sin|menos|mas|mas|agrega|incluye)\b"
)


def parse_dailyplan_iteration_commands(message: str) -> PlanIterationCommandSet:
    raw_message = " ".join(str(message or "").strip().split())
    normalized = normalize_text(raw_message)
    commands: list[PlanIterationCommand] = []

    commands.extend(_macro_commands(normalized))
    commands.extend(_meal_count_commands(normalized))
    commands.extend(_style_commands(normalized))
    commands.extend(_replacement_commands(normalized))
    commands.extend(_food_exclusion_commands(normalized))
    commands.extend(_food_preference_commands(normalized))

    return PlanIterationCommandSet(
        raw_message=raw_message,
        normalized_message=normalized,
        commands=tuple(_deduplicate_commands(commands)),
    )


def normalize_text(value: str) -> str:
    text = " ".join(str(value or "").strip().lower().split())
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )


def _macro_commands(normalized: str) -> list[PlanIterationCommand]:
    commands = []
    if _contains_any(normalized, PROTEIN_UP_KEYWORDS):
        commands.append(
            PlanIterationCommand(
                kind="increase_protein_target",
                label="Subir proteína objetivo",
                payload={"delta_g": 20},
            )
        )
    if _contains_any(normalized, PROTEIN_DOWN_KEYWORDS):
        commands.append(
            PlanIterationCommand(
                kind="decrease_protein_target",
                label="Bajar proteína objetivo",
                payload={"delta_g": -20},
            )
        )
    if _contains_any(normalized, CALORIES_DOWN_KEYWORDS):
        commands.append(
            PlanIterationCommand(
                kind="decrease_calorie_target",
                label="Bajar calorías objetivo",
                payload={"delta_kcal": -200},
            )
        )
    if _contains_any(normalized, CALORIES_UP_KEYWORDS):
        commands.append(
            PlanIterationCommand(
                kind="increase_calorie_target",
                label="Subir calorías objetivo",
                payload={"delta_kcal": 200},
            )
        )
    return commands


def _meal_count_commands(normalized: str) -> list[PlanIterationCommand]:
    commands = []
    if _contains_any(normalized, MEALS_DOWN_KEYWORDS):
        commands.append(
            PlanIterationCommand(
                kind="decrease_meals_per_day",
                label="Reducir cantidad de comidas",
                payload={"delta": -1},
            )
        )
    if _contains_any(normalized, MEALS_UP_KEYWORDS):
        commands.append(
            PlanIterationCommand(
                kind="increase_meals_per_day",
                label="Aumentar cantidad de comidas",
                payload={"delta": 1},
            )
        )
    return commands


def _style_commands(normalized: str) -> list[PlanIterationCommand]:
    commands = []
    if _contains_any(normalized, SIMPLE_KEYWORDS):
        commands.append(
            PlanIterationCommand(
                kind="set_simple_style",
                label="Hacer la propuesta más simple",
                payload={"style": "simple", "complexity_level": "low"},
            )
        )
    if _contains_any(normalized, BUDGET_KEYWORDS):
        commands.append(
            PlanIterationCommand(
                kind="set_budget_style",
                label="Priorizar una propuesta económica",
                payload={"style": "budget", "budget_level": "low"},
            )
        )
    if _contains_any(normalized, VARIED_KEYWORDS):
        commands.append(
            PlanIterationCommand(
                kind="set_varied_style",
                label="Aumentar variedad",
                payload={"style": "varied", "complexity_level": "high"},
            )
        )
    return commands


def _replacement_commands(normalized: str) -> list[PlanIterationCommand]:
    commands = []
    for pattern in _REPLACEMENT_PATTERNS:
        for match in pattern.finditer(normalized):
            source = _clean_food_term(match.group("source"))
            target = _clean_food_term(match.group("target"))
            if not source or not target or _is_non_food_term(source) or _is_non_food_term(target):
                continue
            commands.append(
                PlanIterationCommand(
                    kind="replace_food_preference",
                    label=f"Cambiar {source} por {target}",
                    payload={"exclude": source, "prefer": target},
                )
            )
    return commands


def _food_exclusion_commands(normalized: str) -> list[PlanIterationCommand]:
    commands = []
    replacement_sources = {
        str(command.payload.get("exclude"))
        for command in _replacement_commands(normalized)
        if command.payload.get("exclude")
    }
    for pattern in _EXCLUSION_PATTERNS:
        for match in pattern.finditer(normalized):
            for term in _split_food_terms(match.group("term")):
                term = _clean_food_term(term)
                if not term or term in replacement_sources or _is_non_food_term(term):
                    continue
                commands.append(
                    PlanIterationCommand(
                        kind="avoid_food",
                        label=f"Evitar {term}",
                        payload={"term": term},
                    )
                )
    return commands


def _food_preference_commands(normalized: str) -> list[PlanIterationCommand]:
    commands = []
    replacement_targets = {
        str(command.payload.get("prefer"))
        for command in _replacement_commands(normalized)
        if command.payload.get("prefer")
    }
    for pattern in _PREFERENCE_PATTERNS:
        for match in pattern.finditer(normalized):
            for term in _split_food_terms(match.group("term")):
                term = _clean_food_term(term)
                if not term or term in replacement_targets or _is_non_food_term(term):
                    continue
                commands.append(
                    PlanIterationCommand(
                        kind="prefer_food",
                        label=f"Preferir {term}",
                        payload={"term": term},
                    )
                )
    return commands


def _split_food_terms(value: str) -> list[str]:
    text = str(value or "")
    text = re.split(r"\s+(?:pero|aunque|porque|para)\s+", text, maxsplit=1)[0]
    return [piece for piece in re.split(r"\s+(?:ni|y|e|o)\s+", text) if piece.strip()]


def _clean_food_term(value: str) -> str:
    text = normalize_text(value)
    text = re.split(r"\s+por\s+", text, maxsplit=1)[0]
    text = _COMMAND_BOUNDARY_RE.split(text, maxsplit=1)[0]
    text = _TRAILING_RE.sub("", text).strip()
    while True:
        cleaned = _ARTICLES_RE.sub("", text).strip()
        if cleaned == text:
            break
        text = cleaned
    return text[:80].strip()


def _is_non_food_term(term: str) -> bool:
    normalized = normalize_text(term)
    if not normalized or len(normalized) < 2:
        return True
    if normalized in _MACRO_OR_STYLE_TERMS:
        return True
    words = normalized.split()
    return any(word in _MACRO_OR_STYLE_TERMS for word in words) and len(words) <= 3


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(keyword) in normalized for keyword in keywords)


def _deduplicate_commands(commands: Iterable[PlanIterationCommand]) -> list[PlanIterationCommand]:
    deduped = []
    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    for command in commands:
        payload_key = tuple(sorted((str(key), str(value)) for key, value in command.payload.items()))
        key = (command.kind, payload_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(command)
    return deduped
