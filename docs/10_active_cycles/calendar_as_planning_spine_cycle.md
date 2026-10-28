# Calendario como eje de planificación

Status: completed baseline (planning authority integrated; manual notification parity deferred)
Date: 2026-10-28

## Resultado buscado

Calendario es la autoridad de un plan nutricional por fecha. Un plan de biblioteca
se asigna mediante un snapshot independiente; un programa proyecta una serie de
esos mismos días. Ambos utilizan la misma ejecución de comidas, notificaciones e
historial. El origen se conserva para explicar qué creó cada día, sin controlar
la lectura de Hoy ni las métricas de adherencia.

La interfaz prioriza el tiempo: título, semana actual desde el lunes con
detalle de la fecha elegida, cobertura de las cuatro semanas siguientes, próximas
fechas con nombres y acciones para mover planes, y resumen de cumplimiento del
periodo actual. La vista extendida reúne las semanas actuales y futuras en un
scroll cronológico. La captura compartida el 2026-10-20 orienta la anatomía del
selector y detalle diario; los componentes vigentes del UI System definen su
implementación final.

## Invariantes

1. Una fecha local tiene como máximo un plan nutricional vigente por usuario.
2. Cada asignación guarda snapshot completo; la biblioteca sólo aporta origen.
3. La ejecución y las correcciones son evidencia append-only del snapshot fechado.
4. Reemplazar o mover conserva el antes, el después, quién y cuándo decidió.
5. Pasado y presente con evidencia no se reescriben. La sustitución de un programa
   afecta sólo días futuros elegibles y declara por separado los planes manuales.
6. Un nuevo periodo de progreso cambia el inicio de las métricas principales;
   conserva periodos y evidencia anteriores.
7. Fechas sin plan no cuentan como incumplimiento.
8. La zona horaria del usuario define la fecha local; las alertas mantienen un
   instante UTC y claves idempotentes.
9. La API y clientes existentes migran de forma compatible; no se reinterpretan
   registros antiguos como snapshots que nunca existieron.

## Ciclo de entrega

| Etapa | Entrega | Comprobación específica |
| --- | --- | --- |
| CALV00 | Contrato, inventario de consumidores y decisiones de migración | Casos fechados y matriz de datos existentes |
| CALV01 | Modelo de asignación fechada, procedencia y reemplazos auditables | Restricción de un plan vigente por usuario/fecha; migración reversible |
| CALV02 | Comandos para asignar, mover, quitar y proyectar programas | Colisiones explícitas, concurrencia, idempotencia y pasado protegido |
| CALV03 | Cumplimiento y recordatorios comunes al día calendarizado | El mismo flujo funciona para origen manual y programa |
| CALV04 | Periodos de progreso y métricas del calendario | Reiniciar periodo conserva histórico; días vacíos excluidos |
| CALV05 | API de calendario y proyecciones Hoy/Home con compatibilidad | Contratos y presupuesto de consultas enfocados |
| CALV06 | Web y móvil: vista temporal, agenda extendida y acciones | Aprobación visual/funcional antes de integración |
| CALV07 | Migración y despliegue gradual | Backfill comprobado, compatibilidad, rollback y smoke de staging |

## Orden y límites de migración

- Los `CalendarizedDay` con snapshot ya poseen una fuente histórica verificable.
  Las calendarizaciones completadas o canceladas permanecen como evidencia;
  sólo un día vigente ocupa el slot actual de una fecha.
- `PinnedDailyPlan` apunta hoy al objeto de biblioteca. El cambio crea snapshots
  para asignaciones actuales/futuras. Sus check-ins anteriores se preservan como
  evidencia legacy, pero no se fabrican snapshots históricos a partir del estado
  actual de la biblioteca.
- Las URLs y contratos de programa activo se mantienen mientras los clientes
  consumen el calendario. Se retiran en una etapa posterior con versión explícita.
- La migración de datos se prueba sobre casos de programa parcialmente ejecutado,
  reemplazo, plan fijado editado posteriormente, colisiones y fechas sin plan.

## Política de validación e integración

En desarrollo: pruebas Django focalizadas del dominio modificado y tests móviles
directamente relacionados; feedback visual en el cliente local. CALV06 requiere
aprobación visual/funcional de Felipe antes de iniciar integración. Al cerrar el
ciclo: gates locales relevantes una vez; la migración de esquema obliga tier
`full` en CI. El smoke posterior verifica datos migrados, recordatorios y Hoy,
sin repetir la misma suite de código como sustituto del despliegue.

## Estado de ejecución

- CALV00-CALV05: completados con ADR 0205, autoridad por fecha, historial,
  comandos, progreso, API y compatibilidad de lecturas.
- CALV06: completado; Calendar reemplazó la navegación principal de “Mi programa
  activo” en móvil y expone Planificación y Progreso. Web conserva una proyección
  compatible sobre la misma autoridad.
- CALV07: integración completada en `main` mediante el PR de staging. La migración
  y los servicios calendarizados quedaron clasificados para validación `full` y el
  bloqueo PostgreSQL se corrigió contra la frontera real de filas.
- Extensión posterior integrada: vista mensual, cobertura futura, métricas de
  progreso y compromisos de compra/cocina/entrenamiento con listas alimentarias
  snapshot por periodo.

El movimiento de días originados en Program y la creación automática de eventos de
recordatorio para asignaciones manuales quedan como brechas explícitas posteriores;
no se presentan como cobertura cerrada de CALV.

Los smokes de datos desplegados, recordatorios y comportamiento físico continúan
siendo evidencia operacional por ambiente; no reabren el ciclo de implementación.
El contrato vigente fue promovido a `docs/00_current/features/calendarization.md`.
