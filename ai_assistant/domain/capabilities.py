"""Canonical user-facing AI Assistant capability map.

This catalog describes outcomes, not transport details. The tool registry is
the source of executable tool contracts; this map states how every human
product area is assisted and which safety boundary applies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AssistantCapabilityMode(str, Enum):
    AUTONOMOUS_READ = "autonomous_read"
    REVIEWABLE_PROPOSAL = "reviewable_proposal"
    PREPARED_ACTION = "prepared_action"
    TRUSTED_UI_HANDOFF = "trusted_ui_handoff"
    STAFF_ONLY = "staff_only"


@dataclass(frozen=True)
class AssistantCapability:
    code: str
    domain: str
    outcome: str
    mode: AssistantCapabilityMode
    tool_names: tuple[str, ...] = ()
    prepared_action_keys: tuple[str, ...] = ()
    notes: str = ""

    @property
    def requires_confirmation(self) -> bool:
        return self.mode in {
            AssistantCapabilityMode.REVIEWABLE_PROPOSAL,
            AssistantCapabilityMode.PREPARED_ACTION,
            AssistantCapabilityMode.TRUSTED_UI_HANDOFF,
        }


CAPABILITIES = (
    AssistantCapability("profile.read", "profile", "Consultar ficha, peso y contexto nutricional.", AssistantCapabilityMode.AUTONOMOUS_READ, ("read_user_profile_context",)),
    AssistantCapability("profile.update", "profile", "Preparar y confirmar cambios de ficha.", AssistantCapabilityMode.PREPARED_ACTION, ("update_profile_draft", "share_profile_draft_card")),
    AssistantCapability("foods.read", "foods", "Listar, buscar y consultar alimentos propios o disponibles.", AssistantCapabilityMode.AUTONOMOUS_READ, ("list_user_foods", "search_operational_foods", "read_food")),
    AssistantCapability("foods.manage", "foods", "Crear, actualizar o eliminar alimentos propios.", AssistantCapabilityMode.PREPARED_ACTION, ("prepare_product_action",), ("food.create", "food.update", "food.delete")),
    AssistantCapability("foods.import_reorder_share", "foods", "Importar, ordenar, borrar en lote o compartir alimentos.", AssistantCapabilityMode.TRUSTED_UI_HANDOFF, notes="Importaciones y envíos externos conservan sus formularios y validaciones dedicadas."),
    AssistantCapability("meals.read", "meals", "Listar, buscar y consultar comidas y cantidades.", AssistantCapabilityMode.AUTONOMOUS_READ, ("list_user_meals", "search_user_meals", "read_meal")),
    AssistantCapability("meals.manage", "meals", "Crear, renombrar o eliminar comidas propias.", AssistantCapabilityMode.PREPARED_ACTION, ("prepare_product_action",), ("meal.create", "meal.rename", "meal.delete")),
    AssistantCapability("meals.compose_share", "meals", "Configurar alimentos, copiar, guardar o compartir comidas.", AssistantCapabilityMode.TRUSTED_UI_HANDOFF),
    AssistantCapability("dailyplans.read", "dailyplans", "Listar, resolver por nombre y consultar planes completos.", AssistantCapabilityMode.AUTONOMOUS_READ, ("list_user_dailyplans", "search_user_dailyplans", "read_dailyplan")),
    AssistantCapability("dailyplans.manage", "dailyplans", "Crear, renombrar o eliminar planes propios.", AssistantCapabilityMode.PREPARED_ACTION, ("prepare_product_action",), ("dailyplan.create", "dailyplan.rename", "dailyplan.delete")),
    AssistantCapability("dailyplans.compose_share", "dailyplans", "Configurar comidas snapshot, copiar, guardar o compartir planes.", AssistantCapabilityMode.TRUSTED_UI_HANDOFF),
    AssistantCapability("dailyplans.rebalance", "nutrition", "Ajustar calorías conservando alimentos y estructura.", AssistantCapabilityMode.REVIEWABLE_PROPOSAL, ("create_proportional_dailyplan_calorie_proposal", "compare_dailyplan_to_targets")),
    AssistantCapability("nutrition.generate", "nutrition", "Generar o iterar propuestas de comidas y planes.", AssistantCapabilityMode.REVIEWABLE_PROPOSAL, ("create_nutrition_solver_meal_proposal", "create_nutrition_engine_dailyplan_proposal", "iterate_nutrition_engine_dailyplan_proposal")),
    AssistantCapability("programs.read", "programs", "Listar, buscar y consultar programas semanales.", AssistantCapabilityMode.AUTONOMOUS_READ, ("list_user_programs", "read_program")),
    AssistantCapability("programs.manage", "programs", "Crear, renombrar, eliminar o gestionar semanas.", AssistantCapabilityMode.PREPARED_ACTION, ("prepare_product_action",), ("program.create", "program.rename", "program.delete", "program.add_week", "program.duplicate_week", "program.remove_week")),
    AssistantCapability("programs.compose_share", "programs", "Asignar planes a días, copiar o compartir programas.", AssistantCapabilityMode.TRUSTED_UI_HANDOFF),
    AssistantCapability("calendar.read", "calendar", "Consultar calendarización actual e historial.", AssistantCapabilityMode.AUTONOMOUS_READ, ("read_calendarization",)),
    AssistantCapability("calendar.lifecycle", "calendar", "Pausar, reanudar o cancelar una calendarización.", AssistantCapabilityMode.PREPARED_ACTION, ("prepare_product_action",), ("calendar.pause", "calendar.resume", "calendar.cancel")),
    AssistantCapability("calendar.activate_preferences", "calendar", "Activar un programa o cambiar notificaciones y zona horaria.", AssistantCapabilityMode.TRUSTED_UI_HANDOFF),
    AssistantCapability("comparisons.read", "comparisons", "Listar y consultar comparaciones guardadas.", AssistantCapabilityMode.AUTONOMOUS_READ, ("list_saved_comparisons", "read_saved_comparison")),
    AssistantCapability("comparisons.manage", "comparisons", "Renombrar comparaciones guardadas.", AssistantCapabilityMode.PREPARED_ACTION, ("prepare_product_action",), ("comparison.rename",)),
    AssistantCapability("comparisons.create", "comparisons", "Crear y actualizar comparaciones de alimentos, comidas o planes.", AssistantCapabilityMode.TRUSTED_UI_HANDOFF),
    AssistantCapability("proposals.read", "proposals", "Listar y consultar propuestas y su validación.", AssistantCapabilityMode.AUTONOMOUS_READ, ("list_user_proposals", "read_proposal")),
    AssistantCapability("proposals.lifecycle", "proposals", "Aprobar, rechazar, cancelar, eliminar o aplicar propuestas.", AssistantCapabilityMode.PREPARED_ACTION, ("prepare_product_action",), ("proposal.approve", "proposal.reject", "proposal.cancel", "proposal.delete", "proposal.apply")),
    AssistantCapability("inbox.read", "inbox", "Consultar elementos recibidos, enviados y favoritos.", AssistantCapabilityMode.AUTONOMOUS_READ, ("list_inbox_items",)),
    AssistantCapability("inbox.manage", "inbox", "Marcar, guardar, descartar o eliminar elementos compartidos.", AssistantCapabilityMode.TRUSTED_UI_HANDOFF),
    AssistantCapability("account.billing.read", "account_billing", "Consultar plan, créditos, suscripción, pagos y documentos.", AssistantCapabilityMode.AUTONOMOUS_READ, ("read_account_billing_context",)),
    AssistantCapability("account.billing.change", "account_billing", "Iniciar checkout o cancelar una suscripción.", AssistantCapabilityMode.TRUSTED_UI_HANDOFF, notes="Nunca se llama al proveedor de pagos desde una tool del modelo."),
    AssistantCapability("admin.analytics", "admin", "Consultar analítica administrativa.", AssistantCapabilityMode.STAFF_ONLY, notes="Fuera del catálogo del usuario; exige superficie y permisos de staff."),
    AssistantCapability("admin.operations", "admin", "Ejecutar operaciones administrativas.", AssistantCapabilityMode.STAFF_ONLY, notes="Separación estricta; nunca se delega a la identidad del usuario final."),
)


CAPABILITY_BY_CODE = {capability.code: capability for capability in CAPABILITIES}


def list_capabilities(*, domain: str | None = None) -> tuple[AssistantCapability, ...]:
    if not domain:
        return CAPABILITIES
    normalized = str(domain).strip().lower()
    return tuple(item for item in CAPABILITIES if item.domain == normalized)


def get_capability(code: str) -> AssistantCapability:
    normalized = str(code or "").strip().lower()
    try:
        return CAPABILITY_BY_CODE[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported_assistant_capability:{normalized}") from exc
