# Billing, Payments & Tax Documents Cycle

Status: completed (repository cycle; provider rollout remains gated)
Date: 2026-07-19
Cycle code: BILL

## Contexto

El ciclo ACC dejó a `accounts` como dueño de planes comerciales, suscripciones,
créditos y entitlements. El siguiente paso no es mover esas responsabilidades, sino
explicar y auditar qué operación externa originó el estado comercial.

La primera estrategia de recaudación de My Scoope será Mercado Pago en Chile. La
emisión de boletas se realizará mediante OpenFactura. Son dos integraciones distintas:
un pago aprobado no equivale a una boleta aceptada por el SII y una caída tributaria
no debe borrar ni repetir un pago.

## Objetivo

Crear una app Django `billing` que coordine pagos y documentos tributarios sin
convertirse en dueña de los permisos de producto.

```text
Mercado Pago -> billing -> accounts
                        -> OpenFactura

Mercado Pago = recaudación y ciclo externo de suscripción/pago
billing      = verificación, idempotencia, conciliación y trazabilidad
accounts     = plan efectivo, créditos y entitlements
OpenFactura  = emisión y estado del documento tributario
```

## Ajustes respecto del plan ACC

El plan anterior postergaba Stripe/Mercado Pago como un único bloque de "pagos". Este
ciclo lo reemplaza por dos fronteras explícitas:

1. Mercado Pago es el primer adaptador de recaudación, sin convertir sus estados en
   enums universales del dominio de cuenta.
2. OpenFactura es un adaptador tributario posterior al pago, con outbox, clave de
   idempotencia y reintentos propios.

Stripe queda fuera de la primera integración. Apple App Store y Google Play siguen
siendo proveedores futuros: deben producir las mismas proyecciones internas sin
reemplazar `accounts`.

## Reglas obligatorias

- Nunca activar entitlements desde parámetros de retorno del navegador.
- Verificar firma de webhook y volver a consultar el recurso en Mercado Pago antes de
  cambiar estado comercial.
- Deduplicar notificaciones por proveedor e identificador estable.
- Una notificación es señal de cambio, no comprobante final de pago.
- Proyectar a `AccountSubscription` únicamente desde estado verificado.
- Crear como máximo una solicitud tributaria por pago aprobado.
- Enviar a OpenFactura una `Idempotency-Key` persistida, nunca regenerada en un retry.
- No guardar credenciales, tarjetas, prompts ni payloads innecesariamente sensibles.
- Los errores de OpenFactura se reintentan/operan sin revertir el pago aprobado.
- Reembolsos y contracargos no borran registros: crean transiciones auditables y, si
  corresponde, una nota de crédito en un patch futuro.

## Modelo inicial

```text
BillingProduct
  -> mapea producto/plan externo a accounts.AccountPlan

ProviderSubscription
  -> estado observado en Mercado Pago

BillingPayment
  -> cobro individual verificable

BillingEvent
  -> inbox idempotente de eventos autenticados

TaxDocument
  -> outbox/estado de boleta OpenFactura por pago
```

`ProviderSubscription` no reemplaza `AccountSubscription`. La primera conserva el
hecho externo; la segunda expresa el acceso vigente en My Scoope.

## Secuencia de patches

| Patch | Estado | Resultado |
|---:|---|---|
| BILL00 | implemented | Plan y decisión de frontera Mercado Pago/OpenFactura. |
| BILL01 | implemented | App, modelos iniciales, migración y Django Admin. |
| BILL02 | implemented | Inbox de eventos verificados, proyección a `accounts` y outbox tributario idempotente. |
| BILL03 | implemented | Contratos provider-neutral, gateways fake y promoción explícita de Billing a Tier 1. |
| BILL04 | implemented | Webhook Mercado Pago desactivado por defecto, HMAC/timestamp, consulta server-to-server y reconciliación de recursos registrados. |
| BILL05 | implemented | Checkout/cancelación Mercado Pago opt-in y pantalla Billing para plan, suscripciones, pagos y DTE. |
| BILL06 | implemented | Gateway y worker OpenFactura, estado remoto, idempotencia persistente y retry automático limitado a 23 horas. |
| BILL07 | implemented with tax gate | Refund/chargeback revoca acceso y abre revisión tributaria auditable; nota de crédito automática se difiere hasta aprobación contable. |
| BILL08 | implemented; external smoke pending | Conciliación CLI, Django Admin y cola Billing en Admin Operations. El smoke requiere credenciales sandbox. |
| BILL09 | implemented | Runbook, defaults seguros y frontera documentada para futuros adapters App Store/Google Play. |

## Decisión de cierre

El ciclo de repositorio queda completo. Los flags continúan apagados y no se declara
readiness productivo: habilitar cobros o DTE exige ejecutar los gates externos del
runbook. La nota de crédito no se automatiza con un DTE supuesto; un refund o
chargeback conserva la boleta original, marca `adjustment_required` y deja la resolución
tributaria a una operación revisada hasta aprobar el contrato con contador/OpenFactura.

## Fuera de alcance inicial

- cargos reales antes de completar credenciales, sandbox y smoke;
- almacenar datos de tarjeta;
- paquetes de créditos comprables;
- Apple/Google IAP;
- facturas B2B y boletas de honorarios;
- cálculo contable o asesoría tributaria dentro del código;
- emitir una boleta directamente dentro del request del webhook.

Los paquetes de créditos quedan postergados porque la wallet actual se renueva por
periodo. Antes de vender créditos se deben separar saldos incluidos, promocionales y
comprados para evitar que una compra expire incorrectamente.

## Gates antes de producción

- credenciales de prueba y producción separadas;
- URLs HTTPS y secretos fuera del repositorio;
- validación de firmas con casos negativos;
- reconciliación de pago consultando la API de Mercado Pago;
- sandbox de OpenFactura con claves de idempotencia persistidas;
- definición tributaria revisada por contador para tipo de DTE, IVA, glosa y notas de crédito;
- pruebas de duplicados, retries, pagos rechazados, pausas, cancelaciones, refunds y contracargos;
- rollback que deshabilite checkout/emisión sin ocultar el historial.
