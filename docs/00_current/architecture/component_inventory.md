# Component Inventory

Inventario de patrones UI vigentes para crear o modificar secciones.

Este documento complementa el contrato principal: `docs/00_current/design/ui_system.md`.

## Regla de uso

Antes de crear un nuevo componente, revisar si el caso puede resolverse con uno de estos patrones o con una variante acotada.

## Componentes compartidos

| Patrón | Capa | Usar para | Variantes/Notas |
|---|---|---|---|
| `list-page-header` | component | encabezados de listas/secciones | no usar en details internos si corresponde `card-title-comp` |
| `list-panel` | component | paneles de lista para reordenar/eliminar | usar parciales `list_panel_reorder_row.html` y `list_panel_delete_row.html` para filas repetidas |
| `card-title-comp` | component | encabezado interno de details | útil para detail de comparación guardada, detail de entidad o tarjetas principales |
| `structural-indicator` | component | conteos/resumen bajo títulos | número de alimentos, comidas, semanas, adjuntos |
| `child-card` | component | entidades relacionadas dentro de listas/details | Meals, DailyPlans, attachments, proposals |
| `card-main` | component | cuerpo principal de una entidad | mantener layout y acciones consistentes entre entidades |
| `card-bottom` | component | metadata/acciones inferiores | evitar crear footers nuevos si aplica |
| `panel-tabs` | component | vistas hermanas del mismo nivel | no usar como navegación profunda |
| `data-grid` | component | tablas y paneles estructurados | usar variantes para nutrición, menú, reorder, delete o edit |
| `data-grid-edit-actions` | component | grupos de acciones de edición | mantener estilo consistente de botones internos |
| `data-grid-edit-actions__button` | primitive/component | botones guardar/comparar/editar | preferir variantes existentes |
| `actions-row` | primitive/component | acciones de formularios/pickers | mantener alineación y espaciado del sistema |
| `dash-kpi` | component | KPIs de dashboards | métricas principales por entidad o detalle |
| `dash-kpi-range` | component | rangos min/max | usado en Program detail/list/chart summaries |
| `alloc-bar` | component | distribución P/C/F | usar tokens nutricionales |
| `overflow-menu` | primitive | menú contextual de cards/headers | z-index mediante `--z-dropdown` |
| `picker-list` | component | listas de selección | no mezclar reglas propias de Food Picker si el patrón es genérico |

## Features con estilos propios

| Feature | Archivo | Contrato |
|---|---|---|
| Home | `home.css` | estilos exclusivos de Home |
| Profile | `profile.css` | estilos exclusivos de Profile |
| Proposals | `proposals.css` | estilos de revisión/propuestas; no redefinir cards globales |
| Comparators | `comparators.css` | estilos de comparación y comparaciones guardadas |
| Programs | `programs.css` | estilos exclusivos con prefijo `program-` o `program-chart-`; no agregar reglas genéricas |

## Componentes consolidados

### `list-panel`

Los paneles de reordenar/eliminar en listas mantienen un wrapper por entidad, porque cada entidad define sus URLs y textos, pero las filas repetidas viven en parciales compartidos:

| Parcial | Uso | Recibe |
|---|---|---|
| `components/list_panel_reorder_row.html` | fila arrastrable de reordenamiento | `item_id`, `item_title`, `icon`, `entity_class`, `action_label` |
| `components/list_panel_delete_row.html` | fila seleccionable/eliminable | `item_id`, `item_title`, `icon`, `entity_class`, `select_label`, `action_url`, `action_label`, opcionales `return_to_value`, `hidden_name`, `hidden_value` |

Regla: si se agrega una nueva entidad con panel de reordenar o eliminar, no copiar el HTML completo de la fila; crear solo el wrapper de entidad e incluir el parcial correspondiente.

## Estados oficiales

Usar clases de estado con prefijo `is-`:

```css
.is-active
.is-open
.is-selected
.is-empty
.is-editing
.is-disabled
```

## Clases JavaScript

Las clases `js-*` son hooks de comportamiento. No deben recibir estilos visuales.

## Señales de deuda

Si un cambio requiere alguna de estas acciones, conviene documentarlo o reconsiderar el enfoque:

- agregar `!important`;
- agregar un z-index numérico global;
- crear una clase genérica como `.main`, `.card`, `.header`, `.actions`;
- copiar un bloque completo de CSS entre entidades;
- modificar `programs.css` para resolver un problema que también existe fuera de Programs.
