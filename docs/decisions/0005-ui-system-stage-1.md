# 0005 - UI System Stage 1

Status: accepted
Date: 2026-06-26

## Context

My Scoope llegó a una etapa donde la identidad visual ya está consolidada, pero el CSS y los templates crecieron mediante adaptaciones sucesivas. Esto generó patrones exitosos, aunque todavía no completamente formalizados.

La deuda principal no está en la apariencia actual, sino en la mantenibilidad: cascada global, colores directos, z-index no centralizado, variantes por entidad no siempre uniformes y archivos de feature con demasiadas responsabilidades, especialmente `programs.css`.

## Decision

Se declara una Etapa 1 del UI System con foco en documentación, contratos y tokens fundacionales, sin rediseñar la interfaz.

Se establece como contrato principal:

```text
docs/current/design/ui_system.md
```

Además:

- `tokens.css` pasa a concentrar la escala oficial de z-index, radios, espacios y breakpoints documentales.
- Los z-index globales existentes se normalizan hacia tokens semánticos.
- `docs/current/architecture/ui_patterns.md` y `component_inventory.md` quedan alineados con el contrato de UI System.
- `programs.css` se marca como feature CSS con deuda conocida y reglas de crecimiento seguras.

## Consequences

- Los próximos patches UI deben consultar el contrato antes de crear componentes o estilos nuevos.
- Los nuevos estilos deben preferir tokens semánticos en vez de colores directos.
- No se deben agregar z-index numéricos globales sin justificar.
- `programs.css` no debe recibir estilos genéricos nuevos.
- La separación física de CSS de Programs queda recomendada, pero no se ejecuta de golpe para evitar riesgo visual innecesario.
