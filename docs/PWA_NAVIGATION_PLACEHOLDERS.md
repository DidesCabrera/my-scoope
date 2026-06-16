# PWA navigation placeholders

La splash inicial de iOS/iPadOS se controla con los `apple-touch-startup-image` definidos en `notas/templates/notas/base.html`. Esa imagen la muestra el sistema al abrir la PWA desde el ícono de inicio. No debe reutilizarse para navegación interna.

La carga entre páginas se resuelve con un placeholder HTML/CSS ubicado en `notas/templates/notas/base.html`:

```html
<div class="pwa-navigation-placeholder js-pwa-navigation-placeholder" aria-hidden="true">
```

El comportamiento está en `notas/static/notas/js/pwa.js`. Al hacer click en un link interno de `/app/`, el script detecta la URL de destino, agrega `pwa-is-navigating` al `<html>` y también agrega una clase de variante según la vista destino.

## Variantes disponibles

- `pwa-navigation-placeholder--dailyplan-list`
- `pwa-navigation-placeholder--dailyplan-detail`
- `pwa-navigation-placeholder--meal-list`
- `pwa-navigation-placeholder--meal-detail`
- `pwa-navigation-placeholder--food-list`
- `pwa-navigation-placeholder--food-detail`
- `pwa-navigation-placeholder--proposal-list`
- `pwa-navigation-placeholder--proposal-detail`
- `pwa-navigation-placeholder--profile`
- `pwa-navigation-placeholder--home`
- `pwa-navigation-placeholder--generic`

## Dónde ajustar estilos manualmente

Los estilos están en `notas/static/notas/css/base.css`, dentro del bloque:

```css
/* --- PWA navigation placeholders --- */
```

Para modificar una vista específica, usa la clase de variante. Ejemplo:

```css
html.pwa-standalone.pwa-is-navigating.pwa-navigation-placeholder--meal-detail .pwa-navigation-placeholder__kpis {
  display: grid;
}
```

## Tiempo de visualización

No hay un tiempo fijo. El placeholder aparece cuando el usuario inicia una navegación interna y desaparece naturalmente cuando el navegador pinta la página destino. Si la vista carga muy rápido, se verá poco tiempo; si tarda más, se mantiene durante la transición.

## Elementos del placeholder

- `pwa-navigation-placeholder__topbar`: header visual de destino.
- `pwa-navigation-placeholder__summary`: líneas introductorias.
- `pwa-navigation-placeholder__tabs`: tabs simuladas.
- `pwa-navigation-placeholder__kpis`: bloques KPI.
- `pwa-navigation-placeholder__cards`: cards de listas.
- `pwa-navigation-placeholder__table`: panel/tabla para vistas tipo detalle.
