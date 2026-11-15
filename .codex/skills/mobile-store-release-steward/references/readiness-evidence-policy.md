# Política de evidencia y revalidación

## Propósito

Conservar trabajo válido entre ciclos de publicación y repetir solo la evidencia
afectada por un cambio real. La fecha de una verificación ayuda a evaluar su
vigencia, pero no la invalida por sí sola.

## Registro mínimo por gate

Cada gate mantenido debe permitir responder:

- `scope`: qué afirmación demuestra;
- `state`: `resolved_current`, `revalidate`, `pending`, `unverified` o
  `not_applicable`;
- `evidence_ref`: enlace o identificador de la prueba, sin secretos;
- `verified_at` y `verified_by`;
- `applies_to`: aplicación, plataforma, versión, build, commit, storefront o
  configuración cubierta;
- `source_ref` y `source_checked_at` cuando dependa de una regla externa;
- `expires_at` solo cuando exista un vencimiento real;
- `revalidation_triggers`: cambios concretos que invalidan la evidencia;
- `owner` y `next_action` para estados abiertos.

## Cuándo reutilizar evidencia

Reutiliza una verificación cuando su alcance todavía coincide, la fuente sigue
vigente y ningún disparador ocurrió. Ejemplos frecuentes:

- propiedad y accesibilidad de una URL de soporte sin cambios;
- aprobación legal de un documento cuyo contenido y jurisdicción no cambiaron;
- configuración de una cuenta o contrato que sigue activo;
- metadata permanente que aún representa correctamente el producto.

Recuperar el enlace o identificador perdido es preferible a repetir el trabajo.

## Cuándo revalidar

Marca `revalidate` únicamente cuando exista evidencia previa y al menos un
disparador aplicable:

- cambió el binario, SDK, permiso, entitlement, flujo o servicio que afecta el
  gate;
- cambió la recopilación, uso, asociación o seguimiento de datos, incluidos SDK
  de terceros;
- cambió la política de privacidad, URL legal, mecanismo de eliminación o
  posibilidad de revocar consentimiento;
- cambió la oferta, precio, storefront, compra integrada, suscripción o forma de
  acceder a contenido pagado;
- cambió metadata, capturas, audiencia, clasificación etaria, contenido o una
  afirmación visible al usuario;
- cambió el requisito oficial aplicable o Apple solicitó información nueva;
- venció un contrato, certificado o evidencia con expiración definida;
- un incidente, rechazo o hallazgo contradice la prueba anterior;
- se sustituyó el candidato y la evidencia estaba ligada al build exacto.

Registra siempre la evidencia anterior y el disparador. Si cualquiera de ambos es
desconocido, usa `unverified` hasta investigarlo.

## Capas de vigencia

| Capa | Ejemplos | Regla de repetición |
| --- | --- | --- |
| Base reutilizable | propiedad de URLs, contratos activos, configuración estable | Solo por disparador o vencimiento documentado |
| Versión | descripción, novedades, capturas, notas de revisión, edad | Cuando cambie la versión, el alcance o la representación del producto |
| Build | estabilidad, login, compras, eliminación, permisos, privacidad observada | Sobre el candidato exacto |
| Post-lanzamiento | disponibilidad, precios reales, compras, errores y métricas | Después de publicar y cuando cambie la liberación |

## Privacidad

No se repite una auditoría completa de privacidad solo porque comienza otro ciclo.
Primero compara el delta desde la última evidencia: datos, finalidad, asociación,
tracking, SDK, permisos, retención, eliminación, consentimiento y terceros. Si el
delta es vacío y la declaración publicada sigue cubriendo el producto, conserva
el estado `resolved_current`. Si no puede observarse la declaración publicada o
la evidencia anterior, usa `unverified`.

Apple exige mantener las respuestas de App Privacy exactas y actualizadas cuando
cambian las prácticas propias o de terceros. También exige que metadata, privacidad,
capturas y previews representen la experiencia actual. Verifica la formulación
vigente en fuentes oficiales antes de una recomendación de envío.

## Fuentes oficiales de control

Rutas verificadas el 2026-11-14; revisa su contenido vigente antes de un envío:

- App Privacy: `https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy/`
- propiedades requeridas por aplicación y versión: `https://developer.apple.com/help/app-store-connect/reference/app-information/required-localizable-and-editable-properties`
- proceso de envío: `https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review`
- App Review Guidelines: `https://developer.apple.com/app-store/review/guidelines/`
