# UI Patterns

Este documento describe los patrones visuales vigentes de My Scoope.


## Contrato principal

El contrato visual vigente está en `docs/current/design/ui_system.md`.

Este archivo describe patrones de uso frecuentes. Si hay duda entre una solución local y el contrato del UI System, gana el contrato del UI System.

## Principio

No crear un componente visual nuevo si existe un patrón reutilizable.

La UI debe parecer consistente entre Foods, Meals, DailyPlans, Programs, Inbox, Proposals y Comparators.

## Headers

### `list-page-header`

Usar para páginas de lista o secciones principales.

Ejemplos:

- listas de entidades;
- comparadores normales;
- bandejas/secciones de herramientas.

### `card-title-comp`

Usar para details internos o entidades guardadas donde no corresponde repetir `list-page-header`.

Ejemplos:

- detail de una comparación guardada;
- detail de entidad;
- tarjetas principales de detalle.

## Indicadores

### `structural-indicator`

Usar para conteos o resumen estructural bajo un título.

Ejemplos:

- número de alimentos;
- número de comidas;
- número de semanas;
- número de adjuntos.

## Botones y acciones

### `data-grid-edit-actions__button`

Usar para acciones principales de edición o guardado dentro de paneles.

Ejemplos:

- guardar cambios;
- comparar;
- guardar comparación;
- editar comparación.

### Acciones destructivas

Usar icono `trash-2` para eliminar.

Las acciones destructivas deben estar visibles solo cuando el contexto permita ejecutarlas.

## Cards

### `child-card`

Usar para representar entidades relacionadas dentro de una lista, detail o sección compuesta.

## Paneles de lista

### `list-panel`

Usar para vistas auxiliares de listas donde el usuario reordena o elimina entidades.

El wrapper puede seguir siendo específico por entidad para conservar URLs y textos, pero la fila debe reutilizar los parciales compartidos:

```text
components/list_panel_reorder_row.html
components/list_panel_delete_row.html
```

Esto evita que Foods, Meals, DailyPlans, Programs, Proposals e Inbox tengan versiones divergentes de la misma UI.

## Tabs

Usar tabs existentes cuando una sección tenga vistas hermanas del mismo nivel conceptual.

Ejemplos:

- Comparadores: alimentos, comidas, planes.
- Comparaciones guardadas: alimentos, comidas, planes.

No usar tabs en details que representan una instancia específica si no hay vistas hermanas relevantes.

## CSS

Crear CSS nuevo solo si:

1. no existe un patrón reutilizable;
2. el comportamiento visual es propio de la feature;
3. se usa una variante acotada y nombrada de forma consistente.

Preferir BEM:

```css
.block
.block__element
.block--variant
.block__element--state
```


## Tokens y cascada

Los estilos nuevos deben usar tokens semánticos de `tokens.css`.

Priorizar:

- `--surface-*` para fondos;
- `--text-*` para texto;
- `--border-*` para bordes;
- `--interactive-*` para hover, active y acciones;
- `--entity-*` para colores de entidades;
- `--nutrition-*` para métricas nutricionales;
- `--z-*` para capas globales.

Evitar agregar colores directos, z-index numéricos globales o `!important` nuevos salvo excepción justificada.

## Breakpoints

Usar los breakpoints oficiales:

- `max-width: 768px` para contenido mobile;
- `max-width: 980px` para shell compacto, sidebar/header y tablet/PWA;
- `min-width: 981px` para desktop.

## Programas

`programs.css` es una feature con deuda conocida. Nuevos estilos dentro de ese archivo deben usar prefijos `program-` o `program-chart-` y no deben crear reglas genéricas reutilizables por otras features.
