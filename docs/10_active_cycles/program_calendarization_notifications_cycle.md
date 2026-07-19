# Program Calendarization & Notifications Cycle

Status: active — implementation complete; staging Web Push smoke and rollout remain
Date: 2026-07-18
Last reviewed: 2026-07-19 — CAL00-CAL08 implemented in-repository; production credentials, scheduler and real-device staging smoke remain operational gates.
Cycle code: CAL

## Contexto

My Scoope ya permite construir programas de una o más semanas mediante `Program` y
`ProgramDay`. Esos programas son plantillas nutricionales relativas:

```text
Programa
  -> semana 1, día 1
  -> semana 1, día 2
  -> ...
  -> semana N, día 7
```

Aunque `Program` y `ProgramDay` conservan campos de fecha legacy, el contrato actual
es deliberadamente independiente del calendario. Calendarizar no debe reactivar esos
campos ni convertir la plantilla en una instancia fechada. Debe introducir una capa
separada que active una plantilla para un usuario y la proyecte sobre fechas reales.

La PWA actual es instalable y registra un service worker, pero este solo cachea
archivos estáticos. El proyecto todavía no tiene suscripciones Web Push, permisos de
notificación, entregas idempotentes ni un scheduler/worker para procesos diferidos.

La reevaluación del 2026-07-19 confirma que el requerimiento sigue encajando con el
producto, pero corrige cuatro supuestos del primer borrador:

1. **Calendarizar es un dashboard/herramienta personal**, no una nueva biblioteca de
   entidades paralela a Programs o DailyPlans.
2. El snapshot diario debe ser suficiente para consultar el plan completo aunque el
   programa de origen cambie o desaparezca; no basta con nombres y horas.
3. Un evento lógico programado y su entrega a cada dispositivo son conceptos distintos
   y necesitan persistencia separada.
4. Los modelos y services nuevos deben registrarse en las fronteras ejecutables de
   dominio/application que hoy protege la suite de arquitectura.

## Objetivo del ciclo

Permitir que un usuario:

1. entre a la nueva vista **Calendarizar**;
2. elija uno de sus programas semanales;
3. elija la fecha de inicio;
4. revise el rango y la correspondencia de días;
5. active la calendarización;
6. reciba cada mañana una notificación que abre el plan diario correspondiente.

Como extensión posterior del mismo ciclo, el usuario podrá activar recordatorios en
la hora configurada de cada comida.

## Tesis del ciclo

```text
Program = plantilla nutricional relativa y editable.
ProgramCalendarization = ejecución fechada para un usuario.
CalendarizedDay = snapshot resoluble del plan que corresponde a una fecha.
ScheduledNotificationEvent = aviso lógico que vence en un instante UTC.
NotificationDelivery = intento de entrega auditable e idempotente.
```

Calendarizar no debe mutar el programa original. Una edición posterior de la
plantilla tampoco debe cambiar silenciosamente una calendarización ya activada.

## Alcance funcional

### MVP

- nuevo dashboard personal **Calendarizar** dentro de Tools;
- selector limitado a programas creados por el usuario;
- fecha de inicio igual o posterior a la fecha local actual;
- preview del rango y de la asignación de fechas;
- activación, consulta, pausa, reanudación y cancelación;
- una sola calendarización vigente (`scheduled`, `active` o `paused`) por usuario;
- reemplazo de la vigente únicamente mediante confirmación explícita;
- vista **Hoy** con el plan diario correspondiente;
- notificación Web Push diaria en la zona horaria del usuario;
- apertura del día calendarizado al tocar la notificación;
- finalización automática al terminar el último día;
- registro idempotente de entregas y fallos técnicos.

### Extensión posterior: recordatorios por comida

- preferencia opt-in separada de la notificación diaria;
- un recordatorio por `DailyPlanMeal.hour` válido;
- omitir comidas sin hora, sin inventar horarios;
- reprogramación segura al pausar/reanudar;
- deduplicación por calendarización, fecha, comida y canal.

## Fuera de alcance

- sincronización bidireccional con Google Calendar, Apple Calendar u Outlook;
- envío por correo, SMS o WhatsApp;
- calendarizar programas públicos o compartidos sin guardarlos primero como propios;
- múltiples calendarizaciones simultáneas en el MVP;
- repetición infinita del programa;
- editar el programa original desde la vista Calendarizar;
- notificaciones generadas por IA;
- una app móvil nativa.

## Reglas de producto propuestas

### Selección y activación

- El selector muestra únicamente `Program.created_by == request.user`.
- Se permiten programas incompletos. Antes de activar, la UI debe mostrar una
  advertencia visible con la cantidad y las fechas que quedarán sin plan, además de
  exigir confirmación explícita.
- Los slots vacíos se materializan como `CalendarizedDay` sin `plan_snapshot`. La vista
  Hoy muestra `No hay un plan asignado para este día` y no genera una notificación de
  plan diario. El sistema nunca reutiliza el plan anterior ni inventa uno.
- La fecha elegida representa `semana 1, día 1`; no se fuerza a lunes.
- La fecha final se calcula como:

```text
end_date = start_date + (program.duration_days - 1)
```

- La activación crea un snapshot JSON autocontenido y versionado de cada día que sí tiene un
  plan, conservando referencias opcionales al programa y DailyPlan de origen para
  trazabilidad. Esta decisión evita clonar todo el grafo ORM y mantiene estable la
  calendarización frente a cambios posteriores del programa.
- El snapshot debe incluir lo necesario para ejecutar el día sin consultar el origen:
  nombre del plan; comidas con clave estable, orden, nombre, nota y hora; alimentos con
  nombre, cantidad, unidad y valores nutricionales usados por la vista; totales/resumen
  requeridos por el contrato de presentación. Debe incluir `schema_version` y un hash
  de contenido para trazabilidad.
- `source_program` usa `SET_NULL`: eliminar la plantilla no elimina el historial. Los
  identificadores de `ProgramDay` y `DailyPlan` dentro del día son trazas primitivas,
  no ForeignKeys que puedan provocar cascadas o acoplamiento histórico.
- Al activar una nueva calendarización cuando ya existe otra vigente, la interfaz debe
  explicar cuál será reemplazada y exigir confirmación.

### Activaciones o cambios después de la hora

- Si el usuario activa hoy después de la hora configurada, la vista Hoy queda disponible
  inmediatamente, pero el sistema no envía retroactivamente el aviso de la mañana.
- Si cambia la hora a un valor que ya pasó hoy, el cambio comienza en el próximo día
  elegible. Nunca produce un reenvío del evento de hoy.
- Una caída del scheduler admite una ventana de recuperación de 2 horas para el aviso
  diario. Después de esa ventana el evento queda `skipped` con una causa auditable.
- Los recordatorios por comida de CAL07 tendrán una gracia menor, inicialmente 15
  minutos, porque un recordatorio tardío pierde rápidamente su utilidad.

### Estados

```text
scheduled  -> la fecha de inicio todavía no llega
active     -> hoy está dentro del rango
paused     -> conserva la agenda, pero no envía notificaciones
completed  -> terminó el rango
cancelled  -> fue detenida por el usuario o reemplazada explícitamente
```

La resolución de estado temporal debe ser determinista e idempotente; no debe depender
de que una vista haya sido abierta.

- Pausar marca como `skipped` los eventos que vencen durante la pausa; no los acumula.
- Reanudar conserva o recalcula únicamente eventos futuros. Los avisos omitidos durante
  la pausa no se envían retroactivamente.
- Cancelar, completar o reemplazar una calendarización cancela todos sus eventos
  pendientes dentro de la misma transacción lógica.

### Zona horaria y hora diaria

- Las `07:00` significan siempre **07:00 en la zona horaria de la calendarización**.
  Nunca significan `07:00 UTC`, la hora del servidor ni un offset fijo.
- Agregar una zona horaria IANA persistida para el usuario, por ejemplo
  `America/Santiago`, `America/Lima` o `Europe/Madrid`.
- Detectarla desde el navegador con
  `Intl.DateTimeFormat().resolvedOptions().timeZone` como valor inicial, validarla
  contra la base IANA y permitir confirmarla/cambiarla.
- La pantalla de activación debe mostrar un resumen explícito como
  `Recibirás el plan diario a las 07:00 (America/Santiago)` para evitar que el usuario
  active una zona detectada incorrectamente.
- Guardar una copia de `timezone_name` en la calendarización. Esa copia define el reloj
  de la agenda y permite auditar por qué una entrega se calculó para cierto instante.
- El backend combina `calendar_date + daily_notification_time + timezone_name` y recién
  entonces convierte el resultado a UTC para compararlo con el reloj del scheduler.
- Ejemplo: dos usuarios con `07:00` local pueden tener `scheduled_for_utc` distintos;
  cada uno recibe la alerta a sus propias 07:00.
- El MVP usa `07:00` local como valor inicial, pero la vista de activación incluye un
  campo de hora editable. El valor elegido se guarda en `daily_notification_time` y
  puede modificarse posteriormente para la agenda vigente.
- Al cambiar la hora, solo se recalculan entregas futuras que todavía no fueron
  enviadas o reservadas; nunca se reenvía una notificación histórica.
- Los cambios de horario de verano se resuelven recalculando cada fecha con la zona
  IANA vigente, no reutilizando el offset UTC del día de activación.
- Si el usuario cambia la zona de una calendarización activa, solo se recalculan
  entregas futuras que todavía no fueron enviadas o reservadas. Las entregas históricas
  conservan la zona y el instante con que fueron procesadas.
- Cambiar la zona del perfil no debe modificar silenciosamente una calendarización
  activa: la UI debe ofrecer aplicar la nueva zona a esa agenda y pedir confirmación.
- Un viaje no cambia automáticamente la agenda solo porque el navegador reporte una
  zona nueva. El usuario decide si conserva su zona habitual o adopta la zona local.
- Aunque `07:00` normalmente no cae en una hora ambigua/inexistente por DST, el servicio
  de conversión debe definir una política general: ante una hora local inexistente usar
  el primer instante válido posterior; ante una hora repetida elegir la primera
  ocurrencia y registrar la resolución.

### Notificaciones y privacidad

- Solicitar permiso de notificaciones solo como consecuencia de una acción explícita
  del usuario.
- La activación y el permiso son pasos conceptualmente separados. El dashboard puede
  activar la agenda aunque Web Push falle y debe ofrecer un CTA explícito
  `Activar notificaciones`; si ya existe una suscripción válida, basta con mantenerla.
- En iPhone/iPad, Web Push se ofrece únicamente cuando My Scoope está instalada en la
  pantalla de inicio. Si no lo está, la UI explica cómo instalarla en vez de mostrar un
  botón que no puede funcionar. La implementación usa feature detection, no detección
  por user-agent.
- Calendarizar debe seguir funcionando como agenda dentro de la app si el permiso es
  rechazado o el navegador no soporta Web Push; la UI debe mostrar el estado real.
- La notificación de pantalla bloqueada usa contenido discreto, por ejemplo:
  `Tu plan diario está listo`, evitando exponer alimentos o notas personales.
- El detalle completo se consulta tras abrir una URL autenticada.
- Una suscripción push inválida se desactiva; no se borra evidencia de entregas previas.
- Los endpoints de alta/baja de suscripción requieren autenticación, CSRF y ownership.
  El endpoint push recibido se valida como HTTPS y contra SSRF/redes privadas antes de
  cualquier request saliente; el payload y las URLs de click usan contratos allowlisted.
- La clave VAPID privada vive solo en variables de entorno. La clave pública puede
  exponerse al navegador. Endpoints y claves de suscripción se enmascaran en logs/admin.

## Modelo de datos propuesto

Los nombres definitivos se validan en CAL00, pero la frontera esperada es:

### `ProgramCalendarization`

```text
user
source_program (nullable, SET_NULL)
program_name_snapshot
start_date
end_date
timezone_name
daily_notification_time
daily_notifications_enabled
meal_notifications_enabled
status
activated_at
paused_at
completed_at
cancelled_at
created_at / updated_at
```

### `CalendarizedDay`

```text
calendarization
calendar_date
week_number
day_number
source_program_day_id (nullable trace)
source_dailyplan_id (nullable trace)
plan_snapshot (versioned JSON)
```

Restricción única: `(calendarization, calendar_date)`.

El JSON debe incluir `schema_version` y construirse mediante un servicio dedicado. No
debe usarse como escape para persistir modelos arbitrarios o lógica de dominio.

### `WebPushSubscription`

```text
user
endpoint
p256dh_key
auth_key
user_agent / device_label
is_active
last_success_at
last_failure_at
created_at / updated_at
```

El endpoint debe ser único y sus secretos no deben aparecer en logs o administración
sin enmascarar.

### `ScheduledNotificationEvent`

```text
calendarization
calendarized_day
event_type (daily_plan | meal_reminder)
event_key (unique)
local_scheduled_date
local_scheduled_time
timezone_name
scheduled_for_utc
available_until_utc
status (pending | processing | dispatched | skipped | cancelled)
skip_reason
claimed_at
dispatched_at
created_at / updated_at
```

El evento se crea o recalcula para cada día no vacío cuando se activa la agenda o se
modifica su hora/zona. No depende de que exista una suscripción en ese momento.

### `NotificationDelivery`

```text
event
subscription
status (pending | sent | failed | expired)
attempt_count
sent_at
failure_code
created_at / updated_at
```

Restricción única: `(event, subscription)`. El `event_key` lógico usa, por ejemplo:

```text
daily:<calendarization_id>:<calendar_date>
meal:<calendarization_id>:<calendar_date>:<dailyplanmeal_snapshot_key>
```

## Arquitectura de ejecución

```text
Vista Calendarizar
  -> command de activación transaccional
  -> ProgramCalendarization + CalendarizedDay snapshots

Scheduler externo (cada 5 minutos)
  -> management command liviano
  -> selector de ScheduledNotificationEvent vencidos contra reloj UTC
  -> claim atómico skip_locked / compare-and-set
  -> fan-out hacia suscripciones activas existentes al vencer
  -> get_or_create NotificationDelivery(event, subscription)
  -> adapter Web Push
  -> estado por dispositivo + estado lógico dispatched/skipped

Service worker
  -> evento push
  -> notificación discreta
  -> notificationclick
  -> URL autenticada del CalendarizedDay
```

La lógica de negocio vive en application services/commands. Las vistas permanecen
delgadas, presentation arma viewmodels y el adapter Web Push queda aislado en
infraestructura/notificaciones. El scheduler no debe contener reglas duplicadas.

Para el MVP no es obligatorio adoptar Celery/RQ. Un management command invocado por
un cron de plataforma puede ser suficiente si:

- corre con una frecuencia compatible con el SLA;
- reclama eventos y crea entregas de manera atómica;
- tolera ejecuciones repetidas o solapadas;
- implementa una ventana de recuperación para una corrida omitida;
- expone fallos y conteos operacionales.

La implementación inicial usa Web Push estándar con VAPID mediante `pywebpush` detrás
de un adapter propio. CAL04 debe fijar una versión compatible, ejecutar tests del
adapter sin red y aprobar un smoke real Chrome/Android + Safari/iOS Home Screen antes
de consolidar la dependencia. `pywebpush` es actualmente compatible con Python 3.10+
pero tiene un único mantenedor; el adapter evita que esa dependencia se filtre al
dominio y deja abierta su sustitución.

El scheduler inicial será un management command idempotente apuntado a una cadencia de
5 minutos y un SLA de entrega de 0–5 minutos después de la hora elegida. En Render, el
cron usa horario UTC y tiene garantía de una sola corrida activa; CAL05 debe verificar
la cadencia y costo reales en staging antes de aceptarlo. Si el arranque recurrente no
cumple el SLA, el fallback aprobado es un background worker liviano sobre el mismo
command/selector, no duplicar reglas ni introducir Celery automáticamente. Celery/RQ
queda diferido hasta que volumen, retries o latencia lo justifiquen.

## Retención y ubicación de preferencias

- La zona IANA base vive en `Profile.timezone_name`, porque es una preferencia general
  del usuario y `Profile` ya representa su ficha personal operativa.
- Cada `ProgramCalendarization` conserva su propia copia de `timezone_name` y
  `daily_notification_time` para no depender de cambios silenciosos del perfil.
- Las calendarizaciones terminadas y sus snapshots se conservan como historial hasta
  que el usuario las elimine explícitamente. La UI puede archivarlas sin borrarlas.
- Los registros técnicos `ScheduledNotificationEvent` y `NotificationDelivery` se
  conservan 90 días y luego se eliminan mediante un comando de housekeeping,
  preservando solo métricas agregadas.
- Una suscripción push que responda como expirada/inválida se desactiva de inmediato;
  sus claves se eliminan después de 30 días inactiva si no fue renovada.

## Encaje con la arquitectura actual

### Fronteras de modelos

CAL01 debe actualizar en el mismo patch `notas/domain/model_boundaries.py`, su test y
`docs/00_current/architecture/domain_model_boundaries.md`. La propiedad propuesta es:

```text
Calendarization
  -> ProgramCalendarization
  -> CalendarizedDay
  -> puede depender de Programs

Notification Delivery
  -> WebPushSubscription
  -> ScheduledNotificationEvent
  -> NotificationDelivery
  -> puede depender de Calendarization
```

Los modelos nuevos pueden vivir en módulos físicos nuevos y reexportarse desde
`notas.domain.models`, usando relaciones ORM diferidas para evitar imports circulares.
No se aprovecha el ciclo para mover físicamente `Program` o `DailyPlan`.

### Fronteras de application

- Writes de activación, reemplazo, pausa, reanudación, cancelación y rescheduling:
  `notas/application/services/commands/calendarization_commands.py`.
- Lecturas de dashboard/Hoy/eventos vencidos:
  `notas/application/queries/calendarization_queries.py`.
- Snapshot y cálculo temporal reusable: una nueva entrada
  `notas/application/services/calendarization/`, registrada como área interna
  **Scheduling** en `APPLICATION_SERVICE_AREAS`.
- Builders y adapter Web Push: `notas/application/services/notifications/`; nunca
  importan commands ni deciden estados de calendarización.
- Entity Commands puede coordinar Scheduling y Notifications, por lo que la matriz
  interna debe declarar esas dependencias de forma explícita y mínima.
- El management command llama un command/use case de application; no contiene reglas.

### Contrato de interfaz y presentación

- Rutas: módulo propio en `notas/interface/urls/calendarization.py`.
- Views delgadas: `notas/interface/views/calendarization.py`.
- Dashboard/Hoy: page builders en `notas/presentation/pages/calendarization_pages.py`.
- Acciones y VM: módulos con prefijo `calendarization` en presentation.
- Registrar viewmodes, navegación y breadcrumbs en los contratos existentes.
- **Calendarizar** vive bajo la sección Tools del `APP_NAVIGATION`, porque ejecuta una
  plantilla; no es otra biblioteca junto a Programas, Planes, Comidas y Alimentos.
- Reutilizar `list-page-header`, cards, `structural-indicator`, actions y tokens. El
  CSS exclusivo usa prefijo `calendarization-`; no se agrega a `programs.css`.
- Actualizar la clasificación de placeholders PWA para que el dashboard sea una vista
  conocida y no caiga accidentalmente en el placeholder genérico de detail.

## Patch cycle

Implementation status on 2026-07-19: CAL00-CAL05, CAL07 and repository-side CAL08 are
complete. CAL06 is green for automated QA; its real-device/multi-zone staging smoke
must run after deployment with VAPID credentials and the five-minute scheduler.

| Patch | Objetivo | Resultado esperado |
|---:|---|---|
| CAL00 | Contrato y ADR | Registrar decisiones aceptadas y la reevaluación: dashboard Tools, snapshot autocontenido, una agenda vigente, timezone IANA, hora editable, incompletos advertidos, evento lógico separado de delivery, Web Push/VAPID y scheduler idempotente. |
| CAL01 | Dominio, fronteras y migraciones | Crear calendarización, días, eventos, suscripciones y deliveries; constraints/índices; registrar model boundaries y service areas ejecutables; admin seguro y migraciones. |
| CAL02 | Commands, snapshots y queries | Activar/reemplazar, construir snapshots completos y eventos, pausar/reanudar/cancelar/completar, reschedule futuro y resolver Dashboard/Hoy con concurrencia e idempotencia. |
| CAL03 | Dashboard Calendarizar | Viewmodes, navegación Tools, formulario programa+fecha+hora, preview, warning incompleto, reemplazo, estado/controles y Hoy; responsive, accesible y PWA placeholder. |
| CAL04 | Web Push foundation | `Profile.timezone_name`, permiso explícito, alta/baja CSRF-safe, validación SSRF, VAPID/pywebpush adapter, service worker push/click y UX iOS Home Screen/compatibilidad. |
| CAL05 | Entrega diaria | Claim de eventos, fan-out por dispositivo, retry acotado, gracia de 2h, management command, housekeeping, kill switch y validación del mecanismo Render. |
| CAL06 | Operación y MVP QA | Smoke real multi-browser/multi-device, zonas horarias/DST, duplicados/concurrencia, lag/SLA, fallos, scheduler staging, métricas y rollout progresivo. |
| CAL07 | Recordatorios por comida | Opt-in, eventos derivados de horas válidas, deduplicación, pausa/reanudación y controles de UX. |
| CAL08 | Cierre | Full regression, smoke real en staging, documentación vigente, runbook/rollback y cierre o decisión de siguiente ciclo. |

## Orden recomendado

```text
CAL00 -> CAL01 -> CAL02 -> CAL03 -> CAL04 -> CAL05 -> CAL06
                                                     |
                                                     +-> MVP listo

CAL07 -> CAL08
```

La infraestructura push se implementa después de que la agenda fechada funcione por
sí sola. Así, Calendarizar conserva valor y puede probarse aun cuando las
notificaciones estén deshabilitadas.

## Estrategia de pruebas

### Dominio y comandos

- ownership del programa y de la calendarización;
- rechazo de fechas pasadas;
- cálculo inclusivo de fecha final;
- mapeo secuencial cruzando meses, años y cambios DST;
- programa incompleto permitido solo después de advertencia y confirmación;
- slots vacíos no heredan planes ni producen una notificación diaria;
- reemplazo explícito de la agenda vigente;
- snapshots que no cambian al editar/eliminar el origen;
- snapshot con comidas, alimentos, cantidades y resumen suficiente para renderizar Hoy
  sin consultar el DailyPlan original;
- transiciones válidas e inválidas de estado;
- una sola agenda vigente bajo concurrencia;
- activación hoy después de la hora no crea un envío retroactivo;
- cambiar a una hora pasada hoy aplica desde el próximo día elegible;
- model boundaries, service areas y matrices ejecutables incluyen las entradas nuevas.

### Entregas

- cálculo de vencimiento usando `calendar_date + hora configurada + timezone IANA`;
- dos usuarios en zonas distintas reciben a sus respectivas horas locales;
- ningún cálculo usa `settings.TIME_ZONE`, la zona del servidor o un offset fijo como
  sustituto de la zona de la calendarización;
- el mismo usuario mantiene las 07:00 locales antes y después de un cambio DST;
- actualización de zona recalcula solo entregas futuras elegibles;
- política determinista para horas locales ambiguas o inexistentes;
- un solo evento lógico por `event_key` aunque el scheduler corra dos veces;
- una sola entrega por pareja `(event, subscription)`;
- fan-out idempotente a múltiples dispositivos y alta de un dispositivo antes del
  vencimiento;
- recuperación diaria hasta 2 horas y `skipped` auditable después de la gracia;
- suscripción expirada/desactivada;
- fallo parcial entre varios dispositivos;
- payload discreto y URL interna permitida;
- rechazo de endpoints inseguros, privados o inválidos y cobertura CSRF;
- no enviar durante pausa, después de cancelar o completar;
- comidas sin hora no generan recordatorio.

### Interfaz

- lista solo programas propios;
- estado vacío sin programas;
- advertencia con conteo/fechas vacías para programas incompletos;
- campo de hora precargado a `07:00`, editable y validado;
- preview correcto del primer y último día;
- confirmación de reemplazo;
- degradación sin soporte push o permiso denegado;
- instrucciones de instalación en Home Screen antes de ofrecer Push en iPhone/iPad;
- flujo mobile/PWA y escritorio.

### Verificación por patch

```text
python manage.py check
python manage.py makemigrations --dry-run --check
tests dirigidos de calendarización/notificaciones
python manage.py test
smoke manual en staging con al menos dos zonas horarias
```

## Observabilidad y operación

Métricas mínimas:

```text
calendarizations_scheduled
calendarizations_active
daily_deliveries_due
daily_deliveries_sent
daily_deliveries_failed
daily_deliveries_skipped
notification_events_claimed
push_subscriptions_active
delivery_lag_seconds
```

El runbook debe cubrir:

- rotación/configuración de claves VAPID;
- scheduler detenido o atrasado;
- reintento seguro de una ventana;
- desactivación global de envíos sin borrar calendarizaciones;
- inspección de fallos sin exponer endpoints o claves;
- rollback de UI y worker manteniendo datos compatibles.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Duplicar notificaciones | `event_key` único y reserva atómica antes de enviar. |
| Enviar en una hora incorrecta | Interpretar `07:00` dentro de la timezone IANA de cada agenda y convertir cada fecha a UTC de forma centralizada. |
| Usar accidentalmente UTC o la zona del servidor | Prohibición contractual, API de cálculo única y tests con múltiples zonas cuyos instantes UTC sean distintos. |
| Viaje o cambio de zona | No cambiar agendas silenciosamente; ofrecer actualización confirmada y recalcular solo entregas futuras. |
| Cambios del programa alteran una agenda activa | Snapshot versionado al activar. |
| Push no soportado o denegado | Agenda y vista Hoy siguen disponibles; estado visible y reintento voluntario. |
| iOS fuera de Home Screen | Detectar capacidad y guiar instalación; no prometer Push desde una pestaña Safari normal. |
| Endpoint push malicioso | Validación HTTPS/SSRF, autenticación, CSRF y adapter con timeout/tamaño acotado. |
| Scheduler caído | Ventana de recuperación, delivery lag y alerta operacional. |
| Filtrar información sensible en lock screen | Copy genérico y detalle tras autenticación. |
| Complejidad prematura de workers | Management command idempotente primero; Celery/RQ solo con evidencia operacional. |
| Crecimiento de snapshots/logs | Payload mínimo, índices y política de retención definida antes de producción. |

## Criterios de aceptación del MVP

El MVP CAL00-CAL06 se considera listo cuando:

1. un usuario puede elegir un programa propio, completo o incompleto, y una fecha válida;
2. ve el rango calculado y activa la calendarización con confirmación clara;
3. si el programa está incompleto, conoce qué fechas quedarán vacías y confirma la
   activación; esos días no reciben una notificación de plan;
4. la vista Hoy resuelve correctamente el plan según fecha y zona horaria;
5. editar el programa original no altera los días ya calendarizados;
6. el usuario puede pausar, reanudar y cancelar;
7. el usuario puede conservar `07:00` o configurar otra hora local;
8. una PWA/browser compatible puede suscribirse y recibir una notificación diaria;
9. la notificación llega a la hora local configurada, independientemente de
   la zona del servidor y del offset UTC de otro usuario;
10. tocarla abre el día correcto dentro de una ruta autenticada;
11. dos ejecuciones simultáneas del scheduler no duplican el aviso;
12. permiso denegado o push no soportado no rompe la calendarización;
13. staging completa un smoke real en al menos dos zonas horarias;
14. `check`, migraciones pendientes, tests dirigidos y suite completa quedan verdes;
15. existe un kill switch y un runbook mínimo de operación;
16. activar después de la hora o cambiar a una hora ya pasada no envía avisos tardíos;
17. un evento lógico produce como máximo una entrega por dispositivo;
18. los tests ejecutables de model boundaries y service areas permanecen verdes;
19. iPhone/iPad muestra correctamente el requisito de instalación Home Screen.

## Decisiones CAL00 aceptadas

- `07:00` local es el valor inicial y el usuario puede configurar otra hora.
- Se permiten programas incompletos con advertencia y confirmación explícita; un día
  vacío no genera una falsa notificación de plan.
- Solo puede existir una calendarización vigente (`scheduled`, `active` o `paused`)
  por usuario. La regla debe protegerse con comando transaccional y constraint parcial
  en base de datos, no solo mediante la interfaz.
- La calendarización usa snapshots JSON autocontenidos y versionados, no clones ORM
  completos. `source_program` es nullable con `SET_NULL`; las demás trazas son IDs
  primitivos.
- Evento programado y delivery por dispositivo son persistencias distintas.
- Web Push usa VAPID + `pywebpush` detrás de un adapter y debe aprobar smoke real; el
  scheduler apunta a 5 minutos con fallback a background worker si Render no cumple el
  SLA en staging.
- `Profile.timezone_name` conserva la preferencia base y cada calendarización guarda
  su propia copia auditable.
- Los logs técnicos se retienen 90 días; el historial funcional permanece hasta que
  el usuario decida eliminarlo.

## Fuentes técnicas verificadas en la reevaluación

- [WebKit: Web Push para apps instaladas en Home Screen en iOS/iPadOS](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)
- [MDN: Push API, Service Worker y protección CSRF](https://developer.mozilla.org/en-US/docs/Web/API/Push_API)
- [Render: Cron Jobs, horario UTC y garantía de una sola corrida](https://render.com/docs/cronjobs)
- [PyPI: pywebpush y compatibilidad vigente](https://pypi.org/project/pywebpush/)
