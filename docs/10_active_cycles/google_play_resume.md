# Retomar la preparación de Google Play

Status: active

Estado documentado: 2026-10-26. Este documento reúne la evidencia registrada en
el [ciclo de activación de pagos](production_payment_channels_cycle.md) y el
[runbook de proveedores](../40_technical/operations/billing_providers_runbook.md).
Es una guía de reanudación, no una constatación en vivo de Play Console, Render
o Expo. Antes de cambiar configuración o publicar, volver a comprobar esos
sistemas y anotar fecha, versión y resultado.

## Estado confirmado en la última revisión

- El código de Google Play, incluidos los reemplazos de suscripciones y las
  notificaciones de compras anuladas, se integró en `staging` mediante la
  [PR #114](https://github.com/DidesCabrera/my-scoope/pull/114). Su despliegue
  en Render terminó correctamente y `billing.0011` se aplicó.
- Play Console mostraba cuatro precios de suscripción y tres bolsas activos
  para Chile. La app seguía en borrador y la prueba interna distribuía la
  versión 7; no había evidencia de una build Android posterior instalada.
- Pub/Sub entregó una notificación de prueba autenticada al webhook de
  staging, que respondió HTTP 200 el 2026-10-16. Esto acredita el canal de
  entrega, no una compra ni la proyección correcta de beneficios.
- En staging se había verificado una compra de 500 créditos y su reembolso
  idempotente. No constaba la matriz de suscripciones y bolsas completas.
- Expo estaba en el plan Free con 0 de 30 builds Android usadas y US$0
  previstos. La subida del código privado para una nueva build quedó
  detenida por la revisión automática; confirmar su autorización y las
  condiciones actuales antes de intentarla.

## Pendientes en orden de ejecución

1. **Revalidar la línea base.** Consultar `origin/staging`, el despliegue de
   Render, los flags y el ambiente `sandbox`, la prueba interna de Play Console
   y el estado de Expo. Registrar las diferencias respecto de esta guía. No
   confundir una respuesta 200 del webhook con una compra probada.
2. **Preparar una build Android interna actualizada.** Resolver la autorización
   para subir el código a Expo EAS; verificar perfil, versión, costo y destino
   de la build antes de enviarla. Instalarla desde la prueba interna y
   comprobar que apunta a staging.
3. **Probar compras en staging desde Google Play.** Cubrir los cuatro planes
   y tres bolsas, recompra de consumibles, renovación, reemplazo, cancelación,
   mora, reembolso y notificaciones repetidas. Registrar por caso el producto,
   versión, ambiente, resultado en Play y efecto en `BillingPayment`,
   suscripción y wallet sin copiar tokens ni datos sensibles.
4. **Habilitar conciliaciones con evidencia.** Ejecutar primero los comandos
   de suscripciones y reembolsos en modo de prueba; habilitar sus flags
   programados solo después de observar compras, cambios de estado y
   reembolsos de prueba sin doble beneficio ni doble reversión. Seguir el
   [gate de Google Play](../40_technical/operations/billing_providers_runbook.md#google-play-staging-and-lifecycle-gate).
5. **Completar Play Console.** Verificar y terminar icono, gráfico destacado,
   capturas de la build aprobada, Seguridad de datos, IARC y detalles de
   acceso para revisión con una cuenta de prueba reutilizable y contenido
   premium. Resolver la política y el flujo para usuarios de 13 a 17 años
   antes de solicitar publicación; no inferir declaraciones a partir del
   código o de esta guía.
6. **Preparar lanzamiento.** Revisar configuración live y aprobación de la
   tienda, soporte, alertas y rollback. Una compra productiva controlada de
   suscripción y otra de bolsa, seguidas de conciliación de la primera
   liquidación, son evidencia de cierre; las compras de prueba no la
   sustituyen.

## Cómo continuar

Empezar por el paso 1 y actualizar esta página con fecha y evidencia de cada
resultado. Usar el [ciclo de activación](production_payment_channels_cycle.md)
para los gates PPC02–PPC06 y el [runbook](../40_technical/operations/billing_providers_runbook.md)
para la secuencia operativa y los flags. La investigación de precios de
StoreKit/TestFlight pertenece al canal App Store y no bloquea esta revisión de
Google Play.
