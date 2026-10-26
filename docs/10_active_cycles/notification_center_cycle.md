# Ciclo NC · Centro de notificaciones web y móvil

Status: active
Estado de ejecución: implementación local validada; integración en curso
Fecha: 2026-10-26
Base: `origin/staging` @ `8d071923d752778387ccd5a775486c58c1be2646`

## Objetivo

Reunir en una sola bandeja los acontecimientos que requieren atención del
usuario, con una campana a la izquierda del control para cerrar o contraer el
sidebar y un punto rojo cuando queda algo sin leer.

## Secuencia

| Etapa | Estado | Entregable | Salida |
| --- | --- | --- | --- |
| NC01 · Criterio de eventos | Completada | Propuesta pendiente, invitación dirigida, compartido reclamado y actualización del producto. | Contrato en `docs/00_current/features/notification_center.md`. |
| NC02 · Estado y API | Completada | Proyección cronológica, lectura por usuario y anuncio publicable por staff. | Migraciones, rutas web/API y pruebas de aislamiento aprobadas. |
| NC03 · Interfaces | Completada | Campana con punto rojo y bandeja en web y móvil. | Felipe confirmó el alcance y la ubicación el 2026-10-26. |
| NC04 · Integración | En curso | Suite Django completa (2449 pruebas), pruebas móviles (365), exportación web y comparación con staging aprobadas. | Publicar el commit validado y comprobar CI y entorno de staging. |

## Criterios de aceptación

1. Una propuesta pendiente, una invitación a email verificado, un compartido
   recibido y un anuncio publicado aparecen en orden de fecha.
2. El punto rojo refleja el total sin leer y desaparece tras leer todos los
   elementos desde cualquiera de las dos plataformas.
3. Abrir la bandeja no cambia lecturas. Una acción de lectura no permite acceder
   a objetos de otra cuenta ni a un anuncio todavía inactivo.
4. La invitación mantiene el flujo de verificación de email en web.
5. Los controles son utilizables con lector de pantalla y en ancho móvil.
