# UI System

Este documento declara el contrato visual vigente de My Scoope para que nuevas implementaciones mantengan coherencia entre Foods, Meals, DailyPlans, Programs, Inbox, Proposals, Comparators, Home y Profile.

La Etapa 1 no rediseña la interfaz. Su objetivo fue ordenar el lenguaje común, reducir decisiones improvisadas y dejar explícitas las reglas que deben seguir los próximos patches.

La Etapa 2 inicia la consolidación real de componentes repetidos. El criterio es conservar la apariencia y el comportamiento existentes, pero mover HTML duplicado hacia parciales compartidos cuando el contrato visual es el mismo.

---

## Principio central

Antes de crear CSS o HTML nuevo, revisar si el caso corresponde a:

1. un componente existente;
2. una variante de un componente existente;
3. un componente nuevo realmente necesario.

La opción preferida es siempre extender un patrón existente mediante una variante acotada y nombrada.

---

## Capas CSS oficiales

El CSS debe leerse mentalmente en estas capas, aunque la estructura física todavía sea progresiva:

| Capa | Responsabilidad | Archivos actuales |
|---|---|---|
| Foundations | contrato neutral, tokens generados, temas, reset/base | `design/ui-contract.json`, `ui-contract.generated.css`, `tokens.css`, `base.css` |
| Layout | estructura app, sidebar, header, page shell | `layout.css`, `sidebar.css`, `header.css`, `page.css` |
| Primitives | piezas pequeñas reutilizables | `buttons.css`, `actions.css`, `menu.css`, `toast.css`, `icons.css` |
| Components | componentes compartidos | `entity_card.css`, `content_panel.css`, `detail_section.css`, `card_*`, `panel_tabs.css`, `data_grid.css`, `dash_kpi.css`, `alloc-*`, `picker_list.css` |
| Features | reglas propias de una feature | `home.css`, `profile.css`, `programs.css`, `proposals.css`, `comparators.css` |
| Legacy | estilos históricos que se migran gradualmente | reglas genéricas, colores hardcodeados y overrides puntuales |

### Regla de ubicación

- Un estilo reutilizable entre 2 o más features debe vivir en un componente compartido.
- Un estilo exclusivo de una feature puede vivir en su archivo de feature.
- Un archivo de feature no debe redefinir contratos globales salvo que use una variante clara.
- Los fixes con `!important` deben considerarse deuda temporal y documentarse si se agregan.

---

## Tokens oficiales

Los nuevos estilos deben usar tokens semánticos derivados de
`design/ui-contract.json`. Django carga primero la compatibilidad histórica de
`notas/static/notas/css/tokens.css` y después la salida autoritativa
`notas/static/notas/css/ui-contract.generated.css`.

No editar la salida generada. Ejecutar `npm run generate:ui` para actualizar CSS
y TypeScript, y `npm run check:ui` para comprobar que el repositorio está
sincronizado. Las diferencias deliberadas entre web y React Native se declaran
en `platforms` dentro del contrato.

### Superficies

| Token | Uso |
|---|---|
| `--surface-app` | fondo general de la aplicación |
| `--surface-page` | fondo de páginas o zonas amplias |
| `--surface-card` | cards, paneles y contenedores principales |
| `--surface-card-muted` | subpaneles, tabs inactivos, fondos secundarios |
| `--surface-elevated` | dropdowns, modales, floating panels |
| `--surface-picker` | pickers y selectores nutricionales |
| `--surface-sidebar` | sidebar |

### Texto

| Token | Uso |
|---|---|
| `--text-main` | texto principal |
| `--text-muted` | texto secundario |
| `--text-soft` | labels auxiliares |
| `--text-subtle` | texto de baja jerarquía |
| `--text-inverted` | texto sobre fondos oscuros o activos |
| `--text-link` | links |

### Bordes

| Token | Uso |
|---|---|
| `--border-soft` | separadores sutiles |
| `--border-default` | borde normal de card/input/panel |
| `--border-strong` | borde destacado |
| `--border-inverted` | borde sobre fondos invertidos |

### Interacción

| Token | Uso |
|---|---|
| `--interactive-primary` | acciones principales |
| `--interactive-primary-hover` | hover de acción principal |
| `--interactive-secondary` | acción secundaria destacada |
| `--interactive-muted` | acción secundaria neutra |
| `--interactive-hover` | hover suave |
| `--interactive-active` | estado activo suave |

### Entidades

| Token | Entidad |
|---|---|
| `--entity-food` | Food |
| `--entity-meal` | Meal |
| `--entity-dailyplan` | DailyPlan |
| `--entity-dpm` | DPM |
| `--entity-program` | Program |
| `--entity-proposal` | Proposal |
| `--entity-inbox` | Inbox |
| `--entity-comparator` | Comparator |
| `--entity-home` | Home |
| `--entity-profile` | Profile |

### Nutrición

| Token | Uso |
|---|---|
| `--nutrition-protein` | proteína |
| `--nutrition-carbs` | carbohidratos |
| `--nutrition-fat` | grasas |
| `--nutrition-kcal` | calorías |
| `--nutrition-ppk` | g/kg |

### Z-index

Usar exclusivamente la escala declarada en `tokens.css`:

| Token | Uso |
|---|---|
| `--z-below` | pseudo-elementos detrás de su componente |
| `--z-base` | capa base |
| `--z-raised` | elementos internos elevados |
| `--z-sticky` | headers sticky de tablas o barras locales |
| `--z-dropdown` | menús y dropdowns |
| `--z-picker-dropdown` | dropdowns de pickers |
| `--z-tooltip` | tooltips flotantes |
| `--z-header-mini` | header mobile/mini |
| `--z-header` | header global |
| `--z-sidebar-backdrop` | backdrop sidebar mobile |
| `--z-sidebar` | sidebar |
| `--z-modal` | modales |
| `--z-toast` | mensajes/toasts |
| `--z-pwa-cover` | máscaras PWA de navegación/carga |

No agregar números sueltos de `z-index` salvo en casos internos de stacking local (`0`, `1`, `2`) dentro de un componente aislado.

---

## Breakpoints oficiales

Los breakpoints son contrato de diseño, no tokens técnicos de media query. En CSS vanilla los custom properties no funcionan directamente dentro de `@media`, por lo tanto se usan los valores literales documentados.

| Rango | Valor | Uso |
|---|---:|---|
| Mobile | `max-width: 768px` | layouts de una columna, acciones mobile, cards compactas |
| Tablet / shell compacto | `max-width: 980px` | sidebar colapsado, header mobile, PWA iPad/tablet |
| Desktop | `min-width: 981px` | grillas desktop, paneles amplios, navegación lateral |

Regla práctica:

- Usar `768px` para comportamiento de contenido.
- Usar `980px` para comportamiento del shell de aplicación.
- Evitar nuevos breakpoints salvo que el componente lo justifique y quede documentado.

---

## Naming oficial

Preferir BEM simple:

```css
.block
.block__element
.block--variant
.block.is-state
```

Reglas:

- La entidad debe expresarse como variante explícita: `--food`, `--meal`, `--dailyplan`, `--program`.
- Evitar clases genéricas nuevas como `.main`, `.card`, `.header`, `.actions`, `.edit` sin prefijo de bloque.
- Los estados dinámicos deben usar `is-*`: `is-active`, `is-open`, `is-selected`, `is-empty`, `is-editing`.
- Las clases JS deben usar `js-*` y no deben recibir estilos visuales.

---

## Componentes oficiales

El inventario vigente vive en `docs/00_current/architecture/component_inventory.md`.

### Regla Etapa 2

Cuando varias entidades comparten la misma estructura visual, crear un parcial compartido para la parte repetida y dejar en el template por entidad solo la configuración específica: URL, título, icono, clase de entidad, texto vacío y campos propios.

Ejemplo vigente:

```text
components/list_panel_reorder_row.html
components/list_panel_delete_row.html
```

Estos parciales son la base común de los paneles de reordenar/eliminar en listas.

Componentes que deben reutilizarse antes de crear alternativas:

- `entity-heading`
- `entity-indicators`
- `entity-metadata`
- `collection-page`
- `collection-empty-state`
- `message-card`
- `list-panel`
- `list-page-header`
- `card-title-comp`
- `structural-indicator`
- `entity-card`
- `entity-card__main`
- `entity-card__title`
- `entity-card__kpi`
- `entity-card__footer`
- `detail-section-header`
- `detail-section-heading`
- `child-card`
- `card-main`
- `panel-tabs`
- `panel-tab`
- `content-panel`
- `data-grid`
- `data-grid-edit-actions`
- `actions-row`
- `dash-kpi`
- `dash-kpi-range`
- `alloc-bar`
- `overflow-menu`
- `picker-list`

---

## Features con CSS propio

### Programs

Programs comparte el mismo lenguaje visual de Foods, Meals y DailyPlans. Su complejidad pertenece a la composición del dominio —semanas, días, slots y gráficos—, no a una familia visual independiente.

Regla principal:

> Una pieza de Programs puede tener estructura y contenido propios, pero debe reutilizar el componente visual correspondiente del UI System.

Por lo tanto:

- un panel de Programs usa `content-panel`;
- una navegación hermana usa `panel-tabs` y `panel-tab`;
- una entidad relacionada usa la familia de entity cards;
- una tabla nutricional usa `data-grid`;
- una acción usa los primitives de acciones existentes.

Las clases `program-*` deben controlar composición o comportamiento propio, no volver a declarar superficies, tabs, radios, bordes o estados interactivos compartidos.

`programs.css` es actualmente el archivo con mayor deuda por concentración de responsabilidades. Mantenerlo funcional tiene prioridad sobre dividirlo de golpe.

La carga de `programs.css` es selectiva mediante el bloque `feature_css`; no debe volver a agregarse globalmente a `base.html`. `program_week_tabs.css` contiene la primera extracción acotada y solo se carga en Program detail.

Contrato Etapa 1:

- No agregar estilos globales dentro de `programs.css`.
- Todo estilo nuevo debe comenzar con `program-` o `program-chart-`.
- Si un patrón sirve fuera de Programs, moverlo primero a un componente compartido.
- Si un patrón ya existe fuera de Programs, consumirlo y conservar `program-*` solo como clase de composición o hook.
- Los nuevos fixes de gráfico deben usar tokens de z-index, superficie, texto y borde.
- La separación física futura recomendada es:

```text
components/programs.css
components/programs/program-board.css
components/programs/program-week.css
components/programs/program-chart.css
components/programs/program-picker.css
```

### Comparators y Proposals

Estos archivos son feature CSS válidos. No deben redefinir estilos base de cards, tabs o data-grid salvo mediante variantes propias.

---

## Checklist para próximos patches UI

Antes de entregar un patch visual:

1. ¿El cambio usa tokens semánticos en vez de colores directos?
2. ¿La clase nueva tiene prefijo de componente o feature?
3. ¿El estado dinámico usa `is-*`?
4. ¿La clase usada por JavaScript usa `js-*` y no tiene estilos?
5. ¿El z-index usa token oficial?
6. ¿El breakpoint usa `768px` o `980px` salvo excepción justificada?
7. ¿El componente ya existía en `component_inventory.md`?
8. ¿El cambio evita aumentar `!important`?
9. ¿El comportamiento mobile y desktop queda explícito?
10. ¿La decisión relevante quedó documentada si cambia el sistema?

---

## Criterio para IA

Cuando una IA modifique UI en este proyecto, debe tratar este documento como contrato principal de frontend. Si hay conflicto entre una solución rápida y este contrato, priorizar el contrato salvo que el usuario pida explícitamente un fix urgente y acotado.
