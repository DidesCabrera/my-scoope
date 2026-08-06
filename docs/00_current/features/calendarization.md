# Calendarización de programas

Status: current
Date: 2026-08-05

## Contrato funcional

`Program` continúa siendo una plantilla relativa y editable. Al activar Calendarizar,
`ProgramCalendarization` proyecta sus semanas sobre fechas reales y crea un
`CalendarizedDay` por cada slot. Cada día ocupado guarda un snapshot JSON versionado
con plan, comidas, alimentos, cantidades y totales; editar o eliminar el origen no
cambia la agenda activada.

- Solo se listan programas creados por el usuario.
- La fecha inicial corresponde a semana 1, día 1 y no puede estar en el pasado local.
- Se permiten programas incompletos después de confirmación; los días vacíos no envían.
- Solo existe una agenda `scheduled`, `active` o `paused` por usuario.
- Reemplazar exige confirmación y cancela los eventos pendientes anteriores.
- La hora inicial es 07:00 y puede editarse.
- `Profile.timezone_name` es el default; cada agenda conserva su propia timezone IANA.
- Pausar, reanudar y cancelar son acciones del dashboard `/app/calendarization/`.

## Ejecución y progreso

La calendarización también es la autoridad del programa vivido:

- cada check-in de comida agrega un `CalendarizedMealExecution`; completar,
  omitir o corregir nunca reescribe evidencia anterior;
- el estado visible de una comida se deriva de su último evento y las llaves de
  idempotencia hacen seguros los reintentos;
- la adherencia compara comidas planificadas contra completadas, omitidas y aún
  no registradas dentro de un periodo fechado;
- `WeightLog` sigue siendo la medición personal canónica y
  `CalendarizationMeasurementContext` sólo la relaciona con una agenda/día;
- una `CalendarizationReview` congela el resumen de adherencia y mediciones junto
  a energía, hambre, rendimiento al entrenar y una nota opcional;
- una `CalendarizationRevision` conserva snapshots antes/después y requiere una
  decisión explícita. Al aprobar, sólo cambia días estrictamente futuros, todavía
  sin evidencia, y recalcula sus eventos. Pasado y presente son inmutables.

Las revisiones pueden respaldar una propuesta, pero no modifican automáticamente
el plan. La API consumer permite decidir una revisión preparada por una autoridad
interna; no acepta snapshots arbitrarios desde el cliente.

## Notificaciones

Cada aviso existe primero como `ScheduledNotificationEvent` en UTC, calculado desde
fecha, hora local y timezone de la agenda. `NotificationDelivery` registra como máximo
una entrega por evento/dispositivo. El dispatcher recupera claims antiguos, reintenta
fallos transitorios hasta tres veces, desactiva endpoints 404/410 y respeta ventanas de
gracia de dos horas para el plan diario y 15 minutos para una comida.

La suscripción Web Push requiere acción del usuario, CSRF, endpoint HTTPS validado y
claves VAPID. El payload de lock screen es discreto y al tocarlo abre el snapshot dentro
de una ruta autenticada. En iOS/iPadOS se requiere instalar la PWA en Home Screen.

La operación está deshabilitada por defecto con `MYSCOOPE_WEB_PUSH_ENABLED=false`.
El dashboard y los snapshots siguen funcionando aunque Push no esté configurado.

La agenda lógica es común para todos los canales. La app móvil ya configura sus
horas y muestra próximos eventos; la entrega mediante notificaciones locales/APNs,
incluido el permiso nativo, se incorpora en CML07. Negar el permiso no bloquea la
ejecución del programa.

## Entradas técnicas

- comandos: `notas/application/services/commands/calendarization_commands.py`;
- cálculo/snapshot: `notas/application/services/calendarization/`;
- lecturas: `notas/application/queries/calendarization_queries.py`;
- ejecución/revisiones: `notas/application/services/commands/calendarization_execution_commands.py`;
- lecturas de adherencia: `notas/application/queries/calendarization_execution_queries.py`;
- adapter: `notas/application/services/notifications/web_push.py`;
- worker: `python manage.py dispatch_calendar_notifications --limit 100`;
- worker continuo: `python manage.py run_calendar_notification_worker --interval 300`;
- retención: `python manage.py prune_calendarization_data`;
- migración base: `notas/migrations/0044_profile_timezone_name_programcalendarization_and_more.py`;
- migración de ejecución: `notas/migrations/0048_calendarized_execution_reviews.py`.
