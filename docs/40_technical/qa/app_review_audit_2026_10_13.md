# Auditoría de App Review — 13 de octubre de 2026

Status: build 39 tested physically; follow-up local validation complete; device revalidation pending
Fecha: 2026-10-13, America/Santiago
Última validación: 2026-10-14, America/Santiago
Rama inicial: `codex/app-review-audit`
Rama posterior a pruebas físicas: `codex/build-39-physical-fixes`

## Dictamen

**No recomendar todavía el envío a App Review.** La auditoría inicial fue
integrada mediante [PR #111](https://github.com/DidesCabrera/my-scoope/pull/111),
desplegada y compilada en el build 39, commit `2039165ca24c7fbf5835fbc4f3f762ec76d6fa02`.
Felipe completó pruebas físicas de ese candidato y confirmó siete hallazgos.
Las correcciones posteriores se agrupan en una rama basada en el staging actual.
El informe siguiente registra su validación local antes de integrar; no se ha
creado otra build para ese bloque.

El [reporte de pruebas y correcciones del build 39](app_review_build_39_physical_2026_10_14.md)
actualiza el dictamen, registra lo que funcionó y delimita la revalidación pendiente.
Las secciones siguientes conservan la evidencia de la auditoría inicial del 13.

Esta auditoría distingue pruebas automáticas, observaciones de servicios reales
y pruebas que requieren dispositivo/StoreKit/App Store Connect. No convierte una
prueba con evidencia simulada en una compra real ni promete ausencia de rechazos.

## Alcance y procedencia

- Base actualizada: `origin/staging`, commit
  `ec5ddb72142184ff7e44464c84b94196a83b5288`.
- `origin/main`, `b38bf832d0a3238aa15db6970c1b772dcdf7acee`, contiene el mismo
  árbol de producto que esa base. Se verificó el contenido, no sólo los nombres
  de ramas. La integración anterior es [PR #110](https://github.com/DidesCabrera/my-scoope/pull/110).
- EAS confirmó por consulta de sólo lectura que el build iOS 1.0.0 (38), ID
  `968e2e7c-eded-4987-a4db-33ef42cccf2f`, terminó en el perfil
  `testflight-production` desde `b38bf832…` el 13 de octubre.
- El WIP original de `codex/mobile-corrections` se preservó sin modificar sus
  dos archivos. También se guardó su parche en
  `/private/tmp/my-scoope-mobile-corrections-preserved.patch`. Sus treinta
  consultas cada dos segundos no se adoptaron como solución de compra.
- Durante la etapa inicial del 13 no se modificaron las notas personales ni el
  Knowledge Center, y no se hicieron builds o integraciones. El cierre autorizado
  del 14 integró PR #111, desplegó el commit `2039165` y generó el único build 39.
  Las notas y privacidad de Connect se corrigieron y las siete compras quedaron
  preparadas en el mismo borrador. El seguimiento físico se documenta por separado.

La CI de la base pasó en las ejecuciones
[38474122237](https://github.com/DidesCabrera/my-scoope/actions/runs/38474122237)
y [38472044613](https://github.com/DidesCabrera/my-scoope/actions/runs/38472044613).
Esa evidencia corresponde a la base; **no certifica esta rama modificada**.

## Incidente Basic → Pro del build 38

Felipe observó aprobación de Apple mientras la app seguía mostrando Basic;
después Apple y Django mostraron Pro. La consulta real a App Store Server API
confirmó `active / com.myscoope.pro.monthly` para la cuenta interna autorizada.

Se encontraron mecanismos capaces de producir o prolongar esa inconsistencia:
lecturas comerciales cacheadas, confirmación repartida entre callbacks y lecturas
posteriores, escucha ligada a la pantalla y recepción desordenada de transacciones
de la misma cadena. Las pruebas reprodujeron defectos concretos antes de
corregirlos, entre ellos que un Basic antiguo podía reemplazar un Pro nuevo.
No hay una traza completa del iPhone que permita atribuir aquel incidente a una
única causa. La corrección cubre esos mecanismos y evita anunciar éxito mientras
el plan o los créditos todavía no son utilizables.

## Defectos corregidos y evidencia

| Riesgo | Corrección | Evidencia principal |
| --- | --- | --- |
| Confirmar compra con Basic/saldo anterior | El POST devuelve plan y entitlements efectivos; las comprobaciones posteriores omiten caché. La UI muestra verificación pendiente hasta confirmar beneficios. | API de upgrade y `purchase-coordinator.test.ts`; camino normal: un POST, cero polling. |
| Perder recibos al navegar, reiniciar o recibir callback y promesa | Listener en el proveedor raíz de la cuenta, recuperación de pendientes, cola por cuenta y tarea compartida por ID. | Pruebas de duplicados, serialización, restore de consumibles y cierre sólo después de aceptación. |
| Cerrar una transacción no verificada, ocultar otro cierre pendiente o repetir éxito antiguo después de un refund | No se llama a finish después de rechazo/fallo; el reintento de finish no repite el POST aceptado y vuelve a consultar los beneficios actuales. El indicador considera todos los recibos aceptados sin cerrar. | Pruebas de fallo de verificación, fallo de finish, refund antes de reintentar el cierre y dos recibos con un cierre pendiente. |
| Transacción antigua que revierte upgrade o refund | Orden por periodo de compra y evidencia firmada; StoreKit aislado no deshace una decisión posterior del servidor para el mismo recibo. | `test_apple_lifecycle.py`, incluyendo regresiones de Basic atrasado y refund cacheado. |
| Transferir propiedad en una creación concurrente | Se bloquea la cuenta antes de la evidencia; se vuelve a comprobar propietario y ambiente después de resolver la clave única. | Carrera real en PostgreSQL con dos account tokens para el mismo original ID: un propietario. |
| Eventos duplicados, carreras de proveedor y bloqueos del catálogo | Claim, efectos y estado final de Apple comparten transacción; orden de bloqueo de cuenta consistente entre proyecciones/proveedores; joins no bloquean productos de otros clientes. | Cuatro pruebas PostgreSQL: upgrade desordenado, propiedad, webhook/directo de bolsa y evento duplicado. |
| Grace/retry/cancelación interpretados como acceso indefinido o cambio inmediato | Se verifica renewal JWS, su original ID, grace deadline, auto-renew y siguiente producto. Cancelar conserva el periodo vigente; un recibo sin renewal no borra la cancelación verificada. | Adaptador de renewal y lifecycle: grace válido/vencido, retry, cancelación, downgrade programado y reversión de refund de suscripción. |
| Suscripción autorizada ya vencida que mantiene beneficios o tapa otro proveedor | Se vence evidencia antes de seleccionar proveedor; el resolver de entitlements rechaza periodos pasados incluso sin webhook. | Prueba de proveedor alternativo activo y regresiones de accounts/billing. |
| Bolsa duplicada o refund recibido antes de la compra | Recibo único, tombstone refunded previo al grant y reconocimiento de JWS revocado. Los mappings Apple retirados pueden liquidar una compra ya cobrada. | Lifecycle de bolsas, API de mapping retirado y carrera PostgreSQL. Una nueva transacción del mismo SKU concede otra bolsa. |
| Saldo de Pro mostrado aunque una tarea previa impide usarlo | `credit_status` informa reserva pendiente o wallet congelada y muestra cero créditos utilizables; el éxito espera disponibilidad real. | Reserva real Basic → Pro → liberación → nuevo consumo; pruebas móviles para reserva y freeze. |
| Recibo autoritativo antiguo que se restaura después de vencer | Ignorar su contenido viejo también vuelve a proyectar una autorización cuyo plazo ya pasó; el API informa inactive y conserva cualquier otro proveedor vigente. | Regresión HTTP de restauración después de expiry sin notificación, con entitlements Free y evidencia expired. |
| Eventos posteriores a eliminar la cuenta | Se conserva evidencia financiera sin recrear AccountSubscription ni conceder bolsas nuevas a la cuenta inactiva. Un refund actualiza el recibo aunque su wallet haya sido borrada; locks de cuenta preceden al recibo. | Eliminación real en tests, renovación/compra tardía y carrera PostgreSQL eliminación + refund. |
| Caída de certificados Apple presentada como recibo inválido | El estado retryable del SDK se trata como unavailable/503; las firmas inválidas siguen siendo rechazadas y ningún caso concede beneficios. | Tres entradas del adaptador y ambos endpoints de compra, con las excepciones reales del SDK. |
| Excepción Sandbox que permite compras reales con kill switch apagado | Con live apagado, la cuenta autorizada usa directamente verificador Sandbox; producción se rechaza para ambos tipos de producto. | API de suscripción y consumible; ningún grant/ProviderSubscription con evidencia de ambiente incorrecto. |
| Loop indefinido, solicitudes duplicadas o respuesta aplicada a otra cuenta | Cuatro relecturas con backoff y límites de solicitud, reconcile único en vuelo, controles recuperables, sesión con generaciones y escrituras de credenciales ordenadas. | Tests de presupuesto de solicitudes, timeout, logout durante POST/refresh y respuesta atrasada de otra sesión. |
| Cerrar sesión por una caída transitoria al abrir la app | Se conservan credenciales ante fallo temporal y se ofrece reintentar; rechazo auténtico de autorización las elimina. `apiRequest` mantiene identidad estable. | `session-manager.test.ts` y validación de arranque/onboarding. |
| Permiso de micrófono no usado y declaración incompleta de fotos | Image Picker desactiva micrófono explícitamente; manifiesto y labels locales incluyen fotos/vídeos vinculados, sin tracking. | Introspección nativa: cámara/fototeca con propósito propio, sin NSMicrophoneUsageDescription ni RECORD_AUDIO. |
| Consentimiento que promete retención cero no demostrada | Se quitó la promesa de no conservar en OpenAI y se enlazó la política; notas de revisión describen consentimiento, procesamiento y copia opcional. | Código, política actual y documentación oficial de OpenAI. |
| Ciclo de importación detectado al arrancar la app | Las funciones de navegación del picker se aislaron de la pantalla; los paneles ya no importan la pantalla que los usa. | Lint y suite de pickers; recarga del cliente sin el ciclo observado. |

Las rutas públicas existentes y sus operation IDs se conservan. Los campos nuevos
son aditivos; el cliente admite una respuesta antigua sin entitlements mediante
lecturas frescas. El contrato OpenAPI se regeneró. El nuevo endpoint y las
respuestas de compra se separaron en módulos propios sin aumentar los presupuestos
revisados de tamaño o complejidad.

## Validación automática local

Los resultados finales quedan registrados abajo; los logs locales están en
`/private/tmp/my-scoope-*` y no contienen recibos firmados ni credenciales.

| Capa | Resultado / alcance |
| --- | --- |
| Django completo, SQLite | 2.316 pruebas, cero fallos; cinco omitidas por requerir PostgreSQL y ejecutadas allí aparte. El cierre final tardó 437 segundos sobre el código congelado. Las pasadas anteriores no se usaron para certificar funciones que cambiaron después. |
| Concurrencia PostgreSQL | 5/5 pasaron con conexiones paralelas y límites de bloqueo, en un servidor temporal separado de cualquier base existente; incluye eliminación y refund simultáneos. |
| Gate estructural | 102/102: boot, migraciones sin cambios, contrato OpenAPI actual, arquitectura, higiene y registro documental válido. |
| Mobile completo | 269/269, TypeScript y exportación web pasaron sobre el código final. Lint de los módulos finales pasó; auditorías y lint de archivos idénticos se conservaron del gate. |
| Compras críticas | 25/25 pruebas de comportamiento del coordinador; 3 de restore y 11 de sesiones dentro de la suite móvil. No son comprobaciones regex de la lógica de compra. |
| Pruebas de ciclo Apple | 12 casos dentro de la suite completa; API/créditos/bolsas también cubiertos por los bloques focalizados y la suite final. |
| Expiry, eliminación y disponibilidad | 41/41 de lifecycle/API/bolsas genéricas; 13/13 del adaptador y API después de clasificar el fallo retryable del SDK. |
| Deuda | Presupuestos backend y complejidad Python pasaron. Auditoría npm: cero hallazgos críticos, con excepciones existentes revisadas por el repositorio. |
| Configuración nativa | Introspección de permisos y privacy manifest pasó; no sustituye inspección del archive firmado. |

Los primeros intentos móviles detectaron un contrato visual antiguo, una llamada
síncrona a estado en un effect y acceso a `code` de un Error genérico. Se corrigieron
y se ejecutaron sus controles fallidos y las etapas restantes. No se hizo CI
remota ni se obtuvieron resultados para un commit publicado de esta rama.

El cliente iOS de desarrollo existente cargó el código de esta rama mediante
Metro limitado a `127.0.0.1`, con staging como API. Se comprobó el arranque y el
recorrido Inicio → Mi cuenta → Suscripciones y Bolsas, los enlaces legales y la
acción Restaurar compras. La vista inspeccionada en staging no mostró las tarjetas
Basic/Pro; esta comprobación de interfaz **no prueba una compra real ni
la activación visual Basic → Pro**. No se cambió la sesión ni se realizó una compra.
Al terminar se dejó el cliente en su selector de desarrollo y se detuvieron
Metro y PostgreSQL temporales. Los enlaces de dependencias usados para probar
se retiraron del worktree; no forman parte del commit.

## Estado real observado

| Superficie | Observación |
| --- | --- |
| Cuenta demo de producción | `developer@myscoope.com`: Free, activa, correo verificado, MFA no instalado, cero wallets y cero ProviderSubscription autorizadas. No se modificó. |
| Acceso Sandbox | Demo con purpose App Review hasta 2027-01-10; `myscoope@gmail.com` interno hasta 2026-10-19. Debe renovarse el acceso interno si las pruebas continúan después. |
| Apple real | App ID `6804048394`, bundle `com.myscoope.app`; ambos coinciden en la configuración pública de Render con environment production. Pro mensual activo en Apple Server API para la cuenta interna. |
| Catálogo de producción | Readiness: 4/4 suscripciones y 3/3 bolsas, tanto live como sandbox; credenciales de reconciliación disponibles. |
| Activación | `BILLING_APPLE_PURCHASES_ENABLED=false` sigue impidiendo compras live. La excepción autorizada Sandbox permite TestFlight/revisión; live debe habilitarse con el gate de lanzamiento, no durante esta auditoría. |
| Notificaciones | URLs de producción y sandbox en Connect coinciden con `/billing/webhooks/apple-app-store/{production,sandbox}/`. |
| Grupo de suscripciones | Pro mensual/anual nivel 1; Basic mensual/anual nivel 2; Family Sharing desactivado. Los cuatro productos están Prepare for Submission. |
| Consumibles Connect | SKUs 500/1000/2000, tipo Consumable, los tres Prepare for Submission. La ficha de 500 tiene precio, localización, una región habilitada y screenshot de revisión. El estado dice que todavía no se enviaron; no demuestra por sí solo metadata faltante. |
| Borrador de app | Versión 1.0 todavía selecciona build 33 y tiene notas de revisión antiguas que describen sólo Vision local, incompatibles con el procesamiento OpenAI actual. |
| Privacidad publicada | Diez tipos, sin Photos or Videos. La retención opcional de una copia privada requiere incorporarlo; los archivos locales ya están corregidos. |
| Disponibilidad | App disponible sólo en Chile. Apple Silicon Mac y Apple Vision Pro están seleccionados; su compatibilidad no se probó en esta auditoría. |
| Información | Health & Fitness, rating 9+ con excepciones regionales, Apple Standard License Agreement y declaración de no ser dispositivo médico regulado. |
| Enlaces públicos | Privacy, terms, support y refund-policy devolvieron HTTP 200 en una lectura fresca. AASA devolvió HTTP 200 y application/json. El caché del buscador contenía texto anterior y no se usó para juzgar la página actual. |

## Pendientes antes de recomendar envío

1. Aprobar el comportamiento/visual de la corrección, autorizar integración y
   obtener una única CI `full` requerida para el commit candidato. Billing,
   sesiones y configuración nativa son rutas críticas. Después del merge, añadir
   evidencia diferente: salud del despliegue, configuración y smoke de staging.
2. Probar los flujos de la siguiente tabla en iPhone real usando la cuenta
   interna Sandbox. El build 38 permite estudiar el incidente anterior; no puede
   aprobar estas correcciones aún no integradas. Generar un nuevo candidato
   requiere autorización expresa de Felipe y procedencia de commit limpio.
3. Incorporar Photos or Videos en App Privacy, trasladar las notas corregidas de
   `mobile/store/review-notes.es-CL.md`, seleccionar el candidato final y añadir
   los cuatro planes y tres bolsas al envío inicial. Estas acciones no se hicieron.
4. Comprobar precios localizados, disponibilidad Chile y screenshot de revisión
   de cada IAP en la presentación final. Confirmar contraseña demo mediante login
   real sin incluirla en informes; mantener demo Free antes del envío.
5. Validar Mac/Vision Pro si se conserva esa distribución, o decidir excluirlos
   antes de publicar. Inspeccionar también el archive firmado, cámara/fototeca,
   Sign in with Apple, revocación al eliminar una cuenta desechable autorizada,
   deep links y entrega de notificaciones.
6. Confirmar controles de datos/retención contratados de OpenAI y configuración
   de diagnóstico del candidato. `store:false` no prueba por sí solo Zero Data
   Retention. Antes de lanzamiento live, comprobar permisos comerciales y
   habilitación de compras reales con autorización.

### Matriz física y de Apple pendiente

| Escenario | Resultado que debe quedar evidenciado |
| --- | --- |
| Free → Basic mensual/anual y Free → Pro mensual/anual | Precio/periodo Apple correctos; estado verificando tras aprobación; beneficios utilizables y cierre del recibo una sola vez. |
| Basic → Pro, ambos periodos | Upgrade real inmediato según Apple; ninguna vuelta a Basic por callback antiguo, foco o restore. |
| Pro → Basic; mensual ↔ anual de igual nivel | Mantener beneficios vigentes; mostrar cambio programado sólo con renewal verificado y aplicarlo en la fecha Apple. |
| Cancelar en el sheet, aprobación diferida y retorno sin recibo nuevo | Liberar controles y mensaje correcto, sin fingir cobro, éxito o rechazo definitivo. |
| Bolsas 500/1000/2000 y repetición del mismo SKU | Cada nuevo transaction ID concede una bolsa; callback repetido no vuelve a conceder; UI coincide con saldo gastable. |
| Red perdida antes/después de aceptación y antes de finish | No recompra; restore/retry recupera el recibo, no repite grant, no queda busy indefinidamente. |
| Salir de pantalla y terminar/reabrir la app durante compra | Recuperar transacción pendiente desde raíz y confirmar beneficios antes del mensaje final. |
| Logout/cambio de My Scoope con el mismo Apple ID | El recibo sólo recupera la cuenta propietaria; ninguna respuesta atrasada cambia la otra sesión. |
| Restore vacío, activo, vencido, reembolsado y con consumible sin finish | Resultado honesto por cada recibo; no activar beneficios antiguos ni duplicar saldo. Las bolsas ya consumidas no se reconstruyen desde restore de Apple. |
| Renovación, cancelación, grace, retry, expiración y refund con Apple real | Notificación/reconciliación actualiza Django, entitlements y UI con las fechas firmadas; revisar reversión de refund y déficits de bolsas con soporte. |
| Upgrade durante tarea de IA con reserva y wallet congelada | No mostrar créditos utilizables ni éxito final prematuro; liberar la reserva o indicar soporte y recuperar sin una nueva compra. |
| Demo, privacidad, permisos, soporte y eliminación | Login funcional, demo Free inicial, consentimiento antes de enviar imagen, copia opcional eliminable y cuenta desechable realmente revocada. |
| Eliminación con compra o tareas pendientes | Ningún evento tardío recrea datos personales o beneficios. Evidencia financiera retenida y refund correctos; comprobar también el cierre de trabajos de IA activos en el dispositivo/servicio. |

## Fuentes y límites

- [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/): completitud de la app, compra/restauración y consentimiento para datos compartidos.
- [Enviar el primer IAP](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/submit-an-in-app-purchase): la primera presentación de ese tipo de IAP/suscripción debe incluir una nueva versión de la app.
- [Estados de IAP](https://developer.apple.com/help/app-store-connect/reference/in-app-purchases-and-subscriptions/in-app-purchase-statuses/): Prepare for Submission significa creado y aún no enviado.
- [App Privacy](https://developer.apple.com/app-store/app-privacy-details/): declarar los datos recogidos por la app y sus socios. La copia opcional retenida motivó corregir Photos or Videos.
- [Identificador del manifiesto](https://developer.apple.com/documentation/bundleresources/app-privacy-configuration/nsprivacycollecteddatatypes/nsprivacycollecteddatatype): `NSPrivacyCollectedDataTypePhotosorVideos` conserva exactamente esa capitalización.
- [Datos en OpenAI API](https://developers.openai.com/api/docs/guides/your-data): Responses storage y controles de retención son mecanismos distintos; no se verificó la elegibilidad ZDR del proyecto del usuario.
- [Expo SDK 57](https://docs.expo.dev/versions/v57.0.0/): referencia exigida por `mobile/AGENTS.md`; se inspeccionó también el código instalado de expo-iap 5.5.1 y del SDK oficial Apple.

Los tests automáticos verifican reglas con evidencia controlada; las cinco
carreras usan PostgreSQL real. La consulta de Apple prueba el estado de una
suscripción Sandbox y acceso a Server API, no todos los escenarios ni el archive
futuro. Se comprobó además que el bundle servido al cliente contiene los archivos
de esta rama, pese al enlace local a dependencias del checkout principal. Las
comprobaciones nativas, comerciales y de Connect pendientes son
condiciones concretas para el próximo gate, no aprobaciones implícitas.
