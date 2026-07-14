# AI Nutrition Onboarding

## Estado

Implementación v1 completada en el ciclo ONB00–ONB09. ONB08 muestra y exige confirmar la advertencia de PPK antes de aplicar en la librería personal una propuesta calculada con datos externos/manuales. ONB09 agrega cierre QA y smoke coverage del flujo onboarding → ficha → sujeto nutricional → solver → warning.

Este documento define la dirección para convertir el inicio de MyScoope en una experiencia asistida por IA que lleve al usuario regular a su primer plan útil sin exigirle construir manualmente Meals, DailyPlans o Programs desde cero.

## Problema

El usuario avanzado puede valorar el constructor manual de planes, comidas y programas.

El usuario regular probablemente abandona si la primera tarea relevante es crear manualmente un DailyPlan y mucho más si debe crear un Program semanal. Ese flujo exige conocer el modelo de datos, entender macros, elegir alimentos, ajustar porciones y navegar varias pantallas antes de percibir valor.

La activación del producto debe moverse desde:

```text
"aprende a construir tu plan"
```

hacia:

```text
"cuéntame qué necesitas y te propongo un primer plan editable"
```

## Principio central

```text
La IA conversa.
MyScoope calcula, valida y optimiza.
El usuario revisa y aprueba.
```

La IA no debe ser la autoridad nutricional final ni escribir entidades productivas directamente.

La IA debe interpretar lenguaje natural, hacer preguntas, convertir preferencias en restricciones y explicar resultados. El sistema interno de MyScoope debe construir estructuras válidas, calcular macros, aplicar restricciones, validar tolerancias y crear propuestas revisables.

## Experiencia objetivo

En Home debe existir un punto de entrada principal tipo:

```text
¿En qué puedo ayudarte?
```

Ejemplos de solicitudes esperadas:

```text
Quiero una dieta para bajar grasa con comidas simples.
Hazme un plan de 2200 kcal.
No me gusta el pescado y quiero comer barato.
Entreno 3 veces por semana y quiero subir masa muscular.
Tengo pollo, arroz, huevos y avena.
Quiero una semana completa de comidas.
```

El sistema debe responder con un flujo guiado que capture lo faltante, no con un chat libre sin estructura.

## Flujo recomendado

```text
Home AI Input
  ↓
AI Intake / Conversation Wizard
  ↓
NutritionBrief estructurado
  ↓
Preguntas mínimas faltantes
  ↓
Resumen editable del brief
  ↓
Generador de DailyPlan
  ↓
Validación nutricional y de restricciones
  ↓
NutritionProposal
  ↓
Revisión/aprobación del usuario
  ↓
Creación de DailyPlan
```

Más adelante, el mismo flujo puede extenderse a Programs:

```text
DailyPlan útil y aprobado
  ↓
variaciones / repetición / distribución semanal
  ↓
NutritionProposal de Program
  ↓
aprobación
  ↓
Program
```

## Unidad inicial de generación

La primera unidad generada debe ser `DailyPlan`, no `Program`.

Motivos:

- DailyPlan es la unidad central y más fácil de validar.
- Program es una composición de días y agrega complejidad de variedad, promedios semanales y distribución.
- Resolver bien un DailyPlan permite reutilizar el motor para Programs más adelante.
- El objetivo inicial es reducir el tiempo hasta el primer plan útil, no resolver todo el journey nutricional en una sola versión.

## UserNutritionProfile y NutritionSubjectContext

La ficha personal y el sujeto de cálculo no son equivalentes.

```text
UserNutritionProfileDTO
  = datos persistidos de la ficha personal del usuario autenticado

NutritionSubjectContextDTO
  = persona/contexto concreto usado para calcular una propuesta
```

Reglas vigentes:

- `self_profile` usa ficha personal + actividad/frecuencia completada en chat.
- `external_chat_data` usa datos entregados para otra persona.
- `manual_chat_data` usa datos temporales de cálculo.
- Los sujetos externos no deben completar datos faltantes con la ficha del dueño de la cuenta.
- `requires_library_ppk_warning=True` cuando el sujeto no es `self_profile`.

Esto permite calcular kcal, macros y PPK con el sujeto correcto durante la propuesta, y advertir antes de guardar en la librería personal si el PPK visible será recalculado con el peso personal del dueño.

ONB06 aplica estas reglas en el intake determinístico:

- si el usuario dice que se use su ficha, se prefillean peso, altura, edad y sexo desde `UserNutritionProfile`;
- si el usuario entrega datos de otra persona, el brief queda marcado como `external_chat_data`;
- si el usuario entrega datos corporales sin asociarlos a la ficha, el brief queda como `manual_chat_data`;
- los datos externos/manuales activan `requires_library_ppk_warning`;
- los datos explícitos de chat ganan sobre defaults de la ficha para esa propuesta.

ONB07 aplica estas reglas al motor nutricional:

- `build_dailyplan_target_plan` vuelve a normalizar el brief contra el sujeto explícito antes de estimar targets;
- si el sujeto es `self_profile`, el solver usa la ficha persistida y el último `WeightLog`;
- si el sujeto es externo/manual, el solver usa el peso/altura/edad/sexo/actividad del chat;
- el PPK/proteína por kg se calcula con el peso del sujeto de cálculo;
- `targets`, `current_snapshot` y `validation_summary.generator` guardan un `subject_context` de auditoría.

ONB08 usa ese `subject_context` en la revisión de propuestas:

- si `requires_library_ppk_warning=True`, la UI muestra una advertencia explícita antes de aplicar;
- la advertencia explica que kcal y gramos de macros se conservan;
- la advertencia explica que PPK y otros indicadores dependientes de perfil se mostrarán con el peso actual de la ficha personal;
- el endpoint de aplicación exige una confirmación explícita para propuestas externas/manuales.


## QA closure

El cierre operativo de ONB v1 queda registrado en:

```text
docs/40_technical/qa/onboarding_nutrition_v1_qa.md
```

Ese documento resume los contratos estables, comandos de validación y cobertura de regresión mínima para futuros cambios en onboarding, Profile, AI Intake, NutritionSubjectContext, Solver o Proposal Review.

## NutritionBrief

El flujo debe construir un brief nutricional explícito antes de generar entidades.

Puede comenzar como DTO/JSON interno antes de convertirse en modelo persistente.

Campos sugeridos:

```text
subject_source                # self_profile | external_chat_data | manual_chat_data
ppk_weight_source
requires_library_ppk_warning
goal
requested_entity              # daily_plan | program
meals_per_day
calorie_target
protein_target
carb_target
fat_target
body_weight
training_frequency
preferred_foods
excluded_foods
style_preferences
complexity_level
budget_level
available_foods
notes
missing_fields
```

El brief debe poder mostrarse y editarse antes de generar el plan.

## Restricciones

### Restricciones duras

No deben romperse salvo confirmación explícita del usuario o imposibilidad técnica explicada.

- kcal objetivo;
- proteína mínima u objetivo;
- número de comidas;
- alimentos excluidos;
- alergias/intolerancias cuando existan;
- límites razonables de porción;
- alimentos disponibles si el usuario pide usar solo ciertos alimentos;
- requisitos explícitos del usuario.

### Restricciones blandas

Deben influir en la solución, pero pueden flexibilizarse.

- simpleza;
- bajo costo;
- variedad;
- repetición permitida;
- baja preparación;
- preferencia por alimentos específicos;
- distribución horaria;
- comidas dulces/saladas;
- cercanía cultural/regional.

La IA puede ayudar a traducir preferencias humanas a restricciones estructuradas. Ejemplo:

```json
{
  "style_preferences": ["simple"],
  "max_unique_foods": 10,
  "allow_repeated_meals": true,
  "low_prep": true
}
```

## Generación y validación

La generación no debe depender exclusivamente del modelo de lenguaje.

El generador inicial puede usar heurísticas:

```text
1. definir targets nutricionales;
2. distribuir kcal/macros por comida;
3. elegir templates de comidas;
4. seleccionar alimentos compatibles;
5. ajustar porciones;
6. validar kcal/macros/tolerancias;
7. crear NutritionProposal.
```

Una etapa posterior puede incorporar optimización matemática para ajustar porciones y combinaciones bajo restricciones.

## Relación con Proposals

La salida del flujo debe ser una `NutritionProposal`, no una entidad aplicada directamente.

Regla:

```text
AI-assisted onboarding genera propuestas.
Application commands validan y aplican propuestas aprobadas.
```

Esto conserva el patrón seguro existente:

```text
proponer → validar → revisar → aprobar → aplicar
```

## Relación con Food Catalog

El generador y el futuro LLM externo no deben consultar `food_catalog` directamente.

La generación asistida solo puede usar alimentos operacionales disponibles como `notas.Food`. Si un alimento maestro de Food Catalog todavía no fue materializado como snapshot operativo, entonces no existe para AI/MCP/Solver.

Relación esperada:

```text
Food Catalog App cura/publica alimentos maestros
  ↓
Protocolos internos materializan o actualizan notas.Food
  ↓
AI Nutrition Onboarding usa notas.Food mediante tools/servicios permitidos
  ↓
Nutrition Management App genera NutritionProposal revisable
```

No debe consultar ni persistir datos externos directamente desde el flujo de generación.

## Arquitectura sugerida

```text
services/
  ai_intake/
    parse_intent.py
    followup_questions.py
    build_brief.py
    schemas.py

  nutrition_generation/
    constraints.py
    dailyplan_generator.py
    meal_template_selector.py
    portion_solver.py
    validators.py

  proposals/
    create_proposal.py
    validate_proposal.py
    apply_proposal.py
```

Si se implementa dentro de `notas`, mantener la frontera conceptual:

```text
notas/services/ai_intake/...
notas/services/nutrition_generation/...
```

No poner parsing, optimización ni validación nutricional reusable dentro de views o templates.

## Métricas de éxito

La métrica principal debe ser:

```text
Tiempo hasta primer DailyPlan útil aprobado
```

Métricas complementarias:

- porcentaje de usuarios que envía el primer prompt;
- porcentaje que completa el brief;
- porcentaje que genera propuesta;
- porcentaje que aprueba propuesta;
- porcentaje que edita antes de aprobar;
- tasa de creación del segundo plan;
- usuarios que convierten DailyPlan en Program;
- retención al día siguiente;
- usuarios activos / usuarios totales.

## Roadmap incremental

### Etapa 1 — Home AI Intake

- Agregar input en Home.
- Crear endpoint de intake.
- Parsear intención a estructura.
- Detectar datos faltantes.
- Hacer preguntas mínimas de seguimiento.
- No crear planes todavía.

### Etapa 2 — NutritionBrief editable

- Construir brief estructurado.
- Mostrar resumen editable.
- Confirmar objetivo, comidas, preferencias y restricciones.
- Preparar payload validable para generación.

### Etapa 3 — DailyPlan Proposal Generator

- Generar primera propuesta de DailyPlan.
- Usar alimentos operacionales existentes (`notas.Food`) bajo contrato estable.
- Validar kcal/macros/tolerancias.
- Crear `NutritionProposal`.
- Reutilizar la vista segura de revisión/aprobación.

### Etapa 4 — Portion Solver / optimización

- Ajustar gramajes por solver o búsqueda heurística.
- Incorporar límites mínimos/máximos por alimento.
- Manejar tradeoffs entre restricciones duras y blandas.
- Explicar desviaciones.

### Etapa 5 — Program Generator

- Generar Programs desde DailyPlans aprobados.
- Manejar variedad/repetición.
- Validar promedios semanales.
- Crear propuestas de Program revisables.

## Criterio de implementación

No intentar implementar toda la visión en un solo cambio.

La primera versión exitosa es aquella donde un usuario puede escribir una solicitud simple, responder pocas preguntas, revisar un brief y terminar con una propuesta de DailyPlan suficientemente buena para aprobar o editar.

## Estado de implementación del motor nutricional

### Patch 12 — Validator nutricional estricto

Patch 12 consolida el paso de validación independiente del generador de DailyPlan.

El motor ahora distingue entre:

```text
ok       → propuesta dentro de tolerancias y restricciones esperadas
warning  → propuesta revisable, pero con desviaciones o porciones que requieren ajuste fino
error    → propuesta con incumplimientos duros que no deberían considerarse estables
```

La validación estricta queda ubicada en `notas/application/nutrition_engine/validators.py` y puede reutilizarse desde UI, logs, tests, MCP/API interna o futuros generadores. No depende de views, templates ni modelos Django.

Responsabilidades cubiertas:

- comparar kcal, proteína, carbohidratos y grasa contra targets diarios;
- medir diferencias absolutas y porcentuales;
- clasificar cada métrica como `ok`, `warning` o `error`;
- detectar cantidad de comidas distinta al brief;
- detectar uso de alimentos excluidos por el usuario;
- detectar porciones fuera de mínimos/máximos o porciones poco razonables;
- producir un resumen serializable para `NutritionProposal.validation_summary`.

El generador de DailyPlan conserva el flujo seguro:

```text
NutritionBrief
  ↓
Target Estimator
  ↓
Meal Templates
  ↓
Candidate Selector
  ↓
Portion Solver
  ↓
Payload create_dailyplan
  ↓
Simulation read-only
  ↓
Strict Nutrition Validator
  ↓
NutritionProposal pendiente de revisión
```

La propuesta sigue sin aplicarse automáticamente. La validación estricta solo informa el estado técnico/nutricional de la propuesta para revisión humana y para futuras herramientas IA/MCP.

### Patch 13 — Iteración estructurada de propuestas generadas

Patch 13 agrega una capa determinística de comandos de iteración para que el chat pueda pedir ajustes sobre una propuesta de DailyPlan ya generada sin mutar la versión anterior.

El flujo queda así:

```text
Mensaje del usuario
  ↓
Parser de comandos de iteración
  ↓
Actualización del NutritionBrief acumulado
  ↓
Nueva propuesta DailyPlan
  ↓
Validación nutricional estricta
  ↓
Nueva revisión trazable en NutritionProposal
```

Los comandos iniciales soportados cubren:

- subir o bajar proteína objetivo;
- subir o bajar calorías objetivo;
- aumentar o reducir cantidad de comidas;
- evitar alimentos mencionados (`sin arroz`, `menos arroz`, `no quiero atún`);
- preferir alimentos mencionados (`prefiero pollo`, `más quinoa`);
- reemplazos simples (`cambiar pescado por pollo`);
- estilo simple, económico o más variado.

La implementación queda separada en:

- `notas/application/ai_intake/iteration_commands.py`: parser y contrato serializable de comandos;
- `notas/application/ai_intake/nutrition_brief.py`: aplicación de comandos sobre el brief acumulado;
- `notas/application/ai_intake/plan_iteration.py`: creación de una nueva revisión de propuesta y metadata trazable.

Cada revisión guarda en `current_snapshot["iteration"]` y `validation_summary["chat_iteration"]`:

- `previous_proposal_id`;
- mensaje original del usuario;
- comandos estructurados;
- etiquetas humanas de comandos.

La propuesta anterior permanece intacta. El chat marca la nueva card como versión actual y conserva la versión anterior en historial.

### Patch 14 — Trazabilidad visible de iteraciones IA

Patch 14 expone la metadata generada por Patch 13 en superficies de revisión humana.

La trazabilidad deja de quedar solo como JSON técnico en `current_snapshot["iteration"]` / `validation_summary["chat_iteration"]` y pasa a tener una representación normalizada mediante `notas/application/ai_intake/iteration_trace.py`.

Superficies cubiertas:

- card de propuesta generada dentro del chat AI Nutrition;
- detalle enriquecido de `NutritionProposal`;
- viewmodels serializables para tests y futuras superficies API/MCP.

La UI muestra:

- mensaje original del usuario que gatilló la iteración;
- etiquetas humanas de comandos aplicados;
- referencia a la propuesta anterior cuando existe `previous_proposal_id`.

Esto mantiene la regla de seguridad central: cada ajuste crea una nueva propuesta revisable, sin mutar ni aplicar automáticamente versiones anteriores.

### Patch 15 — Preparar MCP/API del motor nutricional

Patch 15 integra el motor nutricional en el sistema MCP existente sin crear un servidor paralelo ni permitir mutaciones directas. La frontera se mantiene así:

```text
MCP protocol tool
  ↓
MCP dispatcher
  ↓
Myscoope API client
  ↓
/ai-tools/... API adapter interno
  ↓
Application tool
  ↓
NutritionBrief / DailyPlan Generator / Strict Validator
  ↓
NutritionProposal pendiente de revisión
```

Se agregan dos herramientas seguras:

- `create_nutrition_engine_dailyplan_proposal`: recibe un `NutritionBrief` estructurado y crea una propuesta de DailyPlan generada por el motor.
- `iterate_nutrition_engine_dailyplan_proposal`: recibe una propuesta anterior, un `NutritionBrief` actualizado y el mensaje original del usuario; crea una nueva revisión trazable sin mutar ni aplicar la anterior.

Ambas herramientas crean únicamente `NutritionProposal` revisables con `source=mcp`; no crean `DailyPlan` finales, no aprueban propuestas y no aplican cambios. Las herramientas de aplicación siguen explícitamente fuera del MCP.

El contrato API también expone campos útiles para clientes externos:

- `engine_validation`;
- `target_comparison`;
- `source_proposal`;
- `nutrition_brief`;
- `iteration_trace`.

Además, `read_proposal` y las listas de propuestas incorporan `iteration_trace` normalizado cuando la propuesta corresponde a una revisión de chat/feedback.

### Próximo patch recomendado

Patch 16 debería enfocarse en una de estas direcciones:

- comparación visual/API entre propuesta anterior y nueva revisión;
- contrato MCP para leer el estado completo de una cadena de revisiones;
- pruebas end-to-end MCP real contra el adapter interno con token de usuario.

## Patch 41 · External LLM sobre chat existente

La integración LLM externa debe evolucionar sobre la estructura actual de chat de My Scoope, no como una pantalla paralela.

Contrato de UI:

```text
AiNutritionChat
notas/templates/notas/ai_intake.html
notas/templates/notas/_ai_chat_thread.html
notas/templates/notas/ai_chats/list.html
```

Contrato de arquitectura:

```text
Chat UI existente
  -> ai_assistant.ChatEngine / AI Assistant Orchestrator
  -> LLM externo
  -> tools permitidas
  -> servicios internos
  -> NutritionProposal
```

El LLM puede interpretar, preguntar y explicar. No puede escribir entidades productivas directamente, calcular macros finales como fuente de verdad, acceder a Food Catalog ni aplicar cambios sin aprobación humana.

Ver:

```text
docs/00_current/features/ai_assistant/README.md
docs/20_decisions/0019-external-llm-over-existing-chat.md
docs/20_decisions/0020-ai-assistant-django-app-and-chat-engine.md
```


## Patch 42 · app AI Assistant y ChatEngine

El flujo actual de AI Intake sigue siendo el motor activo, pero desde Patch 42 se adapta al contrato `ChatEngine` definido en la app Django `ai_assistant`.

```text
notas/interface/views/ai_intake.py
  -> ai_assistant.application.chat_engines.ChatEngineRequest
  -> notas.application.ai_intake.chat_engine.DeterministicNutritionIntakeChatEngine
  -> notas.application.ai_intake.nutrition_brief.start_or_continue_conversation
```

Esto permite que un futuro motor LLM externo entre por la misma superficie de chat sin duplicar templates ni historial.

## Patch 43 · LLM provider gateway

Desde Patch 43 existe una capa de proveedor LLM dentro de `ai_assistant.infrastructure.providers`.

```text
LLMProviderRequest
  -> FakeLLMClient / OpenAIResponsesClient
  -> LLMProviderResponse
```

Este gateway prepara la integración externa, pero no cambia todavía el motor activo del chat de onboarding nutricional. La view sigue entrando por `DeterministicNutritionIntakeChatEngine` hasta que un patch posterior incorpore el orquestador LLM.

Reglas vigentes:

- el provider gateway no importa `food_catalog`;
- no escribe entidades operacionales;
- no crea ni aplica propuestas;
- no reenvía metadata interna al proveedor externo;
- falla de forma controlada si falta configuración.

Ver:

```text
docs/20_decisions/0021-llm-provider-gateway.md
docs/00_current/features/ai_assistant/README.md
```

## Actualización ONB00 — ficha personal y sujeto nutricional

El onboarding nutricional asistido debe distinguir entre dos momentos:

```text
onboarding inicial
  captura datos personales básicos

primer chat nutricional
  completa contexto operativo de la propuesta
```

### Datos capturados en onboarding

El onboarding inicial, conducido por `accounts`, debe capturar solo:

```text
birth_date
sex
height_cm
weight
```

La persistencia vive en `notas`:

- `Profile` conserva `birth_date`, `sex`, `height_cm`, `onboarding_completed_at` y `onboarding_version`;
- `WeightLog` conserva el peso inicial como métrica histórica;
- futuras queries/services de Body Metrics deben evitar que AI/Solver dependan directamente del modelo histórico de peso.

### Datos completados en el primer chat

El primer chat nutricional debe completar:

```text
activity_level
training_frequency
```

Las preferencias siguientes no se guardan como defaults persistentes en v1:

```text
goal
meals_per_day
complexity_level
budget_level
```

Deben mantenerse como contexto del chat o de la propuesta revisable.

### Sujeto nutricional explícito

Antes de calcular una propuesta, el Assistant debe preguntar o resolver si el plan se calcula con la ficha personal del usuario o con datos nuevos.

Tipos conceptuales:

```text
self_profile
external_chat_data
manual_chat_data
```

El solver debe calcular kcal, macros y PPK usando el sujeto nutricional de la propuesta, no el usuario autenticado de forma implícita.

### Propuestas para otra persona

Si el usuario entrega datos de otra persona, la propuesta se calcula con esos datos. Eso incluye PPK.

Si luego el usuario guarda la propuesta en su librería personal, My Scoope debe advertir que los indicadores dependientes del perfil, como PPK, se recalcularán usando el peso registrado en su ficha personal.

La advertencia debe dejar claro que las calorías y gramos de macros del plan no cambian.

Documento operativo del ciclo:

```text
docs/10_active_cycles/onboarding_nutrition_profile_cycle.md
```

Decisión registrada:

```text
docs/20_decisions/0050-onboarding-nutrition-profile-and-subject-context.md
```


## Onboarding nutricional mínimo y Profile

El ciclo ONB00-ONB04 activa una base previa al primer chat:

```text
accounts conduce el onboarding obligatorio.
notas.Profile guarda birth_date, sex, height_cm y estado de onboarding.
WeightLog guarda el peso como métrica corporal histórica.
Profile muestra la ficha por secciones para no mezclar cuenta, nutrición, métricas y contexto AI/Solver.
```

La vista Profile debe mantener separadas estas áreas:

- Cuenta: usuario, email, rol, plan y fecha de alta.
- Perfil nutricional: fecha de nacimiento, edad calculada, sexo nutricional, altura y versión de onboarding.
- Body Metrics: peso actual, fecha y origen del último registro.
- AI / Solver: datos que se completan en chat y regla de propuestas para terceros.

En v1, actualizar `birth_date`, `sex` y `height_cm` se hace desde la ficha nutricional. Actualizar peso sigue el flujo de Body Metrics y escribe `WeightLog`; no debe sobrescribir silenciosamente historial corporal.
