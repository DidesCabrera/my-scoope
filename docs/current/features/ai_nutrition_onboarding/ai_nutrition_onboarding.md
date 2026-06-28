# AI Nutrition Onboarding

## Estado

Decisión vigente de producto/arquitectura. No implementado todavía.

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

## NutritionBrief

El flujo debe construir un brief nutricional explícito antes de generar entidades.

Puede comenzar como DTO/JSON interno antes de convertirse en modelo persistente.

Campos sugeridos:

```text
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

El generador solo debe usar alimentos canónicos publicados o alimentos privados del usuario bajo contrato estable.

No debe consultar ni persistir datos externos directamente desde el flujo de generación.

Relación esperada:

```text
Food Catalog App publica alimentos confiables
  ↓
AI Nutrition Onboarding selecciona candidatos compatibles
  ↓
Nutrition Management App genera Meals/DailyPlans/Programs
```

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
- Usar Food Catalog / foods existentes bajo contrato estable.
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
