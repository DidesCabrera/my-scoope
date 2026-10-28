# Inbox

Status: current
Date: 2026-10-28
Audience: developers and AI assistants

## Estado

Feature vigente.

## Concepto

Inbox recibe claims normalizados de recursos compartidos y permite revisar snapshots,
gestionar estado visual y guardar una copia propia en la biblioteca o en comparaciones.

Preview, claim y save son acciones distintas. Abrir un GET público nunca reclama ni
guarda contenido. Un claim es explícito e idempotente; guardar hidrata una entidad
propiedad del receptor. Revocar o expirar el recurso original impide nuevas acciones,
pero no elimina un Inbox reclamado o una copia ya guardada.

Foods, Meals, DailyPlans, Programs y SavedComparisons usan el mismo límite
resource/invitation/claim/Inbox. Los registros legacy solo existen como compatibilidad
de lectura o rollback y no deben recibir nuevas escrituras.

## Reglas

- Mantener Inbox como sección de herramientas.
- Las acciones de guardado/eliminación deben vivir en commands si mutan estado relevante.
- Los badges/notificaciones deben derivarse de datos preparados, no de lógica dispersa en templates.
- Las invitaciones dirigidas exigen identidad verificada además de poseer el enlace.
- No leer el objeto privado del emisor para renderizar o guardar: usar el snapshot.
