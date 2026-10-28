# Pagos, beneficios y salud de la beta

Status: human_reference
Date: 2026-10-28
Audience: usuarios staff humanos de soporte, operaciones, producto y desarrollo
Role: human_reference
Authority: non_authoritative
Update-Policy: explicit_user_request_only

> Orientación para clasificar consultas e incidentes. No define precios, beneficios, contratos con
> tiendas ni procedimientos contables.

## Separar compra de beneficio

Apple, Google Play y otros proveedores entregan evidencia externa de compra, renovación, reembolso o
cancelación. My Scoope verifica y reconcilia esa evidencia antes de proyectarla sobre la cuenta. Una
transacción recibida no concede acceso por sí sola y el cliente móvil no es autoridad comercial.

```text
tienda o proveedor
  -> evidencia autenticada
  -> verificación y reconciliación
  -> estado comercial de la cuenta
  -> beneficios y créditos visibles
```

Precios y moneda deben venir de la tienda correspondiente al storefront o de la oferta verificada;
no deben escribirse como texto fijo en la interfaz. Restaurar compras recupera evidencia compatible,
pero no convierte automáticamente productos de otro usuario, ambiente o tienda.

## Preguntas de soporte

| Síntoma | Revisar |
| --- | --- |
| Precio en moneda inesperada | Storefront, cuenta de tienda, entorno y producto configurado. |
| Compra completada sin beneficio visible | Verificación del servidor, reconciliación y cuenta asociada. |
| Restauración no encuentra la compra | Apple/Google, ambiente sandbox/producción y usuario original. |
| Beneficio antiguo sigue visible | Estado de renovación, reembolso, revocación y última reconciliación. |
| Créditos distintos del consumo esperado | Ledger de créditos y eventos aplicados, no tokens del proveedor IA. |

## Salud de la beta

La ausencia de eventos en una plataforma no demuestra ausencia de fallos. TestFlight, Sentry, Expo y
Render observan capas distintas y deben correlacionarse con build, release, ambiente y momento.

Clasificar primero:

1. **Crash del cliente:** cierre nativo o JavaScript asociado a una build.
2. **Error de backend:** excepción o respuesta 5xx del servicio.
3. **Condición comercial esperada:** límite o conflicto que necesita mensaje claro, no una alarma.
4. **Rendimiento:** consultas repetidas, memoria o tiempos altos sin caída total.
5. **Configuración/despliegue:** migraciones, variables, credenciales o versión desalineada.
6. **UX o comprensión:** el sistema responde, pero la persona no entiende el siguiente paso.

Una build instalada antes de mejorar la instrumentación no obtiene observabilidad retroactiva. Para
validar un arreglo se necesita una build nueva, una reproducción controlada y confirmación de que el
evento llega con release y ambiente correctos.

## Regla de comunicación

Informar hechos confirmados, hipótesis y siguiente verificación por separado. No tratar límites
comerciales como crashes ni asumir que un silencio de Sentry equivale a una beta saludable.

## Referencias

- [Recorrido móvil](mobile_journey.md)
- [Evolución del producto](project_evolution.md)
