# 0006 - UI System Stage 2 Component Consolidation

Status: accepted
Date: 2026-06-26

## Context

Después de declarar el contrato de UI System en Etapa 1, el siguiente riesgo era seguir copiando HTML entre entidades para resolver paneles visualmente equivalentes.

Los paneles de reordenar y eliminar en listas ya existían para Foods, Meals, DailyPlans, Programs, Proposals e Inbox. La estructura visual era casi idéntica, pero cada template contenía su propia versión de la fila, icono, checkbox, drag handle, formulario y título.

## Decision

Se inicia la Etapa 2 consolidando la parte repetida de los paneles de lista.

Se agregan parciales compartidos:

```text
notas/templates/components/list_panel_reorder_row.html
notas/templates/components/list_panel_delete_row.html
```

Los templates por entidad se mantienen como wrappers delgados porque todavía concentran configuración específica: URL de reordenamiento, URL de retorno, acción de eliminación, icono, clase de entidad, título y texto vacío.

## Consequences

- La UI visual no cambia.
- Los futuros paneles de reordenar/eliminar deben reutilizar estos parciales.
- La duplicación de filas se reduce sin introducir un viewmodel nuevo ni cambiar contratos de views.
- La consolidación sigue siendo segura: si una entidad necesita una excepción, se expresa en su wrapper sin contaminar el parcial compartido.
- La siguiente consolidación candidata son cards y acciones repetidas, no una división agresiva de `programs.css`.
