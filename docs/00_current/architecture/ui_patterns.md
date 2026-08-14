# UI Patterns

Este documento describe los patrones visuales vigentes de My Scoope.


## Contrato principal

El contrato visual vigente está en `docs/00_current/design/ui_system.md`.

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

### `entity-card`

Contrato estructural compartido para representar Food, Meal, DailyPlan, Program y entidades anidadas equivalentes.

```text
entity-card
  -> entity-card__main
     -> entity-card__title
     -> entity-card__kpi
  -> content-panel (opcional)
  -> entity-card__footer
     -> entity-card__metadata
     -> entity-card__actions
```

Variantes iniciales:

- `entity-card--food`
- `entity-card--meal`
- `entity-card--dailyplan`
- `entity-card--program`
- `entity-card--nested`
- `entity-card--program-week`

Las clases `card`, `card-main`, `card-kpi`, `card-bottom`, `card-metadata` y `card-actions` permanecen como aliases legacy durante la migración.

### `child-card`

Usar para representar entidades relacionadas dentro de una lista, detail o sección compuesta.

`child-card` describe el rol contextual. La estructura visual debe consumir `entity-card`; no constituye un sistema de card paralelo.

## Secciones de detail

### `detail-section-header`

Usar para el encabezado de una sección interna de detail: entidades relacionadas, información nutricional, días, semanas o agregaciones.

### `detail-section-heading`

Agrupa icono y título dentro del header. Las clases históricas `dailyplan-detail__children-header` y `home-section-title detail-dp` permanecen como aliases/contexto hasta completar la migración.

Programs y Program Week consumen estos mismos componentes. Sus clases específicas controlan únicamente composición y comportamiento.

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

La estructura neutral es:

```text
panel-tabs
  -> panel-tab
```

Las clases históricas `card-detail-tabs`, `btn-desplegar` y sus variantes mobile continúan como aliases de compatibilidad durante la migración.

Programs no define un contrato visual alternativo: week tabs y chart tabs usan el mismo `panel-tab`; sus clases `program-*` expresan únicamente scroll, tamaño o comportamiento del dominio.

## Paneles de contenido

### `content-panel`

Usar como superficie neutral para contenido estructurado dentro de una card o detail:

- tablas nutricionales de Meals y DailyPlans;
- agregación de alimentos;
- paneles de semanas y días;
- gráficos de Programs;
- comparadores y otras superficies equivalentes cuando sean migrados.

La variante `content-panel--main` corresponde a paneles principales dentro de un detail. `card-detail-block` y `main` se mantienen temporalmente como aliases legacy.

Una clase de feature puede controlar el layout interno, pero no debe redefinir el fondo, borde o radio base del panel.

## Anatomías neutrales

- `entity-heading` organiza título, indicadores y aside de cards/details, también en Programs.
- `collection-page` y `collection-empty-state` organizan bibliotecas y sus estados vacíos.
- `message-card` organiza Proposal, Inbox y Chat; sus clases de feature solo expresan estado y contenido.

Las clases legacy permanecen como aliases durante la migración. Una nueva entidad debe comenzar por el nombre neutral.

La carga de CSS exclusivo debe usar `feature_css`. Programs ya aplica esta regla: `programs.css` solo se carga en sus páginas y `program_week_tabs.css` únicamente donde existen tabs de semanas.

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

Los estilos nuevos deben usar tokens semánticos generados desde
`design/ui-contract.json`. `tokens.css` mantiene compatibilidad histórica y
`ui-contract.generated.css`, cargado después, fija el contrato vigente.

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
