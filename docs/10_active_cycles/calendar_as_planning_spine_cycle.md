# Calendario como eje de planificación

Status: active
Date: 2026-10-20

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

- CALV00: completado en rama de trabajo; contrato, ADR 0205 e inventario de
  dependencias y migración documentados.
- CALV01: base aditiva implementada y pruebas dirigidas verdes; falta backfill
  contra una copia representativa de staging antes del cutover.
- CALV02: asignar, quitar y mover planes manuales y reemplazar la proyección
  futura de un programa implementados con historial. Mover un día originado en
  programa sigue pendiente por su procedencia y recordatorios: no se habilitará
  hasta resolver el slot original, los eventos pendientes y la trazabilidad. Se conserva la
  restricción de un solo programa globalmente vigente: la revisión automática
  rechazó quitarla y el reemplazo por fechas funciona sin ese cambio.
- CALV03: ejecución append-only compartida para días manuales; notificaciones
  manuales pendientes.
- CALV04: periodos y cálculo básico de adherencia implementados; integración
  de métricas en Hoy y web pendiente.
- CALV05: endpoints aditivos de calendario, historial diario y progreso disponibles en rama;
  Hoy lee el snapshot fechado y crear un plan para hoy crea una asignación. La
  proyección heredada de programa excluye días sustituidos manualmente. Los
  indicadores principales de Home/Inicio ya leen el periodo del calendario;
  faltan recordatorios de planes individuales y revisar el contrato heredado
  `TodayData.adherence` antes del cutover.
- CALV06: vistas web y móvil de revisión accesibles desde el calendarizador
  heredado; ambas muestran semana, cuatro semanas, agenda y cumplimiento. La
  asignación, sustitución y movimiento de planes manuales ya tienen acciones e
  historial consultable por fecha; faltan revisión visual en clientes y aprobación funcional
  antes de sustituir la navegación principal.
- CALV07: pendiente; no se ha publicado ni ejecutado integración.

Validación local: pruebas dirigidas de calendario, programas, planes fijados,
contratos, límites de dominio, borrado de cuenta y vistas web durante el ciclo;
lint Python y lint móvil focalizado. Antes de integrar faltan el gate relevante,
revisión visual/funcional en cliente y prueba de migración sobre datos
representativos. No se ha publicado ni desplegado esta rama.
