"""Keep weekly constraints out of the legacy scalar/notes-only program path."""

import re
import unicodedata
from collections.abc import Mapping


def requires_weekly_specification(request):
    workspace = (request.context.get("metadata") or {}).get("tool_oriented_intake") or {}
    progress = workspace.get("work_progress") or {}
    active = progress.get("active_work") or {}
    if active.get("expected_outcome") != "nutrition_proposal":
        return False
    text = unicodedata.normalize("NFKD", request.user_message.content.lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    is_program = active.get("resource") == "program" or bool(re.search(r"\bprograma\b", text))
    # This only selects a typed contract; the model still extracts the values.
    markers = ("program_specification", "peso proyectado",
               "progresiv", "g/kg", "ppk", "grasa nunca", "limite de grasa")
    weekly_limits = re.search(r"(?:calori\w*|kcal|frutas?|verduras?|familia).{0,45}(?:por|cada) semana", text)
    return is_program and (any(marker in text for marker in markers) or bool(weekly_limits))


def weekly_specification_missing(request, results):
    """Missing also includes a captured reference contradicting an explicit directive."""
    if not requires_weekly_specification(request):
        return False
    for result in reversed(tuple(results)):
        if result.ok and result.tool_name == "update_proposal_preferences":
            draft = (result.data or {}).get("proposal_preferences") or {}
            return _specification_needs_capture(request, draft.get("program_specification"))
    workspace = (request.context.get("metadata") or {}).get("tool_oriented_intake") or {}
    drafts = workspace.get("current_drafts") or {}
    return _specification_needs_capture(request, (drafts.get("proposal_preferences") or {}).get("program_specification"))


def explicit_protein_weight_basis(request):
    """Recognize affirmative reference directives only, never infer from a trajectory."""
    text = unicodedata.normalize("NFKD", request.user_message.content.lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    bases = set()
    for clause in re.split(r"[!?;\n]|(?<!\d)[.,](?!\d)", text):
        # Negative, hypothetical and interrogative statements are not instructions.
        if re.search(r"\b(?:no|nunca|evita|sin|si|debo|deberia|podria)\b|¿", clause):
            continue
        match = re.search(
            r"\b(?:usa|usar|utiliza|utilizar)\s+(?:explicitamente\s+)?(?:el\s+)?peso "
            r"(proyectado|medido|actual|registrado)\b.{0,100}?"
            r"(?:como referencia (?:de |para (?:la )?)proteina|para (?:calcular (?:la )?)?(?:proteina|ppk))\b",
            clause,
        )
        if match:
            bases.add("projected" if match[1] == "proyectado" else "measured")
    return next(iter(bases)) if len(bases) == 1 else None


def _specification_needs_capture(request, specification):
    if not isinstance(specification, Mapping) or not specification:
        return True
    expected = explicit_protein_weight_basis(request)
    return expected is not None and specification.get("weight_basis") != expected


def weekly_capture_instruction(request):
    expected = explicit_protein_weight_basis(request)
    suffix = (f" La referencia de proteína solicitada explícitamente exige weight_basis='{expected}'. "
              "measured_weight_kg es el peso inicial medido, no una elección de la referencia proteica. "
              "Corrige cualquier contradicción antes de crear la propuesta.") if expected else ""
    return WEEKLY_CAPTURE_INSTRUCTION + suffix


WEEKLY_CAPTURE_INSTRUCTION = (
    "Esta solicitud de programa necesita program_specification completo, no requisitos en notes. "
    "Registra los valores expresados por el usuario en ese objeto; no los dupliques en objetivos escalares. "
    "El peso medido, los pesos proyectados y las calorías manuales ya dados no requieren edad, sexo o altura "
    "para este cálculo. Si falta un requisito obligatorio, pregunta por él sin inventarlo. "
    "Los defaults y blocking_fields del plan escalar no sustituyen este contrato semanal. "
    "Después de capturarlo crea la propuesta revisable solicitada. Capturar notas NO crea una propuesta."
)
