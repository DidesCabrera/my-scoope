# 0193 — Sharing separa recurso, invitación, claim e Inbox

Status: accepted
Date: 2026-09-11

## Contexto

El sharing original usa cinco modelos por tipo de entidad. Cada registro mezcla el
objeto compartido, el destinatario por email, el token, la aceptación y estados de
Inbox. Ese diseño permitió el primer flujo web, pero no representa correctamente un
enlace reenviable, múltiples receptores, snapshots, revocación ni Share Sheet móvil.

## Decisión

- `sharing` es un bounded context propio de application.
- `ShareResource` representará contenido portable mediante un snapshot inmutable,
  limitado y versionado; no hará público el objeto privado original.
- `ShareInvitation` representará destinatarios conocidos y exigirá coincidencia con
  un email verificado para ser reclamada.
- `ShareClaim` será explícito, idempotente y separado de abrir un enlace.
- `InboxItem` será la entrega persistente a una cuenta y no pertenecerá a email.
- Los enlaces serán no listados, revocables y gobernados por una política `none`,
  `single` o `multiple`.
- El token es una credencial de acceso al preview, no prueba identidad ni autorización
  para reclamar una invitación dirigida.
- La primera vertical será DailyPlan. Otras entidades entrarán mediante adaptadores
  explícitos una vez validado el contrato.
- Email, Share Sheet, copiar enlace y cards serán adaptadores de distribución; no
  contendrán reglas de ownership o claim.
- Los modelos legacy permanecerán compatibles hasta migrar Inbox y rutas antiguas.

## Consecuencias

La migración será incremental y temporalmente coexistirán dos representaciones. La
seguridad del flujo legacy debe endurecerse antes de ampliar la distribución. El nuevo
núcleo no dependerá de views, UI ni builders de canal, y todo snapshot deberá declarar
su versión y política de privacidad.
