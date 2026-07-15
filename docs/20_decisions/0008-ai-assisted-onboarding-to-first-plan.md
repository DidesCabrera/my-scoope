# 0008 · AI-assisted onboarding hacia el primer plan útil

## Estado

Aceptada.

## Fecha

2026-06-27

## Contexto

La experiencia actual de MyScoope permite construir Meals, DailyPlans y Programs con alto control, pero esa potencia puede ser demasiada fricción para un usuario regular.

Crear manualmente un DailyPlan exige entender alimentos, porciones, macros, estructura de comidas y navegación del sistema. Crear un Program semanal aumenta todavía más la carga. Esto puede afectar directamente la activación y la relación entre usuarios activos y usuarios totales.

La hipótesis de producto es que el usuario regular no quiere empezar construyendo. Quiere abrir la aplicación, explicar su objetivo en lenguaje natural y recibir una primera solución razonable, editable y confiable.

## Decisión

MyScoope debe evolucionar hacia un flujo de onboarding nutricional asistido por IA, iniciado desde Home con una entrada tipo:

```text
¿En qué puedo ayudarte?
```

Este flujo debe convertir lenguaje natural en un `NutritionBrief`, hacer preguntas mínimas para completar restricciones, generar una propuesta de `DailyPlan` y permitir que el usuario revise/apruebe antes de crear entidades finales.

La implementación debe respetar este principio:

```text
La IA conversa.
MyScoope calcula, valida y optimiza.
El usuario revisa y aprueba.
```

La IA no debe crear directamente DailyPlans o Programs productivos. La salida inicial debe ser una `NutritionProposal` validada por la capa de aplicación.

## Alcance inicial

El primer objetivo no es generar Programs completos.

El primer objetivo es reducir el tiempo hasta un primer `DailyPlan` útil aprobado.

Programs deben venir después, como composición de DailyPlans aprobados o generados bajo el mismo contrato.

## Consecuencias

- Home debe convertirse progresivamente en un punto de entrada de intención, no solo navegación.
- Se debe crear un flujo `AI Intake` o wizard conversacional guiado.
- Se debe modelar un `NutritionBrief` estructurado antes de generar planes.
- La generación debe pasar por `NutritionProposal` y no aplicar cambios directamente.
- La IA debe usarse para interpretar, preguntar y explicar; no como autoridad final de cálculo.
- Las reglas de macros, porciones, restricciones y validación deben vivir en servicios internos.
- La primera generación debe priorizar `DailyPlan`; `Program` queda para una etapa posterior.
- El flujo de IA debe usar alimentos operacionales disponibles como `notas.Food`; Food Catalog puede enriquecer esa disponibilidad solo mediante protocolos internos de snapshot/publicación previos.

## Roadmap aceptado

```text
1. Home AI Intake
2. NutritionBrief editable
3. DailyPlan Proposal Generator
4. Portion Solver / optimización
5. Program Generator
```

## Actualización Patch 41

El AI-assisted onboarding debe evolucionar dentro de la estructura de chat existente de My Scoope.

La integración con LLM externo no crea una UI paralela. Debe reutilizar `AiNutritionChat`, `ai_intake.html`, `_ai_chat_thread.html` y la lista de chats actual.

El LLM externo aporta naturalidad y comprensión, pero solo puede operar mediante tools permitidas. No accede a `food_catalog`, no escribe entidades directamente y no aplica cambios sin revisión/aprobación.

Ver también:

```text
docs/20_decisions/0019-external-llm-over-existing-chat.md
docs/00_current/features/ai_assistant/README.md
```

## Documento operativo

Ver:

```text
docs/00_current/features/ai_nutrition_onboarding/ai_nutrition_onboarding.md
```
