from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

PERSONAL_RECORD_KINDS = ("body", "planning", "preferences", "metrics")


@dataclass(frozen=True)
class PersonalRecordRequest:
    kinds: tuple[str, ...] = ()
    ambiguous: bool = False


def parse_personal_record_request(value: str) -> PersonalRecordRequest | None:
    """Recognize explicit requests for the registered personal-record cards."""

    text = _normalize(value)
    if not text or not re.search(r"\b(?:muestra\w*|ensena\w*|ver|revisa\w*|dame|quiero|solicito)\b", text):
        return None

    if re.search(r"\b(?:todas?\s+(?:mis\s+)?fichas|mis\s+fichas(?:\s+personales)?|fichas\s+personales\s+completas?)\b", text):
        return PersonalRecordRequest(kinds=PERSONAL_RECORD_KINDS)

    requested: list[str] = []
    patterns = (
        ("body", r"\b(?:ficha\s+corporal|datos\s+corporales|base\s+de\s+calculo)\b"),
        ("planning", r"\b(?:objetivo\s+y\s+actividad|ficha\s+de\s+planificacion|contexto\s+de\s+planificacion)\b"),
        ("preferences", r"\b(?:preferencias\s+alimentarias|ficha\s+de\s+preferencias|ficha\s+alimentaria)\b"),
        ("metrics", r"\b(?:metricas\s+corporales|ficha\s+de\s+metricas|seguimiento\s+corporal|peso\s+actual)\b"),
    )
    for kind, pattern in patterns:
        if re.search(pattern, text):
            requested.append(kind)
    if requested:
        return PersonalRecordRequest(kinds=tuple(requested))

    if re.search(r"\b(?:mi\s+ficha|ficha\s+personal|una\s+ficha)\b", text):
        return PersonalRecordRequest(ambiguous=True)
    return None


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or "").lower())
    return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).split())


__all__ = ["PERSONAL_RECORD_KINDS", "PersonalRecordRequest", "parse_personal_record_request"]
