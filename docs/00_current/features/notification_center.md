# Centro de notificaciones

Status: current

## Alcance vigente

La campana del encabezado del sidebar web y del menú lateral nativo abre una
bandeja personal. Un punto rojo indica que existe al menos una notificación sin
leer. La bandeja muestra hasta 50 elementos recientes, con fecha, origen,
contenido y acción. El estado de lectura vive en el servidor y se comparte entre
web y móvil; abrir la bandeja no marca todo como leído.

## Eventos incluidos

| Evento | Cuándo aparece | Lectura y destino |
| --- | --- | --- |
| Propuesta | Propuesta visible para el usuario y pendiente de revisión. | Usa `NutritionProposal.is_read`; abre su detalle. Las propuestas finales dejan de aparecer. |
| Invitación dirigida | Invitación pendiente o entregada a una dirección verificada del usuario. | Usa `ShareInvitation.read_at`. En web abre `/i/<id>/`; desde la app abre esa misma página web para conservar la verificación de email. |
| Compartido recibido | El usuario reclamó un recurso y tiene un `InboxItem` no descartado. | Usa `InboxItem.read_at`; abre el detalle de Inbox o del recurso en la app. Si la invitación se leyó antes de reclamarla, el nuevo InboxItem conserva esa lectura. |
| Actualización del producto | Un miembro autorizado del equipo activa un `ProductAnnouncement` con fecha de publicación alcanzada. | Usa `ProductAnnouncementRead`, separado por usuario. Se crea y publica desde Django Admin; no se envía correo ni push. |

El sistema no crea avisos para cada edición, recordatorio de calendario o acción
propia. Los recordatorios de calendario y sus canales de entrega siguen su
contrato independiente. Un enlace compartido sin destinatario identificado no
puede generar una notificación personal hasta que el usuario lo reclame.

## Contratos y permisos

- La lista web y su POST de lectura requieren sesión. El POST comprueba propiedad
  o dirección de email verificada antes de cambiar estado.
- `GET /api/v1/notifications` requiere autenticación móvil. El POST de lectura
  requiere `mobile:write` y vuelve a comprobar acceso al objeto.
- Solo se muestran anuncios activos cuya fecha de publicación ya llegó. Un
  anuncio se crea inactivo; activar es una decisión explícita del equipo.
- La aplicación nunca abre una invitación dirigida como enlace público `/s/`:
  mantiene el flujo web de `/i/` y su verificación de email.
- No hay sondeo continuo ni permisos de notificaciones del sistema operativo en
  este ciclo. La campana nativa actualiza el punto al abrir el menú y la pantalla
  carga el estado al recibir foco.
