# Proposals

## Estado

Feature vigente.

## Concepto

Las propuestas nutricionales permiten revisar, aprobar y aplicar entidades sugeridas por IA.

## Reglas

- La aplicación segura de propuestas debe vivir en application commands.
- Los payloads ricos deben validarse antes de crear entidades.
- Las vistas deben diferenciar revisión, aprobación y aplicación.
- Las acciones destructivas o irreversibles deben estar explícitas.

## Relación con AI Nutrition Onboarding

El flujo de onboarding nutricional asistido por IA debe crear `NutritionProposal` antes de crear entidades finales.

Regla:

```text
Home AI Input → NutritionBrief → validación/generación → NutritionProposal → aprobación → entidad final
```

La IA no debe aplicar cambios directos sobre Meals, DailyPlans o Programs. La aplicación segura debe seguir viviendo en commands de aplicación y debe validar payloads antes de crear entidades.

