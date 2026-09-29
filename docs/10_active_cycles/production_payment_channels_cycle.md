# Ciclo de activación productiva de recaudadores

Status: active (PPC00 en curso; ningún canal completado en producción)
Date: 2026-09-29
Cycle code: PPC
Owner: producto/operación My Scoope

## Objetivo y regla de cierre

Dejar **Paddle, App Store y Google Play** vendiendo en producción los cuatro
precios de suscripción y las tres bolsas de créditos aprobadas, con beneficios
correctos, cobros trazables, conciliación, soporte de reembolsos y operación
continua. Mercado Pago permanece legacy y fuera de este ciclo.

La decisión comercial
[`0201`](../20_decisions/0201-commercial-launch-plans-and-owned-library.md)
es la autoridad para precios, planes y beneficios. Este ciclo no vuelve a definir
esos valores. `accounts` decide el acceso y los créditos; `billing` conserva y
verifica la evidencia del proveedor. Ningún retorno de checkout, captura de
pantalla ni mensaje de éxito concede beneficios por sí solo.

**No marcar `completed` por tener código desplegado, productos visibles o compras
en sandbox.** El cierre exige evidencia productiva por los tres canales y la
primera conciliación de liquidación del dinero al receptor. Si el ciclo técnico
termina antes del primer desembolso del proveedor, registrar `active — liquidación
pendiente`, no `completed`.

## Punto de partida conocido

| Canal | Validado hasta ahora | Brecha principal |
|---|---|---|
| Paddle | Catálogo sandbox; bolsa de 500 acreditada en staging; Pro anual de CLP 59.990 registrada como pago aprobado, suscripción autorizada y plan Pro efectivo desde billing. | Completar otras ofertas y eventos de ciclo de vida; configurar/verificar cuenta y catálogo live; probar cobro real. |
| Google Play | Cuatro precios visibles y botones habilitados en Android; compra de 500 créditos y reembolso conciliado de forma idempotente en staging. | Probar suscripciones y su ciclo de vida; publicar cliente Android actualizado; habilitar reconciliaciones después de la prueba; comprobar compra real. |
| App Store | Integración de repositorio y compilación iOS de staging preparada; envío de Expo a App Store Connect completado, disponibilidad en TestFlight no verificada. | Completar TestFlight físico, compras/restauración/eventos/reembolsos sandbox, aprobación comercial y compra real. |

Este es un **inventario inicial**, no prueba de estado live. Al comenzar PPC00 se
vuelve a leer cada consola y el despliegue efectivo; cualquier diferencia se
registra antes de cambiar catálogo, cuentas o flags. La rama de trabajo y su
commit no son evidencia de una transacción ni de una liquidación.

### Bitácora PPC00 (2026-09-29)

- [x] Confirmar que Paddle Sandbox registra una transacción de Pro anual por
  CLP 59.990 y otra de la bolsa de 500 por CLP 2.990. El servidor de staging
  registra tres pagos Paddle aprobados y dos suscripciones; la operación Pro
  anual proyectó efectivamente Pro con origen `billing`. Esto **no** prueba los
  otros precios, renovaciones ni el ciclo completo.
- [x] Confirmar que la entrega iOS staging
  [0b6893e2](https://expo.dev/accounts/my-scoope/projects/my-scoope/submissions/0b6893e2-bfc5-4cf2-8310-7d23bd7e344d)
  aparece como `Succeeded` en Expo. Falta verificar procesamiento/TestFlight.
- [x] Confirmar que Google Play tiene la prueba interna 7 activa; la app sigue
  en borrador para producción y el panel muestra 0 de 11 tareas de información
  de la app/ficha completadas. El perfil de pagos muestra un método de
  transferencia configurado; su verificación efectiva sigue por confirmar.
- [x] Repetir 35 pruebas focalizadas de Paddle, créditos, conciliación de
  suscripciones Google y App Store sobre base de test local: todas pasan. Esto
  valida código, no compras externas.
- [x] Verificar directamente la página pública de privacidad: ya describe
  Paddle, Apple y Google y muestra el contacto corporativo. Una copia indexada
  anterior estaba obsoleta; no utilizarla como evidencia de despliegue. Sigue
  pendiente la aprobación legal del contenido antes de abrir ventas reales.
- [x] Comprobar en Render que `my-scoope` producción sigue desplegado desde
  `main` en el commit `165a8435` (anterior al contrato comercial y a las bolsas);
  staging contiene los cambios recientes. No se debe activar Paddle live sobre
  ese binario: primero integrar el commit verificado vía PR a `main` y validar
  el nuevo despliegue productivo con checkout aún apagado.
- [x] Preparar `release/payments-production` desde `origin/main` en un worktree
  separado: contiene el contrato comercial, cobros, créditos, conciliaciones y
  requisitos mínimos de autenticación móvil, sin incorporar los 276 archivos
  del avance general de `staging`. Se preservó la vista de propuestas de `main`
  para no introducir un cambio de interfaz ajeno a pagos.
- [x] Ejecutar el gate local del release: 100 verificaciones rápidas Django,
  2.070 pruebas completas Django, 123 pruebas móviles, lint, tipos, auditoría
  de dependencias y exportación web, todos aprobados. La primera ejecución de
  Django detectó una expectativa de prueba de la interfaz de `staging` que no
  correspondía al release aislado; tras ajustarla, la suite completa pasó.
  Falta el gate remoto `full`, incluida la suite PostgreSQL, sobre el commit
  exacto de la PR antes de integrar en `main`.
- [ ] Subir una build Android de staging con las correcciones posteriores a la
  versión interna 7. La red del entorno aislado impidió obtener EAS CLI y el
  acceso ampliado quedó pendiente de autorización específica para subir código
  privado a Expo en una build Android.
- [ ] Revisar sesiones, contratos y disponibilidad de Paddle live y App Store
  Connect con el titular. Ningún checkout real ni flag productivo se activó.

## Lo que Felipe debe tener o resolver

| Necesidad | Para qué | Quién la verifica |
|---|---|---|
| Titular con acceso administrativo y segundo factor a Paddle live, App Store Connect y Play Console; autorización para configurar productos, notificaciones y releases. | Evitar operar con sesiones prestadas o permisos insuficientes. | Felipe inicia sesión; el equipo comprueba permisos sin recibir contraseñas. |
| Identidad comercial, datos bancarios y fiscales completos y aprobados en los tres proveedores. En Paddle, cuenta live verificada y datos de payout; en Apple, acuerdo Paid Apps activo y formularios bancarios/fiscales; en Google, perfil de comerciante y método de cobro verificado. | Poder vender y recibir liquidaciones, no solo simular compras. | Felipe/titular completa formularios privados en cada consola; equipo constata estados, nunca copia datos bancarios al repositorio o chat. |
| Dominio productivo y acceso a Render/secretos de producción; API keys, tokens y secretos de webhook **live**, separados de sandbox. | Conectar cada tienda a producción sin cruzar ambientes. | Equipo configura secretos en proveedor/Render y prueba diagnóstico seguro. |
| Cuentas de prueba separadas y control de una compra real pequeña por canal, con medio de pago propio; presupuesto aceptado para esos cargos. | Verificar recaudación y beneficio reales. Las compras de TestFlight/Play testing no prueban un cargo real. | Felipe realiza o autoriza explícitamente cada compra real; no comparte datos de tarjeta. |
| iPhone físico para TestFlight y luego App Store; acceso a Android físico compatible o a un verificador externo para la versión pública de Google Play. | Verificar que la app distribuida realmente cobra y acredita en cada tienda. | Felipe coordina el dispositivo/verificador; el equipo guía la prueba. El emulador sirve para staging, pero no sustituye esta comprobación de lanzamiento. |
| Criterio contable/tributario para ingresos y reembolsos de Paddle, Apple y Google en Chile, incluyendo cómo conciliar liquidaciones. | Evitar activar OpenFactura o emitir documentos incorrectos por inferencia. | Contador/asesor de Felipe aprueba; OpenFactura sigue fuera de este ciclo salvo decisión expresa. |
| Responsable de soporte y alertas, ventana de lanzamiento y autorización de rollback. | Resolver pagos atascados, dobles cobros o reembolsos sin pérdida de historial. | Felipe designa responsable y canal operativo antes de activar checkout. |

No solicitar ni almacenar contraseñas, claves privadas, números de tarjeta o datos
bancarios en documentos de trabajo. Las pruebas reales con cargo y cualquier
reembolso productivo se coordinan con Felipe antes de ejecutarse.

## Patches y dependencias

| Patch | Entrega | Gate para avanzar |
|---|---|---|
| PPC00 — Línea base y acceso | Inventariar productos/precios existentes (sin duplicarlos), mapeos, entornos, despliegues, flags, permisos, contratos, cuenta de cobro, saldos y cuentas de prueba. Registrar evidencia y plan de rollback por canal. | Inventario firmado; ningún identificador live confundido con sandbox; cuentas actuales preservadas. |
| PPC01 — Paddle staging | Probar Basic/Pro mensual/anual y las tres bolsas: importe, grant único, renovación, rechazo, cancelación, reembolso, webhook repetido y reconciliación. Corregir brechas. | Matriz Paddle sandbox completa; ninguna doble acreditación/cargo en proyección. |
| PPC02 — Google Play staging | Publicar build interna actualizada conectada a staging; probar los cuatro planes, tres bolsas, recompra de consumible, restauración donde aplique, renovación, cancelación, mora y reembolsos con y sin revocación. Verificar jobs de conciliación e idempotencia. | Suscripción y créditos cambian solo por compras verificadas; refund resta una vez; jobs pasan en staging y tienen alertas. |
| PPC03 — App Store staging | Completar TestFlight para staging; probar los cuatro planes, tres bolsas, restauración, renovación, expiración, gracia y reembolso. Verificar firma de notificaciones, enlace de cuenta, reconciliación y reintentos. | Evidencia en iPhone físico y backend; productos y app aptos para revisión/publicación. |
| PPC04 — Preparación live | Reutilizar productos live existentes compatibles y crear solo los que falten; mapear IDs y precios live sin borrar historial. Preparar URLs, secretos, notificaciones, catálogo Chile, builds productivas, revisión de tiendas y alertas. Ensayar rollback y ejecutar gate CI completo sobre el commit exacto. | Aprobaciones/contratos activos, catálogo sin duplicados ofrecidos, builds aprobadas, configuración revisada por dos personas y pruebas de staging verdes. |
| PPC05 — Activación gradual | Habilitar un canal por vez: primero recepción/verificación de eventos, luego checkout; mantener los otros canales intactos. Publicar clientes aprobados. Ejecutar una compra real controlada de plan y bolsa por canal, comparar orden, dinero, cuenta, plan, créditos y ledger. | Cobro real correcto, sin doble beneficio, soporte y rollback listos antes de abrir el siguiente canal. |
| PPC06 — Operación y cierre | Observar renovaciones, expiraciones, cancelaciones, rechazos y reembolsos reales o simulaciones permitidas; comprobar conciliación programada y alertas. Conciliar el primer payout/settlement de cada proveedor con sus ventas, comisiones y reembolsos. Actualizar documentación vigente. | Evidencia completa por canal; cero pagos no explicados; cerrar como `completed` solo entonces. |

Si un proveedor demora aprobación o liquidación, se puede terminar el trabajo de
los otros sin declarar el ciclo total completo. Ningún patch implica eliminar
productos, precios o historial de compras anteriores. Paddle sandbox y live son
catálogos separados: crear el equivalente live no es duplicar una oferta en una
misma tienda; si ya existe un producto live compatible, se reutiliza.

## Evidencia mínima por canal

Registrar en un anexo operativo o ticket por prueba: fecha, ambiente, versión de
app/backend, ID de producto y precio, orden/transaction ID parcial, usuario de
prueba no sensible, importe/moneda, estado en proveedor, `BillingPayment`,
`ProviderSubscription` o asiento de wallet, resultado esperado/real y enlace a
logs seguros. No adjuntar tokens de compra, JWS completos ni datos de tarjeta.

Cada canal debe demostrar:

1. Cuatro ofertas de suscripción y tres bolsas disponibles **solo** para el
   público/plan permitido, con moneda e importes correctos; sin planes duplicados.
2. Compra aprobada, rechazada e interrumpida; beneficio solo tras verificación
   server-to-server; doble entrega o repetición del evento sin doble efecto.
3. Renovación, cancelación, expiración y problema de cobro con acceso coherente;
   downgrade no destructivo y créditos comprados preservados según decisión 0201.
4. Tres bolsas acreditadas una vez, recomprables y conciliables; reembolso o
   contracargo revierte solo lo debido y deja deuda/revisión auditable si ya se
   gastaron créditos.
5. Restauración o recuperación de compras aplicable a la tienda, incluso tras
   reinstalar o iniciar sesión de nuevo, sin adjudicar compras a otra cuenta.
6. Conciliación programada, alertas, procedimiento de soporte, rollback por
   flags y ausencia de secretos en código/logs.
7. Al menos una transacción real productiva de suscripción y una de bolsa, con
   importe y beneficio concordantes; primera liquidación bancaria/financiera
   conciliada cuando llegue el ciclo de pago del proveedor.

No forzar un reembolso real solo para marcar una casilla si el proveedor o el
riesgo lo impiden; documentar la simulación sandbox equivalente y una revisión
operativa explícita del flujo productivo. Toda compra real de verificación debe
seguir el procedimiento y consentimiento del titular.

## Estado de implementación productiva

| Canal | Código | Staging integral | Cobro productivo | Conciliación y payout | Estado final |
|---|---|---|---|---|---|
| Paddle | Parcialmente implementado | Pendiente | Pendiente | Pendiente | **No realizada** |
| Google Play | Parcialmente implementado | Pendiente | Pendiente | Pendiente | **No realizada** |
| App Store | Parcialmente implementado | Pendiente | Pendiente | Pendiente | **No realizada** |

Actualizar esta tabla solo con evidencia identificable. Cambiar `Status` a
`active` al iniciar PPC00 y a `completed` únicamente cuando PPC00–PPC06 y las
tres filas hayan pasado sus gates. Si un canal falla, desactivar su checkout,
conservar webhooks/conciliación necesarios para contratos existentes, no borrar
evidencia y registrar incidente y plan de recuperación.

## Referencias operativas

- [Runbook de proveedores](../40_technical/operations/billing_providers_runbook.md).
- [Estado técnico vigente de billing](../00_current/features/billing.md).
- [Paddle: go-live](https://developer.paddle.com/build/go-live-checklist/),
  [verificación de cuenta](https://www.paddle.com/help/start/account-verification/what-is-account-verification).
- [Apple: configuración de compras](https://developer.apple.com/help/app-store-connect/configure-in-app-purchase-settings/overview-for-configuring-in-app-purchases/),
  [pruebas en TestFlight](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testing-subscriptions-and-in-app-purchases-in-testflight/).
- [Google: perfil de pagos](https://support.google.com/googleplay/android-developer/answer/3092739?hl=en),
  [verificación de cobro](https://support.google.com/googleplay/android-developer/answer/13628312?hl=en),
  [compras de prueba](https://support.google.com/googleplay/android-developer/answer/6062777?hl=en).
