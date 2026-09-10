# 0192 — Edición directa del programa activo mediante snapshots auditados

Status: accepted
Date: 2026-09-08

## Contexto

`Program` representa una plantilla relativa, reutilizable y editable. Al activarla,
`ProgramCalendarization` crea días con fechas reales y snapshots independientes. Esa
calendarización no es sólo una agenda: registra lo planificado, lo ejecutado, las
mediciones, las notas y los ajustes que realmente ocurrieron.

La vista móvil “Mi programa activo” necesita permitir completar o reemplazar planes
diarios sin modificar la plantilla que originó la activación. También debe dejar claro
que el enlace a la biblioteca abre la plantilla original y no el detalle histórico.

## Decisión

- `ProgramCalendarization` es la identidad del programa activo o vivido.
- `Program` conserva el rol de plantilla original; sus cambios posteriores no
  reescriben el programa activo y los cambios del programa activo no la modifican.
- El detalle de “Mi programa activo” se construye exclusivamente desde
  `CalendarizedDay.plan_snapshot`, fechas, progreso, mediciones, notas y revisiones de
  la calendarización.
- La asignación o reemplazo manual de un plan diario se permite sólo sobre fechas
  estrictamente futuras y sin evidencia de ejecución.
- El servidor construye el snapshot desde un `DailyPlan` de biblioteca propiedad del
  usuario. El cliente nunca envía snapshots arbitrarios.
- Cada asignación o reemplazo se registra como una `CalendarizationRevision` aplicada,
  con snapshot anterior y posterior, idempotencia y reconciliación de recordatorios.
- Reemplazar un día ocupado exige confirmación explícita.
- La semana del programa activo se ordena por `calendar_date`; puede comenzar cualquier
  día de la semana y muestra día de semana, número y mes. Los slots vacíos mantienen la
  acción para agregar un plan diario.
- El acceso a `Program` desde el detalle activo se presenta como “plantilla original”
  y explica que se trata de una referencia reutilizable distinta del historial activo.

## Consecuencias

La aplicación puede evolucionar notas, edición y métricas del programa activo sin
convertir la plantilla en un historial mutable. Los cambios futuros quedan auditados y
los días presentes o pasados permanecen protegidos. La UI y la API usan las fechas de
la calendarización como autoridad, incluso cuando la primera semana no comienza el
lunes.

