"""Helpers for proposal warnings related to nutrition subject context.

A proposal can be calculated for a subject that is not the authenticated
user's personal nutrition profile. When that proposal is saved/applied into
the user's library, profile-dependent indicators such as PPK may be displayed
with the user's current profile weight instead of the calculation subject's
weight.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SELF_PROFILE_SOURCE = "self_profile"


@dataclass(frozen=True)
class ProposalSubjectContextWarning:
    """UI/server warning for proposals calculated with external subject data."""

    requires_warning: bool
    source: str
    ppk_weight_source: str
    calculation_weight_kg: float | None

    @property
    def is_external(self) -> bool:
        return self.requires_warning

    def as_dict(self) -> dict[str, Any]:
        return {
            "requires_warning": self.requires_warning,
            "source": self.source,
            "source_label": _subject_source_label(self.source),
            "ppk_weight_source": self.ppk_weight_source,
            "ppk_weight_source_label": _ppk_weight_source_label(self.ppk_weight_source),
            "calculation_weight_kg": self.calculation_weight_kg,
            "calculation_weight_label": _format_weight_label(self.calculation_weight_kg),
            "title": "Propuesta calculada con datos externos",
            "message": (
                "Esta propuesta fue calculada con datos distintos a tu ficha personal. "
                "Si la guardas en tu librería, My Scoope conservará las calorías y gramos "
                "de macros propuestos, pero los indicadores dependientes de tu perfil, "
                "como PPK, se mostrarán usando el peso registrado en tu ficha personal."
            ),
        }


def build_proposal_subject_context_warning(
    proposal: Any,
) -> ProposalSubjectContextWarning:
    """Extract warning metadata from a proposal model or serialized proposal dict."""

    subject_context = _extract_subject_context(proposal)
    source = _safe_str(subject_context.get("source"))
    ppk_weight_source = _safe_str(subject_context.get("ppk_weight_source"))
    calculation_weight_kg = _safe_float_or_none(
        subject_context.get("calculation_weight_kg")
    )

    explicit_warning = bool(subject_context.get("requires_library_ppk_warning"))
    external_source = bool(source and source != SELF_PROFILE_SOURCE)

    return ProposalSubjectContextWarning(
        requires_warning=explicit_warning or external_source,
        source=source,
        ppk_weight_source=ppk_weight_source,
        calculation_weight_kg=calculation_weight_kg,
    )


def proposal_requires_external_subject_ack(
    proposal: Any,
) -> bool:
    """Return True when applying this proposal should require explicit acknowledgement."""

    return build_proposal_subject_context_warning(proposal).requires_warning


def _extract_subject_context(proposal: Any) -> dict[str, Any]:
    targets = _safe_dict(_get_value(proposal, "targets"))
    current_snapshot = _safe_dict(_get_value(proposal, "current_snapshot"))
    validation_summary = _safe_dict(_get_value(proposal, "validation_summary"))

    candidates = [
        targets.get("subject_context"),
        current_snapshot.get("subject_context"),
        _safe_dict(validation_summary.get("generator")).get("subject_context"),
    ]

    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate

    return {}


def _get_value(proposal: Any, key: str) -> Any:
    if isinstance(proposal, dict):
        return proposal.get(key)

    return getattr(proposal, key, None)


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_float_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_weight_label(value: float | None) -> str:
    if value is None:
        return "Peso externo no especificado"

    if value.is_integer():
        return f"{int(value)} kg"

    return f"{value:.1f} kg"


def _subject_source_label(source: str) -> str:
    labels = {
        "self_profile": "Ficha personal",
        "external_chat_data": "Datos externos del chat",
        "manual_chat_data": "Datos temporales del chat",
    }
    return labels.get(source, "Contexto no especificado")


def _ppk_weight_source_label(source: str) -> str:
    labels = {
        "profile_current_weight": "Peso actual de la ficha personal",
        "external_subject_weight": "Peso externo usado para el cálculo",
        "manual_subject_weight": "Peso temporal usado para el cálculo",
        "unknown": "Peso no especificado",
    }
    return labels.get(source, "Peso no especificado")
