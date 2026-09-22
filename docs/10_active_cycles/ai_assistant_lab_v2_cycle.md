# AI Assistant Lab v2 and Outcome Quality Cycle

Status: repository implementation completed; staging calibration pending
Date: 2026-09-21
Owner: Product / AI Assistant / Nutrition
Branch: `feat/ai-assistant-lab-v2`

## Objective

Convertir el asistente técnicamente correcto en un operador útil dentro de My
Scoope, medido por resultados observables y no por prosa aislada. El modelo conserva
libertad conversacional; el producto conserva schemas, ownership, validación,
propuestas/patches y confirmación confiable.

## Completed repository stages

- `LV200` — Lab v2 separa dataset, fixtures, live trajectories, calidad humana,
  costo y diagnóstico.
- `LV201` — los doce escenarios built-in declaran un outcome verificable.
- `LV202` — 64 casos versionados cubren ocho familias de objetivo y surface de tools.
- `LV203` — `active_work.v1` conserva objetivo/recurso/acción y permite cambio de tema.
- `LV204` — el prompt v4 distingue consultas, propuestas y patches, y define parada.
- `LV205` — feedback owner-scoped por respuesta y reporte agregado sin contenido.
- `LV206` — comparación de modelos requiere todas las repeticiones y revisión humana;
  Luna/Terra se evalúan antes del benchmark Sol y Astra queda fuera.
- `LV207` — contratos, migración, UI, comandos y pruebas focalizadas incorporados.

## Local verification evidence

- puerta integral del repositorio: 2048/2048 pruebas;
- catálogo especializado del asistente: 146/146 pruebas;
- dataset determinista: 64/64 casos;
- preflight local: 12/12 escenarios listos con los usuarios de desarrollo 2 y 3;
- el usuario de desarrollo 1 queda correctamente bloqueado por el fixture
  `replacement_food_id`, sin clasificarlo como regresión del asistente;
- `ruff`, `git diff --check`, migraciones, OpenAPI y registro documental en verde.

## External closure gate

El código no declara victoria cualitativa por sí solo. El cierre operacional exige:

1. preparar fixtures reales en staging para los doce escenarios;
2. ejecutar al menos tres repeticiones con el baseline Luna;
3. completar el template humano para cada trayectoria;
4. corregir cualquier regresión dura o cualitativa;
5. comparar Terra sólo si Luna no supera el gate completo;
6. conservar el reporte final y verificar que la limpieza no alteró entidades finales.

## Success criteria

- 64/64 casos deterministas;
- 12/12 escenarios live listos y sin regresiones duras;
- `pass_all` por escenario en las repeticiones seleccionadas;
- cuatro criterios humanos aprobados por trayectoria;
- cero escrituras persistentes sin confirmación confiable;
- no aceptar un modelo por costo si pierde calidad o confiabilidad.
