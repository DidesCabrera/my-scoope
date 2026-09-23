from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from ai_assistant.application.objective_state import infer_active_work
from ai_assistant.application.tool_selection import select_provider_tools
from ai_assistant.application.tools import list_provider_tool_specs
from ai_assistant.domain import AssistantMessage, AssistantMessageRole, AssistantTurnRequest

EVALUATION_DATASET_VERSION = "ai_assistant.task_dataset.v1"


@dataclass(frozen=True)
class AssistantTaskCase:
    key: str
    family: str
    message: str
    objective: str
    expected_outcome: str
    resource: str
    action: str
    required_capability: str

    def as_dict(self) -> dict[str, str]:
        return {
            "key": self.key,
            "family": self.family,
            "message": self.message,
            "objective": self.objective,
            "expected_outcome": self.expected_outcome,
            "resource": self.resource,
            "action": self.action,
            "required_capability": self.required_capability,
        }


def assistant_task_dataset() -> tuple[AssistantTaskCase, ...]:
    """Return 64 versioned routing cases that complement full live trajectories."""

    cases: list[AssistantTaskCase] = []
    cases.extend(
        _family(
            "dailyplan_create",
            (
                "Crea un plan diario de 2200 kcal.",
                "Quiero una dieta simple.",
                "Necesito un dailyplan para hoy.",
                "Dame un plan diario con cuatro comidas.",
                "Prepara una dieta para mí.",
                "Quiero perder grasa.",
                "Mi objetivo es ganar músculo.",
                "Quiero comer mejor.",
            ),
            objective="create_reviewable_dailyplan_proposal",
            outcome="nutrition_proposal",
            resource="dailyplan",
            action="create",
            capability="create_nutrition_engine_dailyplan_proposal_from_drafts",
        )
    )
    cases.extend(
        _family(
            "meal_create",
            (
                "Crea una comida de 450 kcal.",
                "Arma un almuerzo alto en proteína.",
                "Genera un desayuno sencillo.",
                "Dame una cena con pocas grasas.",
                "Quiero una comida para después de entrenar.",
                "Necesito un meal de 600 kcal.",
                "Prepara una colación rápida.",
                "Hazme una comida equilibrada.",
            ),
            objective="create_reviewable_meal_proposal",
            outcome="nutrition_proposal",
            resource="meal",
            action="create",
            capability="create_nutrition_solver_meal_proposal",
        )
    )
    cases.extend(
        _family(
            "program_create",
            (
                "Crea un programa de cuatro semanas.",
                "Quiero un programa semanal nuevo.",
                "Prepara un programa para el próximo mes.",
                "Genera una semana de entrenamiento nutricional.",
                "Dame un programa simple.",
                "Necesito un programa con mis planes.",
                "Armemos una semana nueva.",
                "Hazme un programa de alimentación.",
            ),
            objective="create_reviewable_program_proposal",
            outcome="nutrition_proposal",
            resource="program",
            action="create",
            capability="create_nutrition_engine_dailyplan_proposal_from_drafts",
        )
    )
    mutation_cases = (
        ("Renombra mi comida a Almuerzo rápido.", "meal", "rename"),
        ("Elimina este alimento de mi biblioteca.", "food", "delete"),
        ("Cambia mi plan diario a 2300 kcal.", "dailyplan", "update"),
        ("Pausa mi calendario activo.", "calendarization", "pause"),
        ("Reanuda el calendario del programa.", "calendarization", "resume"),
        ("Aprueba esta propuesta.", "proposal", "approve"),
        ("Rechaza la propuesta actual.", "proposal", "reject"),
        ("Duplica la última semana del programa.", "program", "duplicate"),
    )
    for index, (message, resource, action) in enumerate(mutation_cases, start=1):
        cases.append(
            AssistantTaskCase(
                key=f"workspace_mutation_{index:02d}",
                family="workspace_mutation",
                message=message,
                objective="prepare_reviewable_workspace_patch",
                expected_outcome="prepared_patch",
                resource=resource,
                action=action,
                required_capability="propose_workspace_patch",
            )
        )
    query_cases = (
        ("¿Qué programas tengo activos?", "program"),
        ("Muéstrame mis comidas.", "meal"),
        ("Lista mis alimentos.", "food"),
        ("Busca un plan diario de 2200 kcal.", "dailyplan"),
        ("¿Cuántas propuestas tengo?", "proposal"),
        ("Revisa mi calendario actual.", "calendarization"),
        ("Dime qué comparaciones guardé.", "saved_comparison"),
        ("¿Tengo alguna dieta reciente?", "dailyplan"),
    )
    for index, (message, resource) in enumerate(query_cases, start=1):
        cases.append(
            AssistantTaskCase(
                key=f"workspace_query_{index:02d}",
                family="workspace_query",
                message=message,
                objective="query_workspace",
                expected_outcome="workspace_query",
                resource=resource,
                action="read",
                required_capability="query_workspace",
            )
        )
    cases.extend(
        _family(
            "profile_fact",
            (
                "Peso 80 kg.",
                "Mido 180 cm.",
                "Tengo 38 años.",
                "Soy hombre.",
                "Mi actividad es moderada.",
                "Entreno cuatro veces por semana.",
                "Mi altura es 172 cm.",
                "Soy mujer y tengo 31 años.",
            ),
            objective="record_conversation_facts",
            outcome="workspace_advanced",
            resource="profile",
            action="update_draft",
            capability="update_profile_draft",
        )
    )
    cases.extend(
        _family(
            "preference_fact",
            (
                "Prefiero comidas simples.",
                "Evito el cilantro.",
                "Tengo alergia a los frutos secos.",
                "Soy vegetariano.",
                "Quiero opciones sin gluten.",
                "Tengo poco presupuesto.",
                "Prefiero cocinar rápido.",
                "Necesito más variedad en mis comidas.",
            ),
            objective="record_conversation_facts",
            outcome="workspace_advanced",
            resource="preferences",
            action="update_draft",
            capability="update_preference_draft",
        )
    )
    cases.extend(
        _family(
            "response_only",
            (
                "Hola.",
                "Gracias.",
                "Explícame qué es la fibra dietaria.",
                "¿Cómo estás?",
                "Cuéntame brevemente cómo funciona el asistente.",
                "Eso era todo.",
                "Buen trabajo.",
                "¿Qué significa proteína completa?",
            ),
            objective="respond_to_current_message",
            outcome="response_only",
            resource="none",
            action="respond",
            capability="natural_response",
        )
    )
    return tuple(cases)


def evaluate_assistant_task_dataset(
    cases: Sequence[AssistantTaskCase] | None = None,
) -> dict[str, Any]:
    selected = tuple(cases or assistant_task_dataset())
    failures: list[dict[str, Any]] = []
    tool_surface_failures: list[dict[str, Any]] = []
    family_counts: dict[str, int] = {}
    available = tuple(list_provider_tool_specs())
    for case in selected:
        family_counts[case.family] = family_counts.get(case.family, 0) + 1
        actual = infer_active_work(None, current_user_message=case.message)
        expected = {
            "objective": case.objective,
            "expected_outcome": case.expected_outcome,
            "resource": case.resource,
            "action": case.action,
        }
        mismatches = {
            key: {"expected": expected[key], "actual": actual.get(key)}
            for key in expected
            if actual.get(key) != expected[key]
        }
        if mismatches:
            failures.append(
                {
                    "key": case.key,
                    "family": case.family,
                    "message": case.message,
                    "mismatches": mismatches,
                }
            )
        if case.required_capability != "natural_response":
            selected_tools = select_provider_tools(
                AssistantTurnRequest(
                    user_message=AssistantMessage(
                        role=AssistantMessageRole.USER,
                        content=case.message,
                    ),
                    context={
                        "surface": "ai_nutrition_intake",
                        "metadata": {
                            "tool_oriented_intake": {
                                "work_progress": {
                                    "active_objective": case.objective,
                                    "active_work": actual,
                                    "blocking_fields": [],
                                }
                            }
                        },
                    },
                ),
                available=available,
                enable_reviewable_proposal_tools=True,
            )
            selected_names = {
                str(tool.get("name") or "") for tool in selected_tools
            }
            if case.required_capability not in selected_names:
                tool_surface_failures.append(
                    {
                        "key": case.key,
                        "family": case.family,
                        "required_capability": case.required_capability,
                        "selected_capabilities": sorted(selected_names),
                    }
                )
    all_failures = [*failures, *tool_surface_failures]
    return {
        "version": EVALUATION_DATASET_VERSION,
        "case_count": len(selected),
        "family_counts": dict(sorted(family_counts.items())),
        "passed_count": len(selected) - len({item["key"] for item in all_failures}),
        "failure_count": len(all_failures),
        "passed": not all_failures,
        "failures": failures,
        "tool_surface_failures": tool_surface_failures,
        "scope": "deterministic_objective_outcome_and_tool_availability",
        "live_trajectory_layer_is_separate": True,
    }


def _family(
    family: str,
    messages: Sequence[str],
    *,
    objective: str,
    outcome: str,
    resource: str,
    action: str,
    capability: str,
) -> list[AssistantTaskCase]:
    return [
        AssistantTaskCase(
            key=f"{family}_{index:02d}",
            family=family,
            message=message,
            objective=objective,
            expected_outcome=outcome,
            resource=resource,
            action=action,
            required_capability=capability,
        )
        for index, message in enumerate(messages, start=1)
    ]


__all__ = [
    "AssistantTaskCase",
    "EVALUATION_DATASET_VERSION",
    "assistant_task_dataset",
    "evaluate_assistant_task_dataset",
]
