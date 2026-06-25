# Dark Mode — Color Audit

## Objetivo

Este documento registra la auditoría inicial de colores del sistema antes de implementar dark mode.

La implementación de dark mode debe hacerse mediante tokens semánticos, no reemplazando colores manualmente por componente.

El objetivo es separar colores estructurales de interfaz, colores de texto, colores de borde, colores interactivos, colores de entidades, colores nutricionales y colores legacy o hardcodeados que deben migrarse gradualmente.

---

## Estado actual

El sistema ya cuenta con un archivo central de tokens:

notas/static/notas/css/tokens.css

Actualmente existen tokens como:

- --color-primary
- --color-secondary
- --color-text
- --color-text-muted
- --color-bg
- --color-bg-2
- --color-bg-3
- --color-bg-4
- --color-border-1
- --color-border-2
- --color-protein
- --color-carbs
- --color-fat
- --color-kcal
- --color-ppk
- --color-dailyplan
- --color-meal
- --color-food
- --color-dpm
- --color-program
- --color-inbox
- --color-actions

El problema principal es que varios componentes todavía usan colores hardcodeados como white, black, #fff, #111, #ddd, rgba(...) y rgb(...).

Esto dificulta implementar dark mode de manera segura.

---

## Decisión general

El dark mode se implementará creando una capa nueva de tokens semánticos.

Los tokens actuales --color-* no se eliminarán de inmediato.

Primero se agregarán tokens nuevos como:

- --surface-app
- --surface-page
- --surface-card
- --surface-card-muted
- --surface-elevated
- --text-main
- --text-muted
- --text-soft
- --text-inverted
- --border-soft
- --border-strong
- --interactive-primary
- --interactive-hover
- --interactive-active
- --input-bg
- --input-border
- --input-text
- --input-placeholder

Luego los componentes se migrarán gradualmente hacia esos tokens.

---

## Clasificación de colores

### 1. Colores estructurales de superficie

Estos colores controlan fondos generales, fondos de página, cards, paneles, modales y contenedores.

Tokens actuales relacionados:

- --color-bg
- --color-bg-2
- --color-bg-3
- --color-bg-4
- --color-bg-picker
- --color-bg-picker2
- --color-bg-98

Futuro modelo semántico:

- --surface-app
- --surface-page
- --surface-card
- --surface-card-muted
- --surface-elevated
- --surface-picker
- --surface-sidebar

Archivos prioritarios:

- notas/static/notas/css/base.css
- notas/static/notas/css/layout.css
- notas/static/notas/css/components/card_main.css
- notas/static/notas/css/components/card_child.css
- notas/static/notas/css/components/card_father.css
- notas/static/notas/css/components/modal_create.css
- notas/static/notas/css/components/home.css
- notas/static/notas/css/components/profile.css
- notas/static/notas/css/components/food_picker.css

---

### 2. Colores de texto

Estos colores controlan texto principal, texto secundario, labels, descripciones, placeholders y texto invertido.

Tokens actuales relacionados:

- --color-text
- --color-text-muted

Futuro modelo semántico:

- --text-main
- --text-muted
- --text-soft
- --text-subtle
- --text-inverted
- --text-link

Archivos prioritarios:

- notas/static/notas/css/base.css
- notas/static/notas/css/components/header.css
- notas/static/notas/css/components/sidebar.css
- notas/static/notas/css/components/card_title.css
- notas/static/notas/css/components/data_grid.css
- notas/static/notas/css/components/profile.css
- notas/static/notas/css/components/food_picker.css
- notas/static/notas/css/icons.css

---

### 3. Colores de borde

Estos colores controlan divisores, bordes de cards, bordes de inputs, líneas internas y separadores.

Tokens actuales relacionados:

- --color-border-1
- --color-border-2

Futuro modelo semántico:

- --border-soft
- --border-default
- --border-strong
- --border-inverted

Archivos prioritarios:

- notas/static/notas/css/components/card_main.css
- notas/static/notas/css/components/card_child.css
- notas/static/notas/css/components/data_grid.css
- notas/static/notas/css/components/food_picker.css
- notas/static/notas/css/components/modal_create.css
- notas/static/notas/css/components/profile.css

---

### 4. Colores interactivos

Estos colores controlan botones, acciones, links, hover, active states, tabs y elementos clickeables.

Tokens actuales relacionados:

- --color-primary
- --color-primary-light
- --color-secondary
- --color-actions

Futuro modelo semántico:

- --interactive-primary
- --interactive-primary-hover
- --interactive-secondary
- --interactive-muted
- --interactive-hover
- --interactive-active

Archivos prioritarios:

- notas/static/notas/css/components/actions.css
- notas/static/notas/css/components/header.css
- notas/static/notas/css/components/sidebar.css
- notas/static/notas/css/components/menu.css
- notas/static/notas/css/components/buttons.css
- notas/static/notas/css/components/card_title.css

---

### 5. Colores nutricionales

Estos colores representan información nutricional y no deberían cambiar radicalmente entre light mode y dark mode.

Tokens actuales:

- --color-protein
- --color-carbs
- --color-fat
- --color-qty
- --color-kcal
- --color-kcal-border
- --color-ppk
- --color-ppk0

Decisión:

Estos colores se mantienen como lenguaje visual del dominio nutricional.

En dark mode podrían ajustarse solo si hay problemas de contraste.

Archivos relacionados:

- notas/static/notas/css/components/dash_kpi.css
- notas/static/notas/css/components/dash_kpi_dpm.css
- notas/static/notas/css/components/alloc-bar.css
- notas/static/notas/css/components/alloc-cell.css
- notas/static/notas/css/components/data_grid.css
- notas/static/notas/css/components/grid_foods_aggregation.css

---

### 6. Colores de entidades

Estos colores identifican entidades principales de MyScoope.

Tokens actuales:

- --color-dailyplan
- --color-dpm
- --color-meal
- --color-food
- --color-program
- --color-inbox
- --color-home
- --color-profile

Decisión:

Estos colores no deben tratarse como fondos estructurales.

Son colores de identidad visual de entidades.

En dark mode deberían mantenerse, o ajustarse muy levemente para contraste.

Archivos relacionados:

- notas/static/notas/css/icons.css
- notas/static/notas/css/components/card_title.css
- notas/static/notas/css/components/header.css
- notas/static/notas/css/components/sidebar.css

---

### 7. Proposal UI

La UI de proposals está siendo trabajada aparte.

Por ahora queda fuera del primer ciclo de dark mode.

Archivo excluido temporalmente:

- notas/static/notas/css/components/proposals.css

Cuando proposals se estabilice, se migrará al mismo sistema de tokens semánticos.

---

## Archivos CSS con mayor prioridad

### Prioridad 1

Estos archivos afectan la estructura global de la app:

- notas/static/notas/css/tokens.css
- notas/static/notas/css/base.css
- notas/static/notas/css/layout.css
- notas/static/notas/css/components/header.css
- notas/static/notas/css/components/sidebar.css

### Prioridad 2

Estos archivos afectan cards, KPIs y contenido principal:

- notas/static/notas/css/components/card_main.css
- notas/static/notas/css/components/card_child.css
- notas/static/notas/css/components/card_father.css
- notas/static/notas/css/components/card_title.css
- notas/static/notas/css/components/dash_kpi.css
- notas/static/notas/css/components/data_grid.css

### Prioridad 3

Estos archivos afectan interacción y formularios:

- notas/static/notas/css/components/food_picker.css
- notas/static/notas/css/components/picker_list.css
- notas/static/notas/css/components/modal_create.css
- notas/static/notas/css/components/actions.css
- notas/static/notas/css/components/menu.css

### Prioridad 4

Estos archivos afectan vistas específicas:

- notas/static/notas/css/components/home.css
- notas/static/notas/css/components/profile.css
- notas/static/notas/css/components/table.css
- notas/static/notas/css/components/toast.css
- notas/static/notas/css/icons.css

---

## Criterio para migrar colores

Cada color hardcodeado debe clasificarse antes de cambiarse.

Ejemplos:

- background: white; probablemente debería migrar a background: var(--surface-card);
- color: black; probablemente debería migrar a color: var(--text-main);
- border-color: #ddd; probablemente debería migrar a border-color: var(--border-soft);
- background: rgba(0, 0, 0, 0.04); probablemente debería migrar a background: var(--interactive-hover);
- color: white; puede migrar a color: var(--text-inverted), o mantenerse si pertenece a un botón, icono o elemento sobre fondo oscuro.

Debe revisarse según contexto.

---

## Resultado esperado del Bloque 1

El Bloque 1 se considera terminado cuando:

1. Existe este documento.
2. Los colores están clasificados.
3. Se sabe qué archivos se migrarán primero.
4. Proposal UI queda explícitamente excluido del primer ciclo.
5. No se han hecho todavía cambios visuales grandes.
6. El siguiente paso lógico es editar tokens.css.

---

## Siguiente bloque

Después de este documento, el Bloque 2 será:

Crear tokens semánticos light/dark en tokens.css.

Ese bloque sí modificará CSS, pero todavía de forma controlada.