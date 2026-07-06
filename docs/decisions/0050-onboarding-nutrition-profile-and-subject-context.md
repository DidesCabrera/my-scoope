# 0050 — Onboarding nutricional, ficha personal y sujeto de cálculo

Date: 2026-07-03
Status: accepted
Cycle: Onboarding Nutrition Profile, Patch ONB00

## Context

La implementación de `ai_assistant` y `nutrition_solver` hizo visible que la estimación calórica diaria requiere datos corporales y contextuales: peso, edad, sexo nutricional, altura y nivel de actividad.

Pedir todos esos datos repetidamente en el chat crea fricción y debilita el contrato del solver. Sin embargo, tampoco es correcto asumir que toda propuesta se calcula para el dueño de la cuenta, porque un usuario puede crear una dieta para otra persona, un cliente o una propuesta modelo.

## Decision

My Scoope implementará un onboarding nutricional mínimo conducido por `accounts`, con persistencia de ficha personal en `notas` y consumo estructurado desde `ai_assistant` / `nutrition_solver`.

El onboarding inicial captura solo:

```text
birth_date
sex
height_cm
weight
onboarding_completed_at
onboarding_version
```

El primer chat nutricional completa:

```text
activity_level
training_frequency
```

Las preferencias siguientes no se persisten como defaults de usuario en v1:

```text
default_goal
default_meals_per_day
default_complexity_level
default_budget_level
```

Deben mantenerse como contexto de conversación/propuesta.

## App boundaries

```text
accounts
  conduce onboarding y gate post-login

notas
  persiste Profile, WeightLog y futuras métricas corporales

ai_assistant
  decide si la propuesta usa ficha personal o datos nuevos

nutrition_solver
  calcula sobre un sujeto nutricional explícito
```

`accounts` no será dueño de los datos nutricionales persistentes. `notas` conserva la ficha operativa del usuario.

## Body Metrics

`WeightLog` se conserva en v1 como registro histórico de peso, pero se tratará conceptualmente como parte de Body Metrics.

El acceso futuro debe encapsularse mediante servicios o queries:

```text
record_weight(user, weight_kg, source)
get_current_weight(user)
get_basic_body_profile(user)
```

La migración a un modelo genérico de métricas queda fuera de alcance de v1.

## NutritionSubjectContext

Antes de calcular una propuesta, el Assistant debe determinar el sujeto nutricional:

```text
self_profile
external_chat_data
manual_chat_data
```

La ficha personal es el contexto por defecto, pero no debe asumirse sin confirmación cuando el usuario pide una propuesta nutricional.

El Assistant debe preguntar o resolver:

```text
¿Usamos los datos de tu ficha personal o quieres entregar datos nuevos para esta propuesta?
```

El solver debe recibir un `NutritionSubjectContext` explícito y calcular targets, macros y PPK con los datos de ese sujeto.

## PPK and external proposals

Durante la propuesta, PPK se calcula con el peso del sujeto usado en el cálculo.

Si una propuesta calculada con datos externos se guarda en la librería personal del usuario, My Scoope debe advertir que indicadores dependientes del perfil, como PPK, se recalcularán usando el peso registrado en la ficha personal.

La advertencia debe aclarar que:

- kcal y gramos de macros no cambian;
- el PPK visible en la librería puede cambiar;
- la diferencia se debe al peso de la ficha personal del dueño de la librería.

## Consequences

- El onboarding v1 será corto y no intentará completar todo el brief nutricional.
- El primer chat sigue siendo necesario para capturar actividad y entrenamiento.
- `nutrition_solver` no dependerá del usuario autenticado como sujeto implícito.
- `ai_assistant` deberá construir o seleccionar un sujeto de cálculo antes de llamar tools del solver.
- Las propuestas externas requerirán warning antes de guardarse/aplicarse en la librería.
- Profile deberá refactorizarse en secciones para mostrar ficha nutricional y métricas corporales sin mezclar cuenta, rol y plan.

## Follow-up patches

Ver plan operativo en:

```text
docs/planning/onboarding_nutrition_profile_cycle.md
```


## Implementation closure

ONB00-ONB09 completed the v1 implementation of this decision. The current closure artifact is:

```text
docs/current/qa/onboarding_nutrition_v1_qa.md
```

Future work should not reopen ONB v1 directly. Persistent third-party profiles, generic body metrics, permanent defaults, allergies/intolerances and Program generation should be planned as separate cycles.
