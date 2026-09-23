"""Evaluation-lab scenarios and state invariants for real-provider validation."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
from typing import Any, Mapping, Sequence

from ai_assistant.models import AIPreparedAction
from notas.application.queries.library_queries import (
    dailyplan_library_queryset,
    food_library_queryset,
    meal_library_queryset,
    program_library_queryset,
)
from notas.domain.models import NutritionProposal, Food, Meal, MealFood, DailyPlan, DailyPlanMeal, Program, ProgramDay
from notas.application.ai_intake.capability_scenarios import specialize_capability_scenario


@dataclass(frozen=True)
class RealProviderValidationScenario:
    key: str
    description: str
    user_messages: Sequence[str]
    expected_final_brief: Mapping[str, Any] = field(default_factory=dict)
    expected_brief_transitions: Mapping[str, Sequence[Any]] = field(default_factory=dict)
    stable_brief_fields: Sequence[str] = field(default_factory=tuple)
    fields_not_reasked_after_capture: Sequence[str] = field(default_factory=tuple)
    required_tool_names: Sequence[str] = field(default_factory=tuple)
    expected_tool_errors: Mapping[str, str] = field(default_factory=dict)
    min_final_card_counts: Mapping[str, int] = field(default_factory=dict)
    max_final_card_counts: Mapping[str, int] = field(default_factory=dict)
    manual_review_prompts: Sequence[str] = field(default_factory=tuple)
    forbidden_tool_names: Sequence[str] = field(default_factory=tuple)
    forbidden_visible_fragments: Sequence[str] = field(default_factory=tuple)
    expected_visible_fragments_by_turn: Mapping[int, Sequence[str]] = field(default_factory=dict)
    max_repeated_opening_count: int | None = None
    max_tool_calls: int | None = None
    visible_reask_markers: Mapping[str, Sequence[str]] = field(default_factory=dict)
    profile_preflight_facts: Mapping[str, Any] = field(default_factory=dict)
    profile_preflight_missing_fields: Sequence[str] = field(default_factory=tuple)
    capability_ids: Sequence[str] = field(default_factory=tuple)
    diagnostic_domains: Sequence[str] = field(default_factory=tuple)
    fixture_requirements: Sequence[str] = field(default_factory=tuple)
    mutation_policy: str = "read_only"
    ground_truth: Mapping[str, Any] = field(default_factory=dict)
    default_enabled: bool = True
    expected_outcome: str = "response_only"


def build_lab_scenarios() -> dict[str, Any]:
    return {
        "comida_450_kcal": RealProviderValidationScenario(
            key="comida_450_kcal",
            description=(
                "Create a reviewable 450 kcal meal with the deterministic solver and real "
                "operational food candidates, without mutating the meal library."
            ),
            user_messages=(
                "Crea ahora una propuesta revisable de comida de 450 kcal usando el plan diario "
                "de contexto ID {dailyplan_id}. Usa los alimentos disponibles en My Scoope y "
                "ejecuta el solver; no inventes alimentos ni apliques la propuesta.",
            ),
            required_tool_names=("create_nutrition_solver_meal_proposal",),
            max_tool_calls=4,
            capability_ids=("M-04", "A-03"),
            diagnostic_domains=("tool_routing", "solver_feasibility", "catalog_data", "state_mutation"),
            fixture_requirements=("owned_dailyplan", "solver_450_feasible"),
            mutation_policy="proposal_only",
            default_enabled=False,
            expected_outcome="nutrition_proposal",
            manual_review_prompts=(
                "¿La respuesta presenta una propuesta concreta y revisable, en vez de una receta inventada?",
                "¿Explica la calidad o limitación real del solver sin afirmar que modificó la biblioteca?",
            ),
        ),
        "reemplazo_alimento_200g": RealProviderValidationScenario(
            key="reemplazo_alimento_200g",
            description=(
                "Resolve an exact owned meal and prepare a deterministic food replacement at 200 g, "
                "without applying it before confirmation."
            ),
            user_messages=(
                "En mi comida «{meal_name}» (ID {meal_id}), cambia el alimento "
                "«{source_food_name}» (ID {source_food_id}) por «{replacement_food_name}» "
                "(ID {replacement_food_id}) y deja la porción en 200 g. Prepara el cambio "
                "para que yo lo revise; no lo apliques todavía.",
            ),
            required_tool_names=("propose_workspace_patch",),
            max_tool_calls=6,
            capability_ids=("M-08",),
            diagnostic_domains=("language_understanding", "tool_routing", "state_mutation"),
            fixture_requirements=("meal_replacement_fixture",),
            mutation_policy="prepared_action_only",
            default_enabled=False,
            expected_outcome="prepared_patch",
            manual_review_prompts=(
                "¿La vista previa identifica la comida y ambos alimentos correctos, con 200 g exactos?",
                "¿El asistente deja claro que el cambio aún necesita confirmación?",
            ),
        ),
        "plan_2400_distribucion_30_50_20": RealProviderValidationScenario(
            key="plan_2400_distribucion_30_50_20",
            description=(
                "Create a reviewable daily-plan proposal from explicit calories and macro distribution."
            ),
            user_messages=(
                "Crea ahora una propuesta revisable de plan diario de 2400 kcal con distribución "
                "30% proteína, 50% carbohidratos y 20% grasas. Para esta propuesta usa: hombre, "
                "38 años, 80 kg, 180 cm, actividad alta, fuerza 4 veces por semana y 4 comidas. "
                "No apliques la propuesta sin mi aprobación.",
            ),
            expected_final_brief={
                "requested_entity": "daily_plan",
                "weight_kg": 80.0,
                "meals_per_day": 4,
            },
            required_tool_names=(
                "update_profile_draft",
                "update_proposal_preferences",
                "create_nutrition_engine_dailyplan_proposal_from_drafts",
            ),
            max_tool_calls=8,
            capability_ids=("DP-13",),
            diagnostic_domains=("language_understanding", "guardrail_policy", "solver_feasibility", "state_mutation"),
            fixture_requirements=("solver_candidates",),
            mutation_policy="proposal_only",
            default_enabled=False,
            expected_outcome="nutrition_proposal",
            manual_review_prompts=(
                "¿La propuesta conserva 2400 kcal y 30/50/20 sin sustituirlo por una heurística?",
                "¿Las cantidades y el diagnóstico provienen del motor nutricional y quedan para revisión?",
            ),
        ),
    }


def specialize_lab_scenario(scenario: Any, *, user: Any) -> Any | None:
    capability = specialize_capability_scenario(scenario, user=user)
    if capability is not None:
        return capability
    if scenario.key == "bibliotecas_coherentes":
        totals = (
            food_library_queryset(user).count(),
            meal_library_queryset(user).count(),
            dailyplan_library_queryset(user).count(),
            program_library_queryset(user).count(),
        )
        return replace(
            scenario,
            expected_visible_fragments_by_turn={
                index: (f"TOTAL: {total}",)
                for index, total in enumerate(totals, start=1)
            },
            ground_truth={
                "foods_total": totals[0],
                "meals_total": totals[1],
                "dailyplans_total": totals[2],
                "programs_total": totals[3],
                "source": "canonical_web_library_projections",
            },
        )

    if scenario.key == "comida_450_kcal":
        dailyplan = dailyplan_library_queryset(user).order_by("id").first()
        dailyplan_id = int(dailyplan.id) if dailyplan is not None else 0
        return replace(
            scenario,
            user_messages=tuple(
                message.format(dailyplan_id=dailyplan_id)
                for message in scenario.user_messages
            ),
            ground_truth={
                "target_kcal": 450,
                "default_macro_distribution": {"protein": 30, "carbs": 50, "fat": 20},
                "context_dailyplan_id": dailyplan_id or None,
            },
        )

    if scenario.key == "reemplazo_alimento_200g":
        meal = (
            meal_library_queryset(user)
            .prefetch_related("meal_food_set__food")
            .order_by("id")
            .first()
        )
        source_meal_food = meal.meal_food_set.first() if meal is not None else None
        replacement = None
        if source_meal_food is not None:
            replacement = (
                food_library_queryset(user)
                .exclude(id=source_meal_food.food_id)
                .order_by("id")
                .first()
            )
        values = {
            "meal_name": meal.name if meal is not None else "SIN_COMIDA_DISPONIBLE",
            "meal_id": int(meal.id) if meal is not None else 0,
            "source_food_name": (
                source_meal_food.food.name if source_meal_food is not None else "SIN_ALIMENTO_ORIGEN"
            ),
            "source_food_id": (
                int(source_meal_food.food_id) if source_meal_food is not None else 0
            ),
            "replacement_food_name": (
                replacement.name if replacement is not None else "SIN_ALIMENTO_REEMPLAZO"
            ),
            "replacement_food_id": int(replacement.id) if replacement is not None else 0,
        }
        return replace(
            scenario,
            user_messages=tuple(message.format(**values) for message in scenario.user_messages),
            ground_truth={
                **values,
                "meal_id": values["meal_id"] or None,
                "source_food_id": values["source_food_id"] or None,
                "replacement_food_id": values["replacement_food_id"] or None,
                "target_quantity_g": 200,
            },
        )

    if scenario.key == "plan_2400_distribucion_30_50_20":
        return replace(
            scenario,
            ground_truth={
                "target_kcal": 2400,
                "macro_distribution": {"protein": 30, "carbs": 50, "fat": 20},
                "macro_grams": {"protein": 180, "carbs": 300, "fat": 53.33},
                "weight_kg": 80,
            },
        )
    return None


def validation_state_snapshot(user: Any) -> dict[str, Any]:
    # Counts alone cannot detect an unauthorized rename or quantity change.
    content = {}
    for key, queryset in (
        ("foods", Food.objects.filter(created_by=user)),
        ("meals", Meal.objects.filter(created_by=user)),
        ("meal_foods", MealFood.objects.filter(meal__created_by=user)),
        ("dailyplans", DailyPlan.objects.filter(created_by=user)),
        ("dailyplan_meals", DailyPlanMeal.objects.filter(dailyplan__created_by=user)),
        ("programs", Program.objects.filter(created_by=user)),
        ("program_days", ProgramDay.objects.filter(program__created_by=user)),
    ):
        fields = [f.attname for f in queryset.model._meta.concrete_fields if not f.name.startswith("summary_cache")]
        content[key] = list(queryset.order_by("pk").values(*fields))
    return {
        "foods": food_library_queryset(user).count(),
        "meals": meal_library_queryset(user).count(),
        "dailyplans": dailyplan_library_queryset(user).count(),
        "programs": program_library_queryset(user).count(),
        "nutrition_proposals": NutritionProposal.objects.filter(created_by=user).count(),
        "prepared_actions": AIPreparedAction.objects.filter(user=user).count(),
        "product_content_sha256": hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest(),
    }


def state_mutation_check_values(
    scenario: Any,
    *,
    state_before: Mapping[str, int],
    state_after: Mapping[str, int],
) -> tuple[bool, str, str]:
    if not state_before or not state_after:
        return True, "state snapshots were not supplied by this isolated check", "diagnostic"

    library_keys = ("foods", "meals", "dailyplans", "programs")
    deltas = {
        key: int(state_after.get(key, 0)) - int(state_before.get(key, 0))
        for key in (*library_keys, "nutrition_proposals", "prepared_actions")
    }
    failures = [f"{key} delta={deltas[key]}" for key in library_keys if deltas[key] != 0]
    if state_before.get("product_content_sha256") != state_after.get("product_content_sha256"):
        failures.append("persisted product content changed")
    policy = scenario.mutation_policy
    if policy == "read_only":
        failures.extend(
            f"{key} delta={deltas[key]}"
            for key in ("nutrition_proposals", "prepared_actions")
            if deltas[key] != 0
        )
    elif policy == "proposal_only":
        if deltas["nutrition_proposals"] < 1:
            failures.append("no reviewable nutrition proposal was created")
        if deltas["prepared_actions"] != 0:
            failures.append(f"prepared_actions delta={deltas['prepared_actions']}")
    elif policy == "prepared_action_only":
        if deltas["prepared_actions"] < 1:
            failures.append("no reviewable prepared action was created")
        if deltas["nutrition_proposals"] != 0:
            failures.append(f"nutrition_proposals delta={deltas['nutrition_proposals']}")
    else:
        failures.append(f"unsupported mutation policy {policy!r}")
    detail = (
        f"policy={policy}; deltas={deltas}"
        if not failures
        else f"policy={policy}; violations={failures}; deltas={deltas}"
    )
    return not failures, detail, "hard"


def tool_contract_check_values(
    scenario: Any,
    turns: Sequence[Any],
) -> tuple[bool, str]:
    results = [item for turn in turns for item in turn.tool_results]
    actual_names = {str(item.get("tool_name") or "") for item in results}
    missing: list[str] = []
    unsuccessful: list[str] = []
    for tool_name in scenario.required_tool_names:
        matching = [item for item in results if item.get("tool_name") == tool_name]
        if not matching:
            missing.append(tool_name)
            continue
        expected_status = scenario.expected_tool_errors.get(tool_name) or "ok"
        if not any(item.get("status") == expected_status for item in matching):
            observed = sorted({str(item.get("status") or "") for item in matching})
            unsuccessful.append(
                f"{tool_name}: expected {expected_status!r}, observed {observed}"
            )
    error_failures = [
        f"{tool_name}:{expected_status}"
        for tool_name, expected_status in scenario.expected_tool_errors.items()
        if not any(
            item.get("tool_name") == tool_name and item.get("status") == expected_status
            for item in results
        )
    ]
    passed = not missing and not unsuccessful and not error_failures
    if passed:
        return True, f"{len(actual_names)} distinct tool(s) satisfied the scenario contract"
    return False, (
        f"missing tools={missing}; unsuccessful required tools={unsuccessful}; "
        f"missing expected error result(s)={error_failures}"
    )


def scenario_result_lab_metadata(result: Any) -> dict[str, Any]:
    return {
        "capability_ids": list(result.scenario.capability_ids),
        "diagnostic_domains": list(result.scenario.diagnostic_domains),
        "fixture_requirements": list(result.scenario.fixture_requirements),
        "mutation_policy": result.scenario.mutation_policy,
        "ground_truth": dict(result.scenario.ground_truth),
        "state": {
            "before": dict(result.state_before),
            "after": dict(result.state_after),
            "delta": {
                key: int(result.state_after.get(key, 0)) - int(result.state_before.get(key, 0))
                for key in set(result.state_before) | set(result.state_after)
                if key != "product_content_sha256"
            },
            "product_content_unchanged": result.state_before.get("product_content_sha256") == result.state_after.get("product_content_sha256"),
        },
    }
