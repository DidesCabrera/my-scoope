# Onboarding Nutrition Profile Cycle

Status: completed
Date: 2026-07-03
Activated: 2026-07-03
Last updated: 2026-07-03 — ONB09 closed the cycle with QA docs and regression smoke coverage.

## Contexto

Durante la implementación de `ai_assistant` y `nutrition_solver` se hizo explícito que para estimar consumo calórico diario y macros iniciales se requieren datos corporales y de contexto como peso, edad, sexo nutricional, altura y actividad física.

Hasta ahora, parte de esos datos podía solicitarse directamente en el chat. Ese enfoque funciona para prototipo, pero aumenta fricción y hace que el Assistant repita preguntas que deberían formar parte de una ficha personal básica.

El nuevo ciclo define un onboarding nutricional mínimo, conducido por `accounts`, persistido por `notas` y consumido por `ai_assistant` / `nutrition_solver` mediante contratos explícitos.

## Tesis del ciclo

```text
El onboarding captura datos personales estables.
El primer chat completa datos operativos del contexto actual.
El solver calcula para un sujeto nutricional explícito.
La librería personal recalcula indicadores dependientes del perfil del dueño.
```

La ficha del usuario debe ser el contexto por defecto, pero no debe asumirse que toda propuesta nutricional se calcula necesariamente para el dueño de la cuenta.

My Scoope debe permitir:

- crear una propuesta para el usuario autenticado;
- crear una propuesta para otra persona;
- crear una propuesta modelo o temporal;
- guardar en librería personal con advertencias cuando corresponda.

## Responsabilidades por app

### `accounts`

`accounts` conduce el flujo de onboarding:

- bienvenida inicial;
- explicación del sistema;
- formulario nutricional básico;
- gate post-login para usuarios sin onboarding completo.

`accounts` no debe convertirse en dueño de la ficha nutricional operativa.

### `notas`

`notas` persiste la ficha personal y las métricas corporales operativas:

- `Profile` como ficha personal del usuario;
- `WeightLog` como métrica histórica de peso;
- futuros servicios/read models de Body Metrics;
- vistas de Profile y edición de datos persistentes.

### `ai_assistant`

`ai_assistant` conversa, decide el sujeto nutricional de una propuesta y completa datos faltantes:

- puede usar la ficha personal;
- puede pedir datos nuevos para otra persona;
- mantiene preferencias contextuales en sesión/chat;
- no debe escribir entidades finales sin Proposal Review.

### `nutrition_solver`

`nutrition_solver` calcula sobre un contexto explícito:

- no asume que el sujeto nutricional es el usuario autenticado;
- recibe peso, edad, sexo, altura, actividad y restricciones mediante contratos;
- calcula targets, macros, diagnósticos y PPK usando el sujeto de cálculo.

## Datos por etapa

### Onboarding inicial

El onboarding solo captura datos personales básicos y relativamente estables:

```text
birth_date
sex
height_cm
weight
onboarding_completed_at
onboarding_version
```

Reglas:

- `birth_date` se usa para calcular edad dinámicamente.
- `sex` representa el dato requerido por fórmulas nutricionales, no un sistema amplio de identidad.
- `height_cm` se guarda como dato corporal estable.
- `weight` se registra como métrica corporal histórica inicial.
- `onboarding_completed_at` marca que el usuario terminó el flujo obligatorio.
- `onboarding_version` permite evolucionar el onboarding en ciclos futuros.

### Primer chat nutricional

El primer chat completa datos más contextuales:

```text
activity_level
training_frequency
```

Estos datos pueden variar con la etapa del usuario, por lo que v1 no los persiste como defaults permanentes.

### Sesión o contexto de chat

Las siguientes preferencias no se persisten como ficha personal en v1:

```text
default_goal
default_meals_per_day
default_complexity_level
default_budget_level
```

Deben mantenerse como contexto de conversación/propuesta. Pueden convertirse en preferencias persistentes en un ciclo posterior, cuando exista evidencia de que son defaults reales del usuario.

## Body Metrics

`WeightLog` existe actualmente como registro histórico de peso. Para evitar que el peso parezca una excepción conceptual, este ciclo debe introducir una capa de Body Metrics.

En v1 se conserva `WeightLog`, pero se encapsula su lectura/escritura mediante servicios o queries:

```text
record_weight(user, weight_kg, source)
get_current_weight(user)
get_basic_body_profile(user)
```

La normalización completa hacia un modelo genérico como `UserMetricLog` queda diferida para una v2. El objetivo v1 es reducir acoplamiento y confusión sin introducir una migración amplia innecesaria.

## Implementation progress

```text
ONB00 — Docs and cycle decision: completed
ONB01 — Profile + Body Metrics base: completed
ONB02 — Onboarding UI: completed
ONB03 — Gate post-login: completed
ONB04 — Refactor Profile by sections: completed
ONB05 — UserNutritionProfile + NutritionSubjectContext: completed
ONB06 — AI Assistant decides nutrition subject: completed
ONB07 — Nutrition Solver uses subject context: completed
ONB08 — External subject library warning: completed
ONB09 — QA + closure docs: completed
```

ONB02 adds the authenticated `/accounts/onboarding/` route, renders three welcome/explanation slides and closes with the v1 basic nutrition form. Submitting the form updates `Profile`, records the initial `WeightLog` with `source=onboarding`, marks `onboarding_completed_at` and redirects to the app Home.


ONB03 adds `accounts.middleware.NutritionOnboardingRequiredMiddleware` to the global middleware stack. Authenticated non-staff users who have not completed `onboarding_version=1` are redirected to `/accounts/onboarding/` before entering the main app. The gate allows auth, admin, static/media, OAuth and well-known routes so login/logout/social auth and operational endpoints do not loop.


ONB04 refactors the user Profile screen into explicit sections: Account, Nutrition Profile, Body Metrics and AI/Solver Context. It exposes the persisted onboarding data, current weight source/date and the v1 rule that activity/training are completed in chat. It also adds a safe Profile nutrition update action for stable fields (`birth_date`, `sex`, `height_cm`) while keeping weight changes in the Body Metrics flow through `WeightLog`.


ONB05 adds an explicit read-model boundary for nutrition calculation subjects. `UserNutritionProfileDTO` represents the persisted personal ficha owned by the authenticated user. `NutritionSubjectContextDTO` represents the concrete person/context used to calculate a proposal. This keeps the system from assuming that every generated diet is for the account owner.

ONB05 also introduces `notas.application.queries.user_nutrition_profile` with:

```text
get_user_nutrition_profile(user)
build_nutrition_subject_context(user, source, chat_context)
```

The self-profile subject uses persisted body data plus activity/training from chat. External/manual subjects use chat-provided body data and must not silently fall back to the account owner's body data. External subjects mark `requires_library_ppk_warning=True` so a later save/apply flow can warn that library PPK may be recalculated with the owner's current profile weight.

ONB06 extends the deterministic AI Nutrition Intake brief with explicit subject metadata:

```text
subject_source
ppk_weight_source
requires_library_ppk_warning
```

The chat now asks whether to use the user's personal ficha or new data when the subject is ambiguous. If the user chooses the personal ficha, onboarding body basics are used as defaults and `activity_level` / `training_frequency` still come from chat. If the user provides external/manual body data, the proposal brief uses those values for calculation and PPK without falling back to the account owner's profile.

ONB07 connects that brief metadata to the concrete DailyPlan generator and Target Estimator. Before estimating kcal/macros, the generator re-applies `apply_subject_context(brief, user=user)` so `self_profile` is refreshed from `Profile` + latest `WeightLog`, while external/manual subjects keep their chat-provided data. The resulting `target_plan.as_targets_dict()` now includes a `subject_context` snapshot with calculation weight, PPK weight source and the future library warning flag. Generated proposal `current_snapshot` and `validation_summary.generator` also store the same subject snapshot for auditability.

ONB08 turns that snapshot into a safe application guard. Approved proposals calculated with external/manual subject data now show a warning before applying into the user's library, explaining that kcal and macro grams are preserved but profile-dependent indicators such as PPK will be displayed with the owner's current personal weight. The apply endpoint also requires explicit acknowledgement for those proposals so the warning is not merely decorative.

## Onboarding UI

La experiencia inicial debe tener tres vistas deslizables de bienvenida y explicación, seguidas por el formulario.

```text
Slide 1 — Bienvenida a My Scoope
Slide 2 — Librerías, planes y estructura nutricional
Slide 3 — AI Assistant, propuestas revisables y control humano
Formulario — Datos básicos del usuario
```

El formulario final captura:

```text
fecha de nacimiento
sexo nutricional
altura
peso actual
```

Al completar el formulario:

```text
Profile queda actualizado.
WeightLog registra el peso inicial.
onboarding_completed_at se define.
onboarding_version se fija en 1.
El usuario es redirigido al Home o al primer flujo asistido vigente.
```

## Sujeto nutricional de una propuesta

Antes de calcular una propuesta nutricional, el Assistant debe determinar si el plan es para la ficha personal o para otra persona.

Tipos conceptuales:

```text
self_profile
external_chat_data
manual_chat_data
```

La pregunta base debe ser equivalente a:

```text
¿Usamos los datos de tu ficha personal o quieres entregar datos nuevos para esta propuesta?
```

Si el usuario usa su ficha:

```text
NutritionSubjectContext.source = self_profile
```

Si el usuario entrega otros datos:

```text
NutritionSubjectContext.source = external_chat_data
```

El solver debe calcular kcal, macros y PPK con el peso del sujeto nutricional de la propuesta, no necesariamente con el peso del dueño de la cuenta.

## PPK y guardado en librería

Durante la propuesta, PPK se calcula con el peso del sujeto nutricional usado en el cálculo.

Ejemplo:

```text
Usuario dueño de la cuenta: 88 kg
Persona externa: 70 kg
Proteína propuesta: 140 g
PPK de la propuesta: 2.0 g/kg
```

Si una propuesta calculada con datos externos se guarda en la librería personal del usuario, My Scoope debe advertir que los indicadores dependientes del perfil, como PPK, se recalcularán usando el peso registrado en la ficha personal.

Regla:

```text
Si NutritionSubjectContext.source != self_profile,
mostrar advertencia antes de guardar/aplicar la propuesta en la librería.
```

El warning debe aclarar:

- kcal y gramos de macros del plan no cambian;
- PPK visible en la librería puede cambiar;
- la causa es que la librería personal usa el peso de la ficha del dueño.

## Metadata de cálculo

Para trazabilidad, las propuestas generadas por AI/Solver deberían poder conservar metadata del sujeto usado en el cálculo.

Campos conceptuales:

```text
subject_source
calculation_weight_kg
calculation_height_cm
calculation_age_years
calculation_sex
calculation_activity_level
calculation_training_frequency
```

Esto no significa crear perfiles para terceros. Solo permite explicar cómo fue calculada una propuesta revisable.

## Profile UI

La vista de Profile debe refactorizarse por secciones antes o durante la exposición de los nuevos datos.

Secciones mínimas:

```text
Cuenta
Perfil nutricional
Métricas corporales
Contexto AI / Solver
```

Reglas:

- el peso actual se obtiene desde el último `WeightLog`;
- registrar un peso nuevo crea un nuevo log, no sobrescribe historial;
- la ficha personal debe explicar que puede usarse como contexto por defecto;
- la UI debe aclarar que también es posible crear propuestas para otra persona entregando datos nuevos en el chat.

## Ciclo de patches

### ONB00 — Docs: decisión y ciclo definitivo

Registra el ciclo, decisiones de arquitectura, sujeto nutricional, PPK y warning de guardado externo. No cambia código productivo.

### ONB01 — Profile + Body Metrics base

Implementation status: prepared in ONB01.

Agrega a `Profile`:

```text
birth_date
sex
height_cm
onboarding_completed_at
onboarding_version
```

Conserva `WeightLog`, agrega `source` para distinguir origen de la métrica y crea servicios de Body Metrics para lectura/escritura de peso actual.

La capa base queda ubicada en `notas.application.services.nutrition.body_metrics` para no crear todavía un nuevo bounded context de aplicación.

### ONB02 — Onboarding UI: slides + formulario

Implementa el flujo en `accounts` con tres slides de bienvenida y formulario final.

Guarda ficha básica y peso inicial.

### ONB03 — Gate post-login

Redirige usuarios autenticados sin onboarding completo hacia `/accounts/onboarding/`, evitando loops y sin bloquear admin, logout, static/media ni rutas necesarias de allauth.

### ONB04 — Refactor Profile por secciones

Reordena Profile en secciones claras y expone ficha nutricional, métricas corporales y contexto AI/Solver.

### ONB05 — UserNutritionProfile + NutritionSubjectContext

Crea read models/DTOs explícitos:

```text
UserNutritionProfile
NutritionSubjectContext
```

`UserNutritionProfile` representa la ficha personal persistida.

`NutritionSubjectContext` representa el sujeto usado para calcular una propuesta específica.

### ONB06 — AI Assistant decide sujeto nutricional

El Assistant pregunta si usa la ficha personal o datos nuevos. Si faltan datos para el sujeto elegido, pregunta solo lo necesario.

Las preferencias `goal`, `meals_per_day`, `complexity_level` y `budget_level` quedan en contexto de chat/propuesta.

### ONB07 — Nutrition Solver usa Subject Context

El solver calcula targets, macros y PPK usando el sujeto explícito del brief. `build_dailyplan_target_plan` normaliza el brief con `apply_subject_context`, pasa la metadata al `TargetEstimationProfile` y conserva un snapshot de sujeto en targets, current snapshot y validation summary.

### ONB08 — Warning al guardar propuesta externa

Completado. Si la propuesta fue calculada con datos externos/manuales, la pantalla de revisión muestra una advertencia antes de aplicar en la librería personal. La acción de aplicar exige confirmar que el usuario entiende que los indicadores dependientes de perfil, como PPK, se recalcularán con el peso de su ficha personal.

### ONB09 — QA + docs de cierre

Completado. Agrega `accounts.tests.test_onboarding_nutrition_cycle_closure` como smoke test del ciclo completo y publica `docs/current/qa/onboarding_nutrition_v1_qa.md` como cierre operativo. El ciclo ONB v1 queda cerrado; los siguientes trabajos sobre clientes persistentes, métricas genéricas, preferencias permanentes o Program generation deben planificarse como ciclos nuevos.

## Criterio de cierre

El ciclo se considera cerrado cuando se pueda afirmar:

```text
My Scoope tiene onboarding nutricional mínimo.
El usuario registra birth_date, sex, height y weight al comenzar.
El peso queda como métrica histórica.
Profile muestra la ficha por secciones.
AI Assistant pregunta si la propuesta usa ficha personal o datos nuevos.
AI Assistant completa activity_level y training_frequency en el primer chat.
Nutrition Solver calcula sobre un NutritionSubjectContext explícito.
PPK se calcula con el peso del sujeto durante la propuesta.
Al guardar propuestas externas, My Scoope advierte que PPK se recalculará con el peso de la ficha personal.
```

## Fuera de alcance de v1

No se implementa todavía:

- perfiles persistentes para clientes o terceros;
- modelo genérico `UserMetricLog`;
- alergias/intolerancias persistentes;
- preferencias permanentes de goal, meals, complexity o budget;
- horarios de comida;
- wearables;
- multi-tenant profesional.

Estos puntos pueden planificarse después de validar el flujo mínimo.
