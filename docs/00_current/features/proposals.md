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

Una comida solicitada sólo por energía —por ejemplo, 450 kcal— deriva internamente un
objetivo 30/50/20 de proteína, carbohidratos y grasa para poder optimizar; esa
distribución es una heurística explícita, no un dato atribuido al usuario. Un objetivo
parcial de macros se rechaza en vez de completar silenciosamente los valores restantes.
La prevalidación registra cuántos alimentos están visibles, cuántos son elegibles y
cuántos fueron excluidos por el gobierno del solver. Cero candidatos elegibles tiene
un código estable distinto de una solución matemáticamente inviable.

Para objetivos diarios, la energía y los porcentajes no se resuelven de forma
independiente del peso. La política vigente prioriza proteína por kg, acota la grasa y
asigna a carbohidratos la energía restante. Acepta 1,0–2,5 g/kg como rango ampliado y
señala 1,6–2,2 g/kg como rango preferente. Si el usuario entrega una distribución
completa —por ejemplo 30/50/20— el backend la convierte a gramos y comprueba el PPK
resultante; una combinación incompatible se rechaza con un diagnóstico estable, sin
sobrescribir silenciosamente ninguna instrucción. La distribución particular de una
comida es una restricción local y no redefine por sí sola el objetivo del día.

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

### Anatomía canónica del detalle web

El detalle de una propuesta usa la misma jerarquía visual para cualquier entidad
propuesta (`Meal`, `DailyPlan` o `Program`). El UI-system fija este orden:

1. cabecera de revisión con estado y **Requerimiento**;
2. objetivos o parámetros de validación, cuando existan;
3. trazabilidad y alternativas, cuando correspondan;
4. bloque **Adjuntos de la propuesta** con `.proposal-review-attachment`;
5. card UI-system de la entidad propuesta inmediatamente después del adjunto;
6. resultado aplicado y acciones de revisión.

La página de propuesta resume la entidad mediante su card. La navegación desde esa
card abre una página de detalle de solo lectura que reutiliza los componentes de la
biblioteca de la entidad. Los objetivos pertenecen al contexto de revisión de la
propuesta y no deben repetirse dentro del detalle navegable de la entidad. Esta regla
evita que `Program` tenga una anatomía distinta de `DailyPlan` o `Meal` y mantiene la
separación entre revisar la decisión y explorar su contenido.

## Relación con AI Nutrition Onboarding

El flujo de onboarding nutricional asistido por IA debe crear `NutritionProposal` antes de crear entidades finales.

Regla:

```text
Home AI Input → NutritionBrief → validación/generación → NutritionProposal → aprobación → entidad final
```

La IA no escribe directamente sobre Meals, DailyPlans o Programs. Cuando debe escoger
composición, cantidades o alternativas, crea una `NutritionProposal`. Cuando el usuario
ya definió un cambio exacto y acotado, prepara un workspace patch determinista. Ninguno
modifica la entidad durante la preparación: la aplicación segura ocurre únicamente
después de confirmación confiable y mediante commands de aplicación.
