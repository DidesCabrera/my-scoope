from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

PREPARED_ACTION_TTL = timedelta(minutes=30)


@dataclass(frozen=True)
class PreparedActionSpec:
    action_key: str
    target_type: str
    title: str
    required_arguments: tuple[str, ...] = ()
    destructive: bool = False
    creates_entity: bool = False


PREPARED_ACTION_SPECS = {
    spec.action_key: spec
    for spec in (
        PreparedActionSpec("food.create", "food", "Crear alimento", ("name", "protein", "carbs", "fat"), creates_entity=True),
        PreparedActionSpec("food.update", "food", "Actualizar alimento"),
        PreparedActionSpec("food.delete", "food", "Eliminar alimento", destructive=True),
        PreparedActionSpec("meal.create", "meal", "Crear comida", ("name",), creates_entity=True),
        PreparedActionSpec("meal.rename", "meal", "Renombrar comida", ("name",)),
        PreparedActionSpec("meal.delete", "meal", "Eliminar comida", destructive=True),
        PreparedActionSpec("dailyplan.create", "dailyplan", "Crear plan diario", ("name",), creates_entity=True),
        PreparedActionSpec("dailyplan.rename", "dailyplan", "Renombrar plan diario", ("name",)),
        PreparedActionSpec("dailyplan.delete", "dailyplan", "Eliminar plan diario", destructive=True),
        PreparedActionSpec("program.create", "program", "Crear programa", ("name",), creates_entity=True),
        PreparedActionSpec("program.rename", "program", "Renombrar programa", ("name",)),
        PreparedActionSpec("program.delete", "program", "Eliminar programa", destructive=True),
        PreparedActionSpec("program.add_week", "program", "Agregar semana al programa"),
        PreparedActionSpec("program.duplicate_week", "program", "Duplicar semana del programa", ("week_number",)),
        PreparedActionSpec("program.remove_week", "program", "Eliminar semana del programa", ("week_number",), destructive=True),
        PreparedActionSpec("calendar.pause", "calendarization", "Pausar calendarización"),
        PreparedActionSpec("calendar.resume", "calendarization", "Reanudar calendarización"),
        PreparedActionSpec("calendar.cancel", "calendarization", "Cancelar calendarización", destructive=True),
        PreparedActionSpec("comparison.rename", "saved_comparison", "Renombrar comparación", ("name",)),
        PreparedActionSpec("proposal.approve", "proposal", "Aprobar propuesta"),
        PreparedActionSpec("proposal.reject", "proposal", "Rechazar propuesta", destructive=True),
        PreparedActionSpec("proposal.cancel", "proposal", "Cancelar propuesta", destructive=True),
        PreparedActionSpec("proposal.delete", "proposal", "Eliminar propuesta", destructive=True),
        PreparedActionSpec("proposal.apply", "proposal", "Aplicar propuesta aprobada"),
    )
}

