# Testing Strategy

## Objetivo

Los tests deben proteger los contratos que más se rompen al crecer el sistema.

## Prioridades

### 1. Services y commands

Agregar tests para:

- payload parsing;
- snapshots;
- add/remove/reorder;
- comandos de guardado;
- comandos de aplicación de propuestas;
- permisos/capabilities.

### 2. Arquitectura

Mantener tests que aseguren:

- `application` no importa `presentation`;
- `application` no importa `interface`;
- rutas críticas siguen existiendo.

### 3. Regresiones UI lógicas

Cuando un bug se repite, agregar test si puede representarse sin navegador.

Ejemplos:

- eliminar elemento intermedio compacta posiciones;
- modo edición se mantiene tras submit;
- comparación guardada conserva snapshot;
- rutas de comparadores e inbox siguen registradas.

## Uso de ZIPs

Para cambios de arquitectura o tests, usar export `full`.

Para cambios de UI simples, usar export `ai`.
