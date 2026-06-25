# UI Patterns

Este documento describe los patrones visuales vigentes de My Scoope.

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
