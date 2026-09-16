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
- Una propuesta generada por el solver puede contener un portafolio de alternativas
  confiables. Cambiar la alternativa seleccionada sólo reemplaza el payload pendiente,
  vuelve a validarlo/simularlo y no aprueba ni aplica la propuesta.

## Portafolio del solver

`portfolio_v1` solicita tres alternativas distintas por defecto. Todas viven en el
snapshot de la misma propuesta, con resultado matemático, calidad nutricional y
calidad funcional. Proposal Review muestra sus métricas y permite seleccionar una
antes de aprobar. El cliente envía únicamente `alternative_id`; el servidor obtiene
el payload desde su snapshot para impedir payloads alternativos manipulados.

## Superficie de usuario

La lista de propuestas es la subsección **Propuestas** de **Asistente AI**, junto
al tab **Chats**, tanto en web como en móvil. La ruta de propuestas y sus vistas
de detalle siguen siendo independientes; esta agrupación no altera ownership,
permisos, estados ni el ciclo de revisión. Las opciones de cabecera de esta
subsección deben corresponder únicamente a propuestas.

En la lista unificada, los contadores viven dentro de los tabs y el bloque de
créditos junto a los tabs permanece visible al hacer scroll. En móvil, cambiar
entre Chats y Propuestas alterna el contenido dentro de la misma pantalla, sin
animación de navegación.

## Relación con AI Nutrition Onboarding

El flujo de onboarding nutricional asistido por IA debe crear `NutritionProposal` antes de crear entidades finales.

Regla:

```text
Home AI Input → NutritionBrief → validación/generación → NutritionProposal → aprobación → entidad final
```

La IA no debe aplicar cambios directos sobre Meals, DailyPlans o Programs. La aplicación segura debe seguir viviendo en commands de aplicación y debe validar payloads antes de crear entidades.
