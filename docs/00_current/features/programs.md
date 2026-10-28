# Programs

Status: current
Date: 2026-10-28
Audience: developers and AI assistants

## Estado

Feature vigente y compleja.

## Conceptos principales

- Programa semanal reutilizable y sin fechas propias.
- Semanas dinámicas.
- Días de programa basados en copias/snapshots de DailyPlans.
- KPIs semanales y de programa.
- Gráficos por día/semana.
- Detail semanal dedicado.
- Especificación nutricional y procedencia culinaria versionada cuando el origen es
  una propuesta del Solver.

## Relación con Calendario

Program es una plantilla, no la autoridad de lo que ocurrió en una fecha. Activarlo
proyecta snapshots de sus días hacia `CalendarizedDay`. Calendario conserva ejecución,
movimientos, sustituciones y progreso; modificar después la plantilla no reescribe
esos snapshots.

Durante la transición sólo una `ProgramCalendarization` puede conservar estado global
vigente por usuario, pero los días anteriores de una instancia reemplazada continúan
en el calendario junto con planes manuales. Nuevas funcionalidades de planificación
general deben construirse sobre Calendar, no sobre una segunda línea temporal dentro
de Programs.

## Programas generados o revisables

Una propuesta puede representar un programa culinario de varias semanas con
requisitos semanales, objetivos tipados y procedencia de variantes validadas. Aprobar
y aplicar siguen siendo acciones separadas. Al aplicar, se revalida el catálogo
culinario usado durante la revisión para evitar crear un programa desde evidencia que
cambió silenciosamente.

## Ubicación de lógica

```text
notas/interface/views/programs.py
notas/presentation/viewmodels/programs.py
notas/presentation/viewmodels/program_actions.py
notas/application/services/cache/program_summary.py
```

## Reglas

- No volver a crecer `programs.py` con builders visuales extensos.
- Si se agrega lógica de gráficos, mover a presentation/viewmodels o services adecuados.
- Si se agregan writes, usar commands.
- Si en el futuro se agrega comparador de Programs, diseñarlo como feature separada, no dentro de `programs.py`.
- No volver a usar “programa activo” como sinónimo de toda la planificación fechada.
