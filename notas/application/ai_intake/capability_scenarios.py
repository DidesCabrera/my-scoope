"""Launch cases with independently specified persisted patch outcomes."""

from dataclasses import replace

from ai_assistant.models import AIPreparedAction
from notas.application.queries.library_queries import food_library_queryset, meal_library_queryset, dailyplan_library_queryset, program_library_queryset


def operation(action_key, target_id=None, **parameters):
    return {"action_key": action_key, "target_id": target_id, "parameters": parameters}


PATCH_CASES = (
    ("crear_alimento_exacto", "F-03", "Crea un alimento llamado Avena laboratorio con 13 g de proteína, 68 g de carbohidratos y 7 g de grasa por 100 g.", operation("food.create", name="Avena laboratorio", protein=13, carbs=68, fat=7)),
    ("renombrar_alimento", "F-05", "Renombra el alimento {food_id} como Alimento revisado.", operation("food.update", "{food_id}", name="Alimento revisado")),
    ("actualizar_macros_alimento", "F-06", "Cambia los macros por 100 g del alimento {food_id} a 12 g de proteína, 22 g de carbohidratos y 6 g de grasa.", operation("food.update", "{food_id}", protein=12, carbs=22, fat=6)),
    ("desactivar_alimento", "F-09", "Desactiva el alimento {food_id} de mi biblioteca.", operation("food.delete", "{food_id}")),
    ("crear_comida_vacia", "M-02", "Crea una comida vacía llamada Cena de laboratorio.", operation("meal.create", name="Cena de laboratorio")),
    ("renombrar_comida", "M-06", "Renombra la comida de biblioteca {meal_id} como Cena revisada.", operation("meal.rename", "{meal_id}", name="Cena revisada")),
    ("eliminar_comida", "M-06", "Elimina la comida de biblioteca {meal_id}.", operation("meal.delete", "{meal_id}")),
    ("agregar_alimento_comida", "M-07", "Agrega el alimento {food_id} a mi comida de biblioteca {meal_id} con 175 g.", operation("meal.add_food", "{meal_id}", food_id="{food_id}", quantity=175)),
    ("cambiar_gramos_comida", "M-09", "En la comida {meal_id}, cambia solamente la cantidad de su alimento {source_food_id} a 135 g. Su registro de composición es {meal_food_id}.", operation("meal.update_food", "{meal_food_id}", quantity=135)),
    ("quitar_alimento_comida", "M-07", "Quita el alimento {source_food_id} de la comida {meal_id}.", operation("meal.remove_food", "{meal_food_id}", food_id="{source_food_id}")),
    ("crear_plan_vacio", "DP-02", "Crea un plan diario vacío llamado Día de laboratorio.", operation("dailyplan.create", name="Día de laboratorio")),
    ("renombrar_plan", "DP-02", "Renombra el plan diario {dailyplan_id} como Día revisado.", operation("dailyplan.rename", "{dailyplan_id}", name="Día revisado")),
    ("eliminar_plan", "DP-02", "Elimina el plan diario {dailyplan_id} de mi biblioteca.", operation("dailyplan.delete", "{dailyplan_id}")),
    ("agregar_comida_plan", "DP-03", "Agrega mi comida de biblioteca {meal_id} al plan diario {dailyplan_id}, a las 13:30, con la nota Después de entrenar.", operation("dailyplan.add_meal", "{dailyplan_id}", meal_id="{meal_id}", hour="13:30", note="Después de entrenar")),
    ("crear_programa_vacio", "PG-02", "Crea un programa vacío llamado Programa de laboratorio de 3 semanas. No selecciones planes ni inventes un menú.", operation("program.create", name="Programa de laboratorio", duration_weeks=3)),
    ("renombrar_programa", "PG-03", "Renombra mi programa plantilla {program_id} como Programa revisado.", operation("program.rename", "{program_id}", name="Programa revisado")),
    ("eliminar_programa", "PG-03", "Elimina el programa plantilla {program_id}; no canceles ningún programa calendarizado.", operation("program.delete", "{program_id}")),
    ("agregar_semana", "PG-04", "Agrega una semana vacía al programa plantilla {program_id}.", operation("program.add_week", "{program_id}")),
)


def build_capability_scenarios(scenario_type):
    return {
        key: scenario_type(
            key=key, description=f"Exact reviewable product outcome: {capability}",
            user_messages=(message + " Prepara el cambio para revisión; no lo apliques.",),
            required_tool_names=("propose_workspace_patch",),
            capability_ids=(capability,), max_tool_calls=8,
            mutation_policy="prepared_action_only", expected_outcome="prepared_patch",
            fixture_requirements=("capability_fixture",), default_enabled=False,
            ground_truth={"expected_operations": [expected]},
            manual_review_prompts=("¿La respuesta comunica el cambio exacto y que está pendiente de aprobación?",),
        )
        for key, capability, message, expected in PATCH_CASES
    }


def specialize_capability_scenario(scenario, *, user):
    if scenario.key not in {case[0] for case in PATCH_CASES}:
        return None
    food = food_library_queryset(user).filter(created_by=user).order_by("id").first()
    meal = meal_library_queryset(user).order_by("id").first()
    plan = dailyplan_library_queryset(user).order_by("id").first()
    program = program_library_queryset(user).filter(created_by=user).order_by("id").first()
    meal_food = meal.meal_food_set.order_by("id").first() if meal else None
    if scenario.key == "agregar_alimento_comida" and meal:
        food = food_library_queryset(user).exclude(pk__in=meal.meal_food_set.values("food_id")).order_by("id").first()
    values = {
        "food_id": food.pk if food else None,
        "meal_id": meal.pk if meal else None,
        "dailyplan_id": plan.pk if plan else None,
        "program_id": program.pk if program else None,
        "meal_food_id": meal_food.pk if meal_food else None,
        "source_food_id": meal_food.food_id if meal_food else None,
    }
    message = scenario.user_messages[0]
    missing = [key for key, value in values.items() if "{" + key + "}" in message and value is None]

    def bind(value):
        if isinstance(value, dict):
            return {key: bind(item) for key, item in value.items()}
        if isinstance(value, str) and value.startswith("{"):
            return values[value[1:-1]]
        return value

    return replace(scenario, user_messages=(message.format(**values),), ground_truth={
        "expected_operations": [bind(item) for item in scenario.ground_truth["expected_operations"]],
        "missing_fixture_fields": missing,
    })


def prepared_patch_check(scenario, *, user, previous_ids):
    expected = scenario.ground_truth.get("expected_operations")
    if expected is None:
        return None
    actions = list(AIPreparedAction.objects.filter(user=user).exclude(pk__in=previous_ids))
    if len(actions) != 1:
        return False, f"Expected one reviewable patch; observed {len(actions)}."
    action = actions[0]
    if action.status != AIPreparedAction.Status.PREPARED or action.action_key != "workspace.patch":
        return False, "Expected an unapplied workspace patch."
    if action.preview.get("writes_applied") is not False or action.preview.get("requires_explicit_confirmation") is not True:
        return False, "Patch lacks the explicit approval boundary."
    actual = action.arguments.get("operations", [])
    if len(actual) != len(expected):
        return False, f"Expected {len(expected)} operation(s); observed {len(actual)}."
    for wanted, observed in zip(expected, actual):
        for field in ("action_key", "target_id", "parameters"):
            if observed.get(field) != wanted[field]:
                return False, f"Incorrect {field}: expected {wanted[field]!r}; observed {observed.get(field)!r}"
        if observed.get("references"):
            return False, "Unexpected deferred entity reference."
    return True, "Persisted patch matches the exact requested operations, targets and parameters."
