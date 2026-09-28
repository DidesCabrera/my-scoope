# Commercial Launch Contract Cycle

Status: active
Decision: `docs/20_decisions/0201-commercial-launch-plans-and-owned-library.md`
Date: 2026-09-25

## Avance de implementación (2026-09-27)

La ejecución comenzó en la rama `docs/commercial-launch-contract`, sin despliegue ni
alteración de datos productivos. La decisión 0201 es la autoridad comercial; este
registro distingue implementación local de validación externa de recaudación.

| Patch | Estado local | Evidencia o pendiente |
|---:|---|---|
| CLC00 | Implementado | Decisión 0201 y ciclo registrados. |
| CLC01 | Implementado localmente | Seeds de Free/Basic/Pro y ofertas mensuales/anuales actualizados; migración conserva snapshots históricos y desactiva mapeos con precio anterior. |
| CLC02 | Implementado localmente | Evaluador común de límites para comandos, compartición, web y API móvil; API expone límites y uso. |
| CLC03 | Implementado localmente | Los límites gobiernan acciones nuevas; pruebas de downgrade conservan comidas, programas largos y créditos comprados. |
| CLC04 | Implementado localmente | Recepción/consulta independiente de incorporación; Free 1 incorporación por mes, idempotencia y renovación mensual probadas. |
| CLC05 | Implementado localmente | Wallet mensual/comprado, gasto mensual primero, expiración, reserva/liberación, bloqueo Free y reembolso auditado. |
| CLC06 | Tarifa inicial implementada; calibración pendiente | Felipe aprobó una tabla inicial ajustable. Hay 17 muestras locales de `assistant.ai_nutrition_intake.preview` (USD 0,001708–0,008841; media USD 0,005161); no hay muestras locales de programas. Se fija una tarifa v1 provisional y se conserva costo/modelo como telemetría interna. |
| CLC07 | Catálogos sandbox parcialmente configurados; compras pendientes | Los cuatro precios y las tres bolsas de Paddle Sandbox están creados sin duplicar planes. Los cuatro productos de suscripción preexistentes de Apple y Google recibieron los nuevos precios CLP; en Apple se crearon tres consumibles con precio, disponibilidad y localización, pendientes de revisión con una versión de la app. En Google se crearon tres productos únicos como borradores con opción de compra `standard`, precio CLP y disponibilidad solo Chile; no se activan antes de validar reembolsos. El mapeo de staging usa IDs verificados y conserva Mercado Pago como legacy. Faltan compras, conciliación y pruebas de reembolso reales en sandbox. |
| CLC08 | Implementado localmente | Landing, Billing y móvil usan beneficios/catálogo de servidor; falta revisión visual y de textos con producto. |
| CLC09 | Gate local completado, despliegue pendiente | Fast checks, calidad, frontend, móvil, MCP y suite backend completa pasaron; la suite completa dio 78% de cobertura. Tras el ajuste del mapeo móvil y la migración 0007 se debe repetir el gate afectado antes de integrar. No hay todavía commit, merge, push ni pruebas desplegadas en staging. |

### Definiciones aprobadas y tarifa v1 (2026-09-27)

Felipe autorizó una tabla inicial ajustable. La tarifa fija de cada acción
explícita se resuelve en `AI_ASSISTANT_TASK_CREDIT_TARIFFS`; el costo del proveedor
se sigue midiendo por separado. La acción cobrada queda fijada en la solicitud,
antes de ejecutar IA: una respuesta clasificada después como otra acción no puede
elevar silenciosamente el precio. Acciones no clasificadas mantienen el cálculo
dinámico anterior hasta completar su inventario.

| Tarea de IA explícita | Créditos v1 | Base |
|---|---:|---|
| Conversación y llamada de herramienta | 10 | Provisional; también es la reserva segura del chat genérico. |
| Propuesta de comida | 15 | Provisional; sin muestra local específica. |
| Propuesta de plan diario | 20 | Provisional; sin muestra local específica. |
| Modificación/propuesta de programa | 50 | Objetivo comercial provisional, no validación de costo. |
| Vista previa de intake nutricional | 10 | 17 muestras locales; costo medio USD 0,005161. |
| Lectura de etiqueta nutricional | 2 | Tarifa fija ya existente, fuera del medidor de turnos. |

El flujo de programa puede requerir varios turnos; por tanto 50 créditos por
acción explícita no demuestra que un programa completo cueste 50. Hay que medir
el recorrido completo y ajustar antes de publicarlo como equivalencia Basic/Pro.
La regla de cuentas existentes depende del entorno: local y staging dejan todas
Pro; producción deja a `bacardides` Pro anual y al resto Free. Ningún rol
profesional otorga Pro automáticamente. Esta regla no cancela por sí misma
contratos de cobro con proveedores.

### Puertas pendientes para cierre comercial

1. Medir los costos faltantes de programas y revisar la tarifa v1 antes de
   prometer las equivalencias buscadas (Basic ≈ 3, Pro ≈ 20 programas).
2. Completar el catálogo de distribuidores: en Paddle Sandbox están los cuatro
   precios y las tres bolsas. Apple conserva los cuatro productos existentes y
   suma tres consumibles; requieren revisión junto con la primera versión de la
   app. Google conserva los dos productos Basic/Pro y sus cuatro planes básicos;
   las tres bolsas son borradores disponibles solo en Chile y no se activarán antes
   de probar el circuito de reembolsos. El script de predespliegue de staging
   registra los mapeos aprobados; las bolsas Google aún no se mapean para venta.
3. Verificar cobro, webhook repetido, rechazo, cancelación, reembolso y conciliación
   de importe/beneficio en cuentas de prueba de cada distribuidor. Ningún test local
   sustituye la prueba de recaudación externa. Felipe autorizó el descuento real
   y la programación periódica de reembolsos después de la prueba sandbox; el
   cron está preparado pero desactivado hasta completar esa puerta. En Google
   existe consulta verificada de anulaciones; falta la prueba real. No activar
   las bolsas allí antes de esas verificaciones.
4. Aplicar la regla por entorno: en local y staging, todas las cuentas Pro; en
   producción, solo `bacardides` Pro anual y el resto Free.
   `reconcile_launch_account_plans --scope=...` simula por defecto y requiere
   `--apply` para modificar; en producción bloquea ante acuerdos de cobro activos de otras
   cuentas. Las tres cuentas locales quedaron Pro y se aplicaron migraciones y
   catálogo comercial en la base de desarrollo; staging/producción aún no
   cambiaron. La sincronización genérica ya no promueve por rol.
5. Revisar copy y experiencia de compra web/móvil, activar flags de proveedor solo
   tras pruebas de sandbox y actualizar `docs/00_current/` cuando esté desplegado.

## Objetivo

Implementar y validar el contrato comercial de lanzamiento de Free, Basic y Pro sin
crear nuevas funciones premium. El ciclo termina cuando beneficios, límites, créditos,
precios, recaudación y comunicación utilizan la misma autoridad y existe evidencia de
que una pérdida de plan nunca destruye el capital digital del usuario.

## Fuera de alcance

- desarrollar nuevas capacidades exclusivas para Basic o Pro;
- construir el futuro onboarding Free determinístico hacia un Plan diario;
- generar Programs completos como beneficio inicial Free;
- presentar la tarifa inicial como validación económica final sin medir tareas faltantes;
- eliminar elementos existentes para hacer cumplir un downgrade;
- rediseñar la arquitectura de billing ya adoptada.

La experiencia determinística de primer Plan diario se abordará en otro ciclo de
producto. Este ciclo solo debe preservar el espacio contractual para incorporarla sin
convertir Free en una fuente de costo variable.

## Contrato de referencia

La matriz, los precios y las reglas detalladas viven únicamente en la decisión 0201.
Este documento organiza la implementación; no debe mantener una segunda copia de sus
valores que pueda divergir.

Principios que atraviesan todos los patches:

```text
El plan controla capacidades nuevas, no la propiedad de lo ya construido.
Compartir y consultar no exige pagar; incorporar y editar una copia sí consume cupo.
Free no origina costo variable de IA.
accounts decide el beneficio; billing aporta evidencia de pago.
```

## Patches

| Patch | Objetivo | Resultado esperado |
|---:|---|---|
| CLC00 | Contrato documental | Registrar 0201, precedencia, brechas y plan de ejecución. |
| CLC01 | Autoridad de catálogo y planes | Alinear seeds, defaults y configuración canónica de Free/Basic/Pro; retirar valores comerciales incompatibles. |
| CLC02 | Evaluación central de capacidades | Implementar límites de creación/incorporación desde `accounts`, con respuestas consistentes para web, móvil y servicios. |
| CLC03 | Downgrade no destructivo | Conservar lectura, edición, uso y compartición de elementos propios; bloquear solo nuevas acciones que excedan Free. |
| CLC04 | Compartidos conmigo | Mantener recepción/consulta en todos los planes e implementar incorporación Free de 1 por mes y pagada ilimitada, de forma idempotente. |
| CLC05 | Wallet y consumo | Separar asignación mensual de saldo comprado, expiración/orden de consumo, liberación ante fallos y suspensión segura en Free. |
| CLC06 | Calibración por tarea | Medir costo real, definir tabla de créditos, mostrar el costo antes de confirmar y validar las equivalencias comerciales. |
| CLC07 | Ofertas y recaudación | Configurar mensual/anual y bolsas para Basic/Pro; validar checkout, webhooks, renovación, cancelación, rechazo, reembolso y conciliación. |
| CLC08 | Comunicación de valor | Alinear landing, cuenta, upgrade, web y móvil con el mismo contrato y mensajes claros de límites/no destrucción. |
| CLC09 | Cierre | Ejecutar matriz de pruebas, registrar evidencia, actualizar contratos vigentes y cerrar brechas/documentos históricos. |

## Brecha inicial conocida

Antes de CLC01 se debe obtener un inventario reproducible de todo punto que codifique
planes o precios. Como mínimo se revisarán:

- seeds y migraciones de `accounts`;
- catálogo y snapshots de billing;
- entitlements consumidos por web, API móvil y AI Assistant;
- landing, perfil, checkout y superficies de upgrade;
- configuración de Mercado Pago y Apple cuando corresponda;
- fixtures, factories, pruebas, comandos de bootstrap y documentación vigente.

Los valores incompatibles no se migran ciegamente: se clasifican como datos de prueba,
historia, configuración de staging o contrato productivo antes de modificarlos.

El inventario documental inicial ya confirma estas divergencias activas:

| Superficie | Estado previo encontrado | Contrato 0201 |
|---|---|---|
| `accounts/seed_plans.py` | Free incluye 25 créditos mensuales | Free incluye 0 |
| `billing/catalog.py` | Basic $7.990 mensual / $79.900 anual | $3.990 / $34.990 |
| `billing/catalog.py` | Pro $12.990 mensual / $129.900 anual | $6.990 / $59.990 |
| Catálogo de billing | No contiene las tres bolsas decididas | 500/$2.990, 1.000/$5.990 y 2.000/$9.990 para Basic/Pro |

Estos hallazgos justifican CLC01 y CLC07; se documentan aquí sin modificar todavía el
comportamiento del producto.

## Reglas de implementación

### Creación y downgrade

- Los contadores se calculan sobre elementos propios aplicables a cada categoría.
- Alcanzar el umbral permite conservar todo lo existente y bloquea la siguiente
  creación o incorporación.
- Un usuario que baja de plan con más elementos que Free no pierde funciones sobre
  esos elementos existentes.
- Un Programa de hasta 12 semanas creado bajo un plan pagado no se trunca al volver a
  Free; sus semanas existentes permanecen editables y el límite se aplica a nueva
  extensión.
- Toda transición de plan registra plan anterior, plan nuevo, fecha, causa y evidencia
  de proveedor cuando exista.
- Ningún job de downgrade puede incluir borrado, archivado forzoso o cambio masivo de
  visibilidad de elementos propios.

### Compartidos conmigo

- La autorización para ver el recurso compartido es independiente del entitlement de
  incorporación.
- Agregar crea una copia propia idempotente y registra el consumo mensual.
- Reintentos de la misma operación no consumen cupo adicional ni crean duplicados.
- El periodo mensual debe tener una definición única y pruebas de borde temporal.

### Créditos

- La asignación mensual y los créditos comprados se representan como fuentes
  distinguibles y conciliables.
- Al consumir se usan primero los créditos mensuales y luego los comprados.
- Reserva, consumo, liberación, reembolso, expiración y ajuste dejan ledger.
- Una ejecución que falla antes de entregar el resultado libera la reserva.
- Free no puede iniciar tareas con costo, comprar bolsas ni consumir el saldo comprado;
  ese saldo reaparece al reactivar Basic o Pro.
- CLC06 debe basar las tarifas en mediciones por tarea y modelo, incluyendo
  escalamiento interno y margen, sin exponer tokens al usuario.

### Recaudación

- Solo Basic y Pro exponen checkout mensual/anual y bolsas.
- El producto, precio, moneda, periodo y plan interno se resuelven por una tabla
  versionada y verificable.
- Los webhooks son idempotentes y la proyección de entitlement es determinística.
- Un pago confirmado no concede un beneficio distinto al contrato de `accounts`.
- La conciliación permite explicar cada cobro, suscripción, bolsa y movimiento de
  créditos sin editar ledgers históricos.

## Validación mínima

La matriz automatizada y los smokes de sandbox deben incluir:

1. alta nueva en Free y ausencia de créditos/capacidades pagadas;
2. límites de Comidas, Planes diarios, Programas y Comparaciones;
3. cambio Free → Basic/Pro y aplicación inmediata de beneficios;
4. downgrade por cancelación, mora o expiración con biblioteca intacta;
5. usuario sobre los umbrales Free que conserva y usa sus elementos, pero no crea más;
6. recepción y consulta de múltiples compartidos en Free;
7. primera incorporación mensual Free exitosa, segunda bloqueada y renovación del cupo;
8. incorporación ilimitada Basic/Pro y protección posterior de las copias;
9. grant mensual, compra de bolsa, orden de consumo, expiración y liberación por fallo;
10. saldo comprado preservado pero suspendido en Free y recuperado al reactivar;
11. checkout mensual/anual de Basic y Pro con importes exactos;
12. compra de las tres bolsas en ambos planes pagados y rechazo en Free;
13. renovación, cancelación, rechazo, reembolso, webhook duplicado y conciliación;
14. paridad de mensajes y capacidades entre web y móvil.

## Definición de terminado

El ciclo puede cerrarse cuando:

- existe una única autoridad ejecutable para la matriz decidida;
- no quedan precios o beneficios anteriores en superficies de producto activas;
- todos los límites se aplican a acciones nuevas y ninguna transición destruye datos;
- Compartidos conmigo cumple la separación entre consultar e incorporar;
- la tabla de créditos por tarea está respaldada por medición y aprobada antes de
  publicarse;
- las ofertas y bolsas fueron validadas en sandbox con conciliación completa;
- web y móvil comunican exactamente el beneficio que el backend aplica;
- las pruebas focalizadas y los gates pertinentes quedan verdes;
- la evidencia externa pendiente, si la hubiera, queda identificada como gate y no
  como implementación supuestamente terminada;
- `docs/00_current/` se actualiza con el contrato realmente desplegado y este ciclo
  cambia a `completed` solo después de esa verificación.
