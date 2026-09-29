# 0201 — Planes comerciales de lanzamiento y permanencia de la biblioteca propia

Status: accepted
Date: 2026-09-25

## Contexto

My Scoope ya contaba con modelos de planes, suscripciones, créditos, entitlements y
recaudación. También existían precios, cupos y mensajes comerciales implementados o
documentados en distintos momentos. Esos valores se definieron antes de cerrar una
propuesta comercial única y no deben seguir interpretándose como decisiones vigentes.

El análisis de pricing posterior aportó referencias competitivas e ideas de producto,
pero fue preparado sin conocer completamente el estado de implementación. Por ello no
se adopta como una obligación de construir nuevas funciones premium antes del
lanzamiento. El contrato comercial debe partir de capacidades que ya existen y dejar
las funciones pagadas futuras para el roadmap posterior.

Además, los límites comerciales no deben convertir la biblioteca del usuario en un
alquiler. Los elementos creados o incorporados legítimamente constituyen capital
digital del usuario y deben sobrevivir a una cancelación, mora o cambio a Free.

## Decisión

### 1. Matriz comercial de lanzamiento

Los tres planes de lanzamiento son Free, Basic y Pro. Sus beneficios y precios
canónicos son:

| Capacidad | Free | Basic | Pro |
|---|---:|---:|---:|
| Alimentos privados | Ilimitados | Ilimitados | Ilimitados |
| Comidas | 12 | Ilimitadas | Ilimitadas |
| Planes diarios | 4 | Ilimitados | Ilimitados |
| Programas guardados | 1 | Ilimitados | Ilimitados |
| Extensión máxima por programa | 2 semanas | 12 semanas | 12 semanas |
| Programas activos | 1 | 1 | 1 |
| Agregar desde Compartidos conmigo | 1 al mes | Ilimitado | Ilimitado |
| Comparaciones guardadas | 0 | Ilimitadas | Ilimitadas |
| Créditos mensuales | 0 | 150 | 1.000 |
| Precio mensual (CLP) | $0 | $3.990 | $6.990 |
| Precio anual (CLP) | $0 | $34.990 | $59.990 |

Los límites de Comidas, Planes diarios y Programas guardados son umbrales para crear
o incorporar nuevos elementos, no topes de almacenamiento ni instrucciones de
eliminación.

### 2. Propiedad y política no destructiva

Un elemento creado por el usuario o agregado legítimamente a su biblioteca personal
permanece suyo, con independencia del plan futuro.

Al cancelar, dejar de pagar o volver a Free:

- no se eliminan, ocultan, archivan automáticamente ni despublican elementos propios;
- los elementos existentes siguen visibles, editables, utilizables y compartibles;
- se retiran las capacidades exclusivas del plan pagado;
- si la biblioteca supera un umbral Free, se bloquea únicamente la creación o
  incorporación adicional de esa categoría hasta volver a quedar bajo el umbral o
  reactivar un plan que la permita;
- un Programa existente de más de 2 semanas no se recorta al volver a Free: conserva
  sus semanas y estas siguen siendo utilizables y editables; el límite de 2 semanas se
  aplica a la extensión nueva permitida bajo Free;
- nunca se exige borrar contenido propio como condición para usar Free.

La aplicación debe explicar el bloqueo en el momento de intentar una acción nueva y
ofrecer una vía de actualización de plan, sin presentar los elementos existentes como
secuestrados o perdidos.

### 3. Compartidos conmigo

Recibir y consultar un elemento compartido no es una capacidad premium. Todos los
planes pueden acceder al elemento recibido mientras el recurso compartido siga
disponible.

El elemento recibido es de solo lectura dentro de Compartidos conmigo. Para editarlo,
el usuario debe agregar una copia a su biblioteca personal:

- Free puede agregar 1 elemento recibido por mes;
- Basic y Pro pueden agregar elementos sin límite;
- una copia agregada pasa a ser un elemento propio y queda protegida por la política
  no destructiva;
- compartir un elemento propio no está limitado por el plan Free.

El cupo mensual se aplica a la acción de agregar a la biblioteca, no al número de
enlaces recibidos, vistas o remitentes.

### 4. Créditos y bolsas

Los créditos mensuales son una asignación periódica del plan, no acumulable entre
periodos. Free no recibe créditos mensuales y no puede comprar bolsas.

Basic y Pro pueden comprar cualquiera de estas bolsas:

| Bolsa | Precio (CLP) |
|---:|---:|
| 500 créditos | $2.990 |
| 1.000 créditos | $5.990 |
| 2.000 créditos | $9.990 |

Los créditos comprados:

- se mantienen separados de la asignación mensual;
- no expiran al terminar el periodo de suscripción;
- se consumen después de los créditos mensuales;
- permanecen en la cuenta después de un downgrade, aunque su uso queda suspendido
  mientras la cuenta esté en Free porque la ejecución con costo es una capacidad de
  los planes pagados.

Una tarea fallida técnicamente no consume créditos. El costo debe mostrarse antes de
confirmar una tarea pagada. El trabajo manual y determinístico sin costo externo no
consume créditos.

La tabla exacta de créditos por tarea no queda fijada por esta decisión. El ciclo de
implementación debe medir costos y calibrarla con esta referencia comercial:

```text
Basic: 150 créditos permiten aproximadamente 3 programas completos o equivalente.
Pro: 1.000 créditos permiten aproximadamente 20 programas completos o equivalente.
```

La equivalencia es un objetivo de diseño y validación, no una autorización para
publicar todavía una tarifa de 50 créditos por programa sin evidencia.

### 5. Alcance del lanzamiento

Este contrato no exige desarrollar nuevas funciones exclusivas para Basic o Pro. La
separación inicial se realizará sobre capacidades existentes, límites, créditos y
recaudación. El roadmap posterior podrá agregar nuevas capacidades premium mediante
decisiones y ciclos propios.

Para un usuario con poca experiencia nutricional, la dirección de producto para el
primer valor Free es obtener un Plan diario útil mediante un flujo determinístico y
de bajo costo, antes que generar un Programa completo. Es menos abrumador, requiere
menos creación de elementos y evita que la propuesta gratuita dependa de costo
variable de IA. Esta dirección queda registrada para un ciclo posterior y no forma
parte del ciclo comercial abierto por esta decisión.

## Precedencia y decisiones reemplazadas

Esta decisión reemplaza todo valor anterior incompatible de precios, cupos, créditos
incluidos, beneficios o disponibilidad de bolsas que aparezca en seeds, catálogos de
billing, pantallas, documentos de ciclos o material comercial. Esos registros pasan a
ser evidencia histórica o brecha de implementación, no autoridad comercial.

Se mantienen vigentes las fronteras arquitectónicas de decisiones anteriores:

- `accounts` continúa como autoridad de planes, suscripciones, entitlements y wallet;
- billing y los proveedores de pago continúan como evidencia de recaudación, no como
  autoridad del beneficio;
- tokens y costo de proveedor continúan como observabilidad interna;
- el ledger de créditos continúa siendo auditable y append-only.

La decisión `0008-ai-assisted-onboarding-to-first-plan.md` queda parcialmente
reemplazada respecto de la activación inicial Free: ya no se exige IA para entregar el
primer Plan diario. Sus límites de seguridad —cálculo interno, propuesta revisable y
aprobación explícita— siguen vigentes cuando se utilice una experiencia asistida.

## Consecuencias

- Código, migraciones, seeds, catálogo de cobro y comunicación comercial deben
  converger a una sola matriz.
- Downgrade y cancelación requieren pruebas explícitas de no destrucción.
- Las cuotas deben aplicarse en un servicio central de capacidades, no mediante
  ocultamiento o borrado oportunista en cada pantalla.
- La cuota de Compartidos conmigo necesita una medición mensual auditable e
  idempotente.
- Los saldos mensuales y comprados deben distinguirse en wallet y ledger.
- Deben validarse recaudación, renovación, cancelación, rechazo, reembolso y
  conciliación antes del cierre comercial.
- La implementación se realizará en
  `docs/10_active_cycles/commercial_launch_contract_cycle.md`.
