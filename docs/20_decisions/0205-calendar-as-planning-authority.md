# 0205 — Calendario como autoridad de planificación nutricional

Status: accepted
Date: 2026-10-20

## Contexto

El producto ofrece una calendarización de un único programa vigente y un plan
diario fijado que apunta directamente a la biblioteca. La primera opción exige
crear un programa incluso para planificar una fecha; la segunda no conserva el
contenido que se planificó. Reemplazar un programa completo después de algunos
días cumplidos cancela la instancia y dificulta explicar qué ocurrió realmente.

## Decisión

- El calendario del usuario posee como máximo un plan nutricional vigente por
  fecha local. Es la autoridad para Hoy, ejecución y métricas.
- Toda asignación de plan guarda un snapshot independiente. El objeto de
  biblioteca y el programa de origen permanecen como procedencia opcional.
- Asignar un plan y proyectar un programa son dos entradas a la misma secuencia
  de días fechados. Los programas conservan su agrupación, semanas y revisiones
  especializadas, pero dejan de determinar el periodo principal de adherencia.
- La sustitución futura de un programa conserva sus días anteriores y toda
  evidencia. Cada fecha reemplazada mantiene su snapshot y vínculo de
  sustitución; los días con evidencia no se reescriben.
- Durante la transición se mantiene una sola instancia de programa con estado
  global vigente por usuario. La instancia anterior pasa a cancelada cuando se
  acepta un reemplazo, pero sus asignaciones anteriores a la fecha efectiva
  continúan vigentes en el calendario. El vínculo entre instancias y la fecha
  efectiva explican la sustitución sin relajar la cardinalidad global.
- El cumplimiento se deriva de eventos de comidas asociados al día fechado.
  Los periodos de progreso son límites de consulta elegidos por el usuario;
  iniciar uno nuevo no elimina ni altera registros anteriores.
- Un plan por fecha es una regla nutricional. Otras actividades futuras podrán
  coexistir como categorías distintas sin convertirlas en segundos planes.

## Compatibilidad y transición

Se introducen esquema y lecturas aditivos. La API heredada de programa activo
permanece disponible durante la migración de clientes. Las calendarizaciones y
eventos anteriores se conservan. Los check-ins de `PinnedDailyPlan` hechos antes
del cutover no permiten reconstruir el contenido exacto que tuvo la biblioteca
en cada fecha; se preservan como evidencia legacy sin fabricar snapshots.

Esta decisión reemplaza la autoridad exclusiva de `ProgramCalendarization` de
0178, 0181 y 0192 para la experiencia general del calendario. Sus garantías de
snapshots, evidencia append-only y ajustes prospectivos siguen vigentes.
