# 0054 · Admin Analytics app shell

Status: accepted
Date: 2026-07-04

## Context

El ciclo ADM ya definió `admin_analytics` como la app transversal para el dashboard estratégico interno de My Scoope.

ADM01 debe crear una base técnica mínima antes de agregar métricas reales. El objetivo no es calcular KPIs todavía, sino asegurar frontera, rutas, permisos y navegación interna.

## Decision

Crear la app Django:

```text
admin_analytics
```

con ruta interna:

```text
/staff/analytics/
```

La primera pantalla será un overview staff-only y read-first que muestra:

```text
Admin Analytics
Weekly Active Nutrition Builders
módulos planificados del dashboard
estado de los próximos ADM patches
```

La app se registra en `INSTALLED_APPS`, tiene `urls.py`, `views.py`, `viewmodels.py`, template propio y tests básicos de acceso.

## Access rule

La ruta queda protegida con `staff_member_required`.

Usuarios anónimos y usuarios autenticados no-staff no deben ver el dashboard. Solo usuarios staff pueden acceder.

## Architecture

ADM01 mantiene la frontera acordada:

```text
admin_analytics observa.
admin_analytics no ejecuta negocio.
admin_analytics no modifica datos de dominio.
```

Por eso este patch no crea modelos, migraciones ni tablas analíticas.

## Consequences

- El ciclo ADM pasa de planificación a implementación.
- Existe un shell real para construir ADM02+ sin mezclarlo con `accounts` ni con `notas`.
- `/staff/analytics/` queda reservado como superficie interna de inteligencia de producto.
- Las métricas agregadas quedan postergadas explícitamente para ADM02.
