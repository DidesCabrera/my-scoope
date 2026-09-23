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
    if not requires_weekly_specification(request):
        return False
    for result in reversed(tuple(results)):
        if result.ok and result.tool_name == "update_proposal_preferences":
            draft = (result.data or {}).get("proposal_preferences") or {}
            return not isinstance(draft.get("program_specification"), Mapping) or not draft["program_specification"]
    workspace = (request.context.get("metadata") or {}).get("tool_oriented_intake") or {}
    drafts = workspace.get("current_drafts") or {}
    return not (drafts.get("proposal_preferences") or {}).get("program_specification")


WEEKLY_CAPTURE_INSTRUCTION = (
    "Esta solicitud de programa necesita program_specification completo, no requisitos en notes. "
    "Registra los valores expresados por el usuario en ese objeto; no los dupliques en objetivos escalares. "
    "El peso medido, los pesos proyectados y las calorías manuales ya dados no requieren edad, sexo o altura "
    "para este cálculo. Si falta un requisito obligatorio, pregunta por él sin inventarlo. "
    "Los defaults y blocking_fields del plan escalar no sustituyen este contrato semanal. "
    "Después de capturarlo crea la propuesta revisable solicitada. Capturar notas NO crea una propuesta."
)
