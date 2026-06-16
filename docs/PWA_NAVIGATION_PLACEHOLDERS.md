# PWA navigation placeholders

La splash inicial de iOS/iPadOS se controla con los `apple-touch-startup-image` definidos en `notas/templates/notas/base.html`. Esa imagen la muestra el sistema al abrir la PWA desde el ícono de inicio. No debe reutilizarse para navegación interna.

La carga entre páginas se resuelve con un placeholder HTML/CSS ubicado como componente reutilizable en:

```text
notas/templates/components/pwa_navigation_placeholder.html
```

Ese componente se incluye desde `notas/templates/notas/base.html`.

El comportamiento está en `notas/static/notas/js/pwa.js`. Al hacer click en un link interno de `/app/`, el script detecta la URL de destino, agrega `pwa-is-navigating` al `<html>` y también agrega una variante según el **tipo de vista destino**, no según la entidad.

## Variantes disponibles

- `pwa-navigation-placeholder--list`
- `pwa-navigation-placeholder--detail`
- `pwa-navigation-placeholder--home`
- `pwa-navigation-placeholder--profile`

## Reglas de clasificación

- `/app` → `home`
- `/app/profile...` y `/app/authors...` → `profile`
- `/app/dailyplans`, `/app/meals`, `/app/foods`, `/app/proposals`, `/app/ai-tools` → `list`
- Cualquier otra ruta interna de `/app/` → `detail`

## Estructura visual

### Vista lista

- Header global simplificado:
  - espacio flexible
  - acciones
- Componente inicial:
  - logo genérico
  - título de página
  - structural indicator
- Cards:
  - header de card
  - título
  - structural indicator
  - dash KPI
  - panel como bloque único dinámico

### Vista detail

- Header global:
  - ícono genérico
  - título
  - acciones
- Page detail:
  - título
  - structural indicator
  - dash KPI
  - panel como bloque único dinámico

### Home

- Header global:
  - ícono genérico
  - acciones
- Logo MyScoope
- Un banner principal con proporción cercana al banner real
- Home cards en grilla de dos columnas en mobile:
  - ícono
  - título
  - indicadores
  - acción

### Profile

- Header global
- Resumen de cuenta:
  - título con ícono
  - texto secundario
  - métrica principal
  - grilla de datos de cuenta
- Cards de configuración con copia y acción

## Dónde ajustar estilos manualmente

Los estilos están en `notas/static/notas/css/base.css`, dentro del bloque:

```css
/* --- PWA navigation placeholders --- */
```

Para modificar una variante completa, usa la clase de tipo de vista. Ejemplo:

```css
html.pwa-standalone.pwa-is-navigating.pwa-navigation-placeholder--detail .pwa-navigation-placeholder__detail-page {
  gap: 16px;
}
```

Para revisar el placeholder en desktop, abre DevTools y agrega clases al `<html>` desde la consola:

```js
document.documentElement.classList.add(
  "pwa-standalone",
  "pwa-is-navigating",
  "pwa-navigation-placeholder--detail"
);
```

Para cambiar de variante:

```js
document.documentElement.className = document.documentElement.className
  .split(" ")
  .filter((className) => !className.startsWith("pwa-navigation-placeholder--"))
  .join(" ");

document.documentElement.classList.add(
  "pwa-standalone",
  "pwa-is-navigating",
  "pwa-navigation-placeholder--list"
);
```

Para ocultarlo:

```js
document.documentElement.classList.remove("pwa-is-navigating");
```

## Tiempo de visualización

No hay un tiempo fijo. El placeholder aparece cuando el usuario inicia una navegación interna y desaparece naturalmente cuando el navegador pinta la página destino. Si la vista carga muy rápido, se verá poco tiempo; si tarda más, se mantiene durante la transición.

## Criterio visual actual

Los placeholders no usan bordes. Las superficies principales usan los tokens existentes (`--surface-card` y `--surface-card-muted`) para acercarse al color real de cards y bloques de MyScoope. El efecto dinámico se aplica al elemento final visible de cada unidad: líneas, indicadores, KPIs, paneles y acciones.
