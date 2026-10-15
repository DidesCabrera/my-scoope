# Test físico del build 40 — 15 de octubre de 2026

## Estado y alcance

El recorrido 1–12 de Felipe se realizó en un iPhone con My Scoope 1.0.0 (40),
EAS `02f08e6d-c21b-482e-adfc-cf44a3f2b198`, commit
`19384f5bf4fe190ee0e0ff99abb2ce8491d91e7a` (PR 112).
Confirmó tres incidencias. **El build 40 no está aprobado para App Review.**

La investigación y los cambios siguientes son locales, en
`codex/build-40-physical-fixes`. La rama se creó desde `origin/staging`
`45233cd3ad0d49126934e13043367abcda73e937` y se avanzó localmente hasta
`origin/main` `19384f5` para conservar íntegra PR 112, que staging aún no contenía.
No se cambió ninguna rama remota ni se inició otra build. Felipe está trabajando
en paralelo; la integración requiere nueva autorización y volver a comprobar
el staging más reciente antes de coordinarla. No se modificó el Knowledge Center.

## 1. Precio de las cards distinto de Apple

Felipe comprobó directamente en Apple Basic mensual $3.990 CLP, Basic anual
$34.990 CLP, Pro mensual $6.990 CLP y Pro anual $59.990 CLP. Las cards y bolsas
seguían mostrando USD. El sheet nativo cobró los importes correctos.

La inspección de esta revisión confirma que las cards consumen el `displayPrice`
del producto cuyo ID coincide con el configurado por el servidor. No hay un
fallback monetario en esos componentes. La versión instalada de expo-iap 5.5.1
consulta OpenIAP 3.4.0, que llama `StoreKit.Product.products(for:)`; el bridge
traslada `Product.displayPrice`, `price` y `priceFormatStyle.currencyCode`.
Por tanto, **usar ese campo y superar un test no demuestra la corrección física**.

Hay un [reporte primario con el mismo síntoma en StoreKit 2/TestFlight](https://developer.apple.com/forums/thread/845478),
incluyendo storefront FRA/EUR estable con productos USD y una reproducción
nativa. Es evidencia de una hipótesis; no prueba por sí sola la causa del iPhone
de Felipe. No se afirma que publicar en producción lo solucione.

Se preparó instrumentación específica y protección para la siguiente validación:

- Parche acotado de expo-iap: consulta `Storefront.current` con ID, país, moneda
  nativa y momento de lectura; escucha `Storefront.updates`. La moneda procede de
  Apple en iOS 17 o posterior, sin inferirla de la región del dispositivo. En
  iOS 16.4 queda explícitamente desconocida.
- Cada consulta guarda en memoria los IDs solicitados y los productos recibidos,
  `displayPrice`, precio numérico, moneda, contexto antes/después y motivo de
  carga. El historial conserva como máximo 20 muestras y excluye recibos,
  tokens, identificadores de cuenta y descripciones arbitrarias. No se envía a
  terceros ni se persiste con el perfil del usuario.
- En Sandbox/desarrollo, Suscripciones y Bolsas → acciones → Diagnóstico de
  precios permite leer y copiar esas muestras. No se añade esa acción a una
  sesión normal de producción.
- Un cambio del storefront o salida al segundo plano invalida las cotizaciones
  pendientes. Hay recarga al conectar, abrir la pantalla, regresar, cambiar
  storefront y terminar compra/restauración.
- Si la moneda nativa del producto contradice la moneda del storefront, se
  descarta la cotización y se vuelve a consultar una vez. Si persiste, se muestra
  un aviso humano y se bloquea comprar con ese precio. No se convierte ni se
  sustituye por CLP fijo o una tabla propia.

**Pendiente:** capturar esas muestras en el iPhone y comparar cada card con el
sheet Apple para el mismo SKU/storefront. Ocultar una cotización inconsistente
es una protección, no satisface por sí solo el criterio de mostrar el precio
correcto. La causa del precio en ese dispositivo sigue sin confirmación de
ejecución; este punto permanece abierto. El iPhone físico disponible para
desarrollo figuraba `unavailable`; no se generó otra app para investigarlo.

## 2. Errores crudos al navegar sin conexión

Error observado: `fetch failed: UnexpectedException: La conexión a Internet
parece estar desactivada. (at ExpoModulesCore/Promise.swift:56)`, además de una
variante con NSURLErrorDomain/ConcurrentFunctionDefinition.

La causa local era `userFacingError`: devolvía sin filtrar `Error.message`.
Restore tenía un filtro propio y por eso sí mostraba un mensaje correcto.

Se centralizó la detección de fallos de conexión, incluyendo wrappers `cause`
y `nativeError`, con recorrido acotado y protección ante ciclos. Se filtran
excepciones, trazas y nombres internos también en respuestas API desconocidas.
Cuenta, Suscripciones y Today permiten reintentar y mantienen sus datos ya
disponibles cuando falla la lectura. Los mensajes propios de validación se
conservan.

**Pendiente físico:** modo avión y Wi-Fi realmente apagado; recorrer únicamente
Cuenta, Suscripciones y Today y comprobar texto humano, datos conservados y
recuperación al reconectar.

## 3. Plan vencido obsoleto al reanudar

Felipe canceló la renovación Pro, esperó la expiración y volvió a la app. La
pantalla mantuvo Pro hasta navegar. Después actualizó correctamente a Free,
conservó 3.000 comprados y retiró sólo 988 incluidos restantes.

La causa local era una condición de `AppState`: sólo actualizaba beneficios si
la fase era `pending` o `activating`. Además, Cuenta guardaba otra copia local
de los entitlements que no seguía las actualizaciones del coordinador.

La reanudación actualiza siempre la instantánea y reconcilia con Apple, aunque
no haya compra pendiente. Cuenta y Suscripciones consumen la instantánea común.
Las conciliaciones y aceptaciones de recibos comparten una cola, evitando que
una respuesta anterior a una compra sobrescriba sus beneficios nuevos. También
se retira el aviso antiguo de plan activo si el plan confirmado cambió.

Las solicitudes coincidentes comparten el trabajo. Una reanudación que ocurre
durante una consulta anterior solicita una actualización posterior. Si falta
red, se conserva el estado conocido y se reintenta sólo en primer plano, con
esperas de 3, 6 y hasta 15 segundos. El reintento se detiene al recuperar conexión
o salir de la cuenta; no se añade sondeo periódico después de un éxito.

**Pendiente físico:** dejar Suscripciones abierta, cancelar/esperar el cambio
Sandbox y volver sin navegar ni restaurar. Debe actualizar plan y saldo solo.

## Evidencia conservada del build 40

No repetir el recorrido 1–12. Quedaron aprobados logout/cambio de usuario,
aislamiento de cuentas, uso de saldo comprado desde Free, compra Basic → Pro,
acreditación y recuperación de bolsas sin duplicación, restore online/offline,
expiración con conservación del saldo comprado, notificaciones y Asistente.
Today, bibliotecas, Cuenta, legal y soporte pasaron. Se conserva la evidencia
física anterior de cámara, galería y privacidad porque no se cambió ese flujo.

## Validación local de estas correcciones

El primer cierre dirigido aprobó 52 pruebas funcionales, con lint de los
archivos modificados. Incluye el error real de Expo observado, AppState/resume,
recuperación de red, expiración con saldo comprado, carreras de reconciliación
y pruebas de cotizaciones que contradicen un storefront estable. Estas últimas
usan datos controlados y **no equivalen a evidencia del StoreKit del iPhone**.

El parche se comprobó contra el archivo exacto de expo-iap 5.5.1 sin modificar
las dependencias compartidas. Su sintaxis Swift y los tipos/disponibilidad del
probe se comprobaron contra el SDK real de iOS 26 para destino iOS 16.4. No se
ha enlazado, firmado ni instalado una app con el parche.

El gate móvil completo se ejecutó una vez. Auditoría de dependencias, presupuesto
de pruebas, lint global y tipos aprobaron. La suite ejecutó 301 casos: 299
aprobaron y dos controles de fuente detectaron un contrato anterior de Cuenta y
un indicador de scroll del diagnóstico. Se corrigieron ambos y aprobaron los
14 casos de sus dos archivos, con lint de lo cambiado. Se completó también la
exportación web. El último ajuste para retirar el aviso de tienda al recuperar
conexión aprobó sus seis casos relacionados y lint. No se repitieron tipos ni
las 301 pruebas por ese ajuste acotado. El presupuesto no se amplió.

No hay evidencia nueva de ejecución física de los tres puntos. No se solicitó
CI remota, PR, merge, despliegue ni candidato adicional. La siguiente revisión
física queda limitada a estos tres fallos y exige nueva autorización antes de
integrar o compilar.
