# 0016 · Endurecimiento de frontera MCP / alimentos operativos

## Estado

Aceptada.

## Fecha

2026-06-30.

## Contexto

Las decisiones `0009`, `0010` y `0013` definieron que Food Catalog es fuente maestra interna, mientras que `notas.Food` es la única verdad nutricional operacional.

Después de introducir modelos maestros, comandos de importación y el protocolo interno de snapshot, aparece un riesgo nuevo: que por compatibilidad histórica el nombre `list_food_catalog` sea interpretado como acceso real al catálogo maestro.

Ese nombre debe mantenerse por ahora para no romper el contrato MCP/API, pero su semántica debe quedar cerrada por tests y documentación.

## Decisión

El Patch 38 endurece la frontera MCP / alimentos:

```text
MCP -> list_food_catalog -> Django API Adapter -> notas.Food
MCP -X-> food_catalog.CatalogFood
MCP -X-> catalog_food_id
MCP -X-> snapshot commands
```

`list_food_catalog` queda definido como nombre histórico para listar alimentos operativos disponibles para planificación. Sus respuestas deben contener `food_id`, donde `food_id` significa exclusivamente `notas.Food.id`.

No debe aceptar ni devolver campos de trazabilidad del catálogo maestro como identificadores operativos.

## Reglas ejecutables

- El paquete `mcp_server/myscoope_mcp` no puede importar `food_catalog`.
- El paquete MCP no puede referenciar identificadores maestros como `CatalogFood`, `catalog_food_id` o comandos de snapshot.
- La tool `list_food_catalog` solo reenvía `search` y `limit` hacia el API Adapter.
- Argumentos extra como `catalog_food_id` o `catalog_food_ref` se ignoran en MCP y nunca se reenvían.
- El contrato de respuesta para planificación expone solo `food_id` operacional.

## Consecuencias

- El MCP conserva compatibilidad con el nombre `list_food_catalog`.
- La semántica queda corregida: no es acceso al catálogo maestro.
- Los protocolos de actualización desde Food Catalog permanecen internos al backend.
- Cualquier alimento maestro debe materializarse antes como `notas.Food` para aparecer en MCP.

## Relación con decisiones previas

Complementa y endurece:

```text
docs/decisions/0009-food-catalog-hybrid-source-snapshot.md
docs/decisions/0010-mcp-operational-food-boundary.md
docs/decisions/0013-operational-food-snapshot-protocol.md
```
