# Component Inventory

Inventario de patrones UI relevantes para crear o modificar secciones.

| Patrón | Usar para | Notas |
|---|---|---|
| `list-page-header` | encabezados de listas/secciones | no usar en details de instancia guardada si corresponde `card-title-comp` |
| `card-title-comp` | encabezado interno de details | útil para details sin tabs/list header |
| `structural-indicator` | conteos/resumen bajo títulos | reutilizar antes de crear indicadores nuevos |
| `data-grid-edit-actions` | grupos de acciones de edición | mantener estilo de botones consistente |
| `data-grid-edit-actions__button` | botones guardar/comparar/editar | preferir variantes existentes |
| `child-card` | cards de entidades relacionadas | meals, plans, attachments, proposals |
| `comparator-tabs` | tabs de comparadores | usar solo para navegación entre tipos |
| `actions-row` | acciones de formularios/pickers | mantener alineación y espaciado del sistema |
| `dash-kpi` | KPIs de dashboards | usar para métricas principales |
| `card-bottom` | metadata/acciones inferiores | evitar crear footer nuevo si aplica |
