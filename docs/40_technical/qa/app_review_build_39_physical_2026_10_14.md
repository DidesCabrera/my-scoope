# Pruebas físicas del build 39 y correcciones — 14 de octubre de 2026

Status: local validation complete; next physical candidate pending
Fecha: 2026-10-14, America/Santiago
Rama: `codex/build-39-physical-fixes`

## Procedencia y alcance

Felipe realizó el test físico en iPhone sobre My Scoope 1.0.0 (39), EAS ID
`252884c4-172d-4338-95e9-004cc6c4d966`, commit
`2039165ca24c7fbf5835fbc4f3f762ec76d6fa02`, perfil `testflight-production`.
El reporte fue entregado desde el chat de pruebas a «Auditoría final App Store
sin errores». Corresponde a pruebas reales de ese candidato, no a tests simulados.

Se usó la cuenta My Scoope autorizada para Sandbox y una cuenta Apple Sandbox
con storefront Chile. Fue necesario separar la cuenta real de Contenido y
compras antes de probar. La cuenta demo `developer@myscoope.com` debe permanecer
Free; no se modificaron cuentas reales durante estas correcciones locales.

La rama de corrección parte de `origin/staging`, commit
`45233cd3ad0d49126934e13043367abcda73e937`, cuyo árbol de producto es idéntico al
del candidato 39. El WIP anterior, las notas personales y el Knowledge Center
quedan fuera del alcance. Este bloque reúne los siete fallos del reporte.
No se crea ni publica otro build sin la autorización explícita de Felipe.

## Hallazgos y correcciones

| Hallazgo físico | Causa comprobada y cambio local | Evidencia y límite |
| --- | --- | --- |
| Logout vuelve al login, pero el navegador reutiliza la identidad anterior y dificulta cambiar de cuenta. | La sesión OAuth compartía cookies. iOS solicita una sesión efímera; la autorización muestra la cuenta y permite «Usar otra cuenta» mediante POST protegido por CSRF. Cada intento tiene un estado nuevo; los callbacks y respuestas anteriores no cambian la sesión actual. Logout retira la UI autenticada antes de esperar al servidor y descarta errores de generaciones anteriores. | Tests de cambio de identidad con CSRF, generaciones de sesión y callbacks tardíos. En el simulador: A con 1.000 créditos→logout→login vacío→B con cero, sin heredar identidad ni saldo; logout voluntario sin aviso de sesión vencida. Repetir con el candidato físico. |
| Las tarjetas y bolsas muestran USD mientras la hoja Apple cobra en CLP. | `expo-iap` 5.5.1 conserva el primer producto recibido para cada ID en su hook. El catálogo propio usa la consulta nativa fresca, reemplaza IDs y comprueba storefront antes y después. Refresca al entrar, volver al primer plano, restaurar y comprar; una consulta fallida retira ofertas antiguas y ofrece reintentar. | Cuatro tests de catálogo cubren USD→CLP, bolsas, cambio durante consulta, respuestas desordenadas y productos ausentes. La fuente nativa OpenIAP 3.4.0 consulta `StoreKit.Product.products(for:)` en cada fetch. Los precios reales requieren revalidación en iPhone. |
| Avisos persistentes o apilados; cancelar Pro anual vuelve a mostrar «Tu plan Pro ya está activo» por un recibo mensual antiguo. | Los avisos distinguen el intento actual del replay histórico y de las renovaciones. La cancelación cierra en silencio; restore muestra un resumen; un cambio programado muestra fecha, sin afirmar activación. Salir de la pantalla o comenzar otra acción limpia los avisos. La verificación financiera continúa aunque el aviso se descarte. | Siete regresiones de avisos y 25 casos del coordinador, incluyendo cancelación, mismo SKU antiguo, renovación concurrente, blur durante verificación y cambio ya programado. |
| Restore sin conexión expone `UnexpectedException`, `NSURLErrorDomain` y rutas Swift. | Los errores nativos se convierten en una explicación de conexión y reintento. Los errores conocidos del servidor conservan su indicación específica. El estado de restauración se libera en `finally`. | Tests con el texto nativo real y fallos del servidor; tests existentes de restore fallido y recuperación. Falta repetir modo avión en el candidato físico. |
| Al vencer Pro y volver a Free, las dos bolsas compradas permanecen pero la UI muestra cero y no permite usarlas. | El display forzaba cero en Free y la reserva de créditos rechazaba ese plan. Free ahora conserva el saldo comprado visible y utilizable; pierde sólo el aporte incluido. Sin saldo comprado sigue bloqueado y conserva protecciones de freeze/reserva. Comprar bolsas nuevas sigue requiriendo Basic o Pro. | Transición Pro→Free con 1.000 créditos comprados, reserva y consumo reales en tests; casos Free sin fondos y wallet congelada. API y UI local muestran 1.000. Revalidar vencimiento Sandbox físico. |
| «Activar» no hace nada después de denegar notificaciones; volver de Ajustes no actualiza de inmediato. | Permiso denegado muestra «Abrir Ajustes» y abre la configuración de la app. Permiso sin decidir solicita la autorización nativa. Foco y retorno al primer plano consultan el permiso y sincronizan automáticamente la agenda y su estado visible. | Tests de selección de acción y proyección de recordatorios. En el simulador se denegó sólo el permiso de My Scoope: al regresar apareció «Abrir Ajustes», abrió la configuración correcta y, tras restituir el permiso, la app se actualizó sin pulsar Sincronizar. El estado original del permiso quedó restaurado. Revalidar físicamente con un programa activo. |
| Notificaciones son difíciles de encontrar y dependen de tener programa activo. | Mi cuenta incorpora «Notificaciones y recordatorios». La tarjeta de permiso existe también sin programa; explica cómo activar y calendarizar uno para recibir avisos. | Acceso y tarjeta sin programa comprobados en el simulador local. |

Fuentes de implementación para precios: hook instalado `mobile/node_modules/expo-iap/src/useIAP.ts`
(versión 5.5.1, `mergeWithDuplicateCheck`) y
[OpenIAP 3.4.0, consulta nativa](https://github.com/hyodotdev/openiap/blob/3.4.0/packages/apple/Sources/OpenIapModule.swift).
La clasificación de renovaciones usa los campos nativos de
[StoreKitTypesBridge 3.4.0](https://github.com/hyodotdev/openiap/blob/3.4.0/packages/apple/Sources/Helpers/StoreKitTypesBridge.swift).

## Comportamiento aprobado por Felipe en el build 39

- Free→Basic y Basic→Pro aplicaron beneficios en aproximadamente 2–4 segundos,
  sin revertir al plan anterior.
- Una bolsa de 500 acreditó exactamente 500; restaurar no duplicó saldo.
- Restauración normal tomó aproximadamente 7–10 segundos. Sin conexión conservó
  plan y saldo correctos; al recuperar la red pudo restaurar.
- Cerrar forzosamente la app durante una bolsa cobrada recuperó la compra al
  volver a abrir, sin exigir otra compra.
- El vencimiento Sandbox volvió a Free. La conservación contable de bolsas fue
  correcta; su visibilidad y uso son el defecto descrito arriba.
- Cancelar Pro anual conservó Pro mensual y no produjo cobro ni cambio; falló
  sólo la confirmación visual.
- Cámara, permisos, preview, cancelación y galería funcionaron sin crashes.
- Today, programas, librerías, búsqueda, detalle, crear/editar/eliminar alimentos,
  Asistente y navegación funcionaron en los recorridos realizados.
- Privacidad, términos, reembolsos, soporte y reportar incidencias funcionaron;
  el destino de soporte observado fue `felipe@myscoope.com`.
- Se detectó permiso denegado. Con permiso concedido, se observaron 26 avisos
  locales sincronizados.

Precios observados directamente en la hoja de Apple, Chile:

| Plan | Mensual | Anual |
| --- | --- | --- |
| Basic | CLP 3.990 | CLP 34.990 |
| Pro | CLP 6.990 | CLP 59.990 |

Son evidencia de ese storefront y momento, no precios fijos codificados para
otros países. La UI debe usar el texto localizado devuelto por la tienda.

## Validación local del bloque

- 37 tests del servidor aprobados: proyección y transición de créditos,
  autoridad de configuración de IA, bolsas y cambio de cuenta OAuth con CSRF.
- Ruff de los cinco archivos Python modificados aprobado.
- 61 casos móviles relacionados cubiertos por las ejecuciones enfocadas;
  la última ejecución del coordinador y avisos aprobó 32/32. Lint de todos los
  archivos móviles modificados aprobado, sin typecheck global en cada ajuste.
- Se ejecutó una vez `scripts/ci_mobile_checks.sh` al cerrar el bloque de sesión
  y compras: auditoría de dependencias, presupuesto de tests, lint y TypeScript
  aprobados. La suite cubrió 287 casos; el único fallo fue una aserción antigua
  que exigía `$0/mes` para Free. Se actualizó a `Gratis` y pasaron los cuatro
  casos de ese archivo; se completó la exportación web local. Tras corregir el
  aviso visto en logout se repitieron sólo los 15 casos de sesión/OAuth, el lint
  del archivo afectado, TypeScript y la exportación, todos aprobados. Los otros
  casos conservan el mismo contenido validado; no se repitió la suite completa.
- Presupuesto de complejidad Python y registro documental estricto aprobados,
  con cero hallazgos documentales. No hay cambios de esquema o dependencias.
- Cliente de desarrollo conectado a una base SQLite temporal aislada. Cuenta
  local A: Free con 1.000 créditos ficticios; B: Free sin saldo. Esos grants son
  fixtures locales, no transacciones Apple. Inicio de sesión A, saldo visible,
  cambio a B, logout y acceso a recordatorios sin programa comprobados. La app
  también detectó automáticamente los cambios de permiso realizados en Ajustes.
- El cierre posterior requiere integración por PR con CI `full`, comprobación
  del despliegue y próximo candidato físico autorizado. La CI exitosa del build
  39 no certifica estas modificaciones posteriores. La validación móvil local
  está cerrada; no hace falta repetir
  `ci_mobile_iteration.sh`, cuyo contenido ya cubrió el gate completo.

Capturas locales del recorrido: `/private/tmp/my-scoope-local-free-credits.png`,
`/private/tmp/my-scoope-local-account-choice.png`,
`/private/tmp/my-scoope-local-account-b.png` y
`/private/tmp/my-scoope-local-reminders-denied.png`. Son evidencia de UI local,
no de una compra Apple real.

## Única revalidación física pendiente

Una vez cerrado e integrado este bloque, el próximo candidato autorizado debe
revalidar juntos los siete hallazgos, conservando los recorridos aprobados.
No hace falta repetir toda la auditoría de formularios y privacidad para probar
estas correcciones.

También siguen pendientes los casos financieros que el reporte no certifica:
Pro→Basic, cambios mensual↔anual del mismo nivel y variantes anuales Basic/Pro;
aprobación diferida/interrumpida; reembolso Sandbox real y déficit de créditos;
grace y reintento de facturación si se incluyen en el alcance de lanzamiento.
El borrado de cuenta debe probarse sólo con una cuenta desechable, comprobando
que entregas tardías de IAP/IA no la recrean. Confirmar demo Free al finalizar y
precios correctos tras cambiar storefront y reiniciar.

Los tests automáticos prueban las decisiones del código; el simulador prueba el
flujo local. Ninguno sustituye la hoja de compra, renovación o reembolso real en
StoreKit. El build 39 publicado todavía no contiene este bloque de correcciones.
