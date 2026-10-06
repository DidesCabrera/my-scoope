# Onboarding Flow Normalization Cycle

Status: active — Native v2 implemented; Web normalization pending
Decision: `docs/20_decisions/0202-onboarding-storyboard-and-cross-platform-flow.md`
Implementation decision: `docs/20_decisions/0203-native-onboarding-v2-persistence-and-first-plan.md`
Related decisions: 0186, 0201, 0050, 0008

## Objective

Normalizar el flujo inicial de My Scoope entre Web y Native a partir de un
storyboard revisable en ambas galerías. El ciclo debe permitir iterar primero orden,
contenido y estética; solo después conectará las vistas aprobadas con autenticación,
persistencia, disclosures, selección comercial y Home.

El resultado buscado es un recorrido coherente que explique el sistema, capture los
datos necesarios para estimar mantenimiento y objetivos nutricionales, presente los
planes comerciales con una salida Free clara y entregue una transición comprensible
hacia el primer Home.

## Product hypothesis

Una persona comprenderá mejor My Scoope y completará con menos fricción su inicio si:

- ve el valor antes de responder preguntas;
- entiende la estructura Alimento → Comida → Plan diario → Programa;
- aprende que los paneles permiten pasar de una lectura simple a profundidad;
- sabe que la asistencia propone y calcula, pero no sustituye su decisión;
- completa su ficha en grupos breves con una razón visible para cada dato;
- recibe un resumen transparente antes de elegir un plan;
- puede comenzar con Free sin una barrera comercial artificial.

## Canonical storyboard baseline

```text
01 Login
02 Resultado y propuesta de valor
03 Estructura nutricional reutilizable
04 Navegación entre paneles: profundidad con sencillez
05 Asistencia, cálculo y control humano
06 Seguimiento y evolución
07 Disclosures
08 Objetivo personal
09 Datos personales: nacimiento y sexo
10 Medidas: altura y peso
11 Actividad habitual y training_frequency
12 Resumen del punto de partida
13 Planes Free / Basic / Pro
14 Home inicial
```

Esta es una baseline de diseño, no una obligación de conservar catorce pantallas.
Las revisiones pueden combinar pasos cuando mantengan claridad, ritmo y contratos.

## Scope

### Included

- storyboard no funcional en las galerías Web y Native;
- navegación lineal y acceso directo a cada vista;
- contenido y jerarquía equivalentes entre plataformas, sin exigir pixel parity;
- extracción de vistas presentacionales desde rutas/templates productivos;
- definición de estado visual vacío, seleccionado, resumido y de transición;
- captura futura de `goal`, `birth_date`, `sex`, `height_cm`, `weight_kg`,
  `activity_level` y `training_frequency`;
- decisión y pruebas sobre la semántica de `training_frequency` en el solver;
- presentación comercial Free, Basic y Pro alineada con 0201;
- normalización funcional posterior a la aprobación visual;
- pruebas focalizadas, accesibilidad básica y responsive layouts.

### Excluded from the storyboard stage

- autenticación OAuth real;
- writes de perfil o WeightLog;
- aceptación real de disclosures;
- compra, restauración o checkout;
- creación del primer Plan diario;
- cambios al Knowledge Center;
- publicación, PR, deploy o validación física antes de la aprobación visual.

## Invariants

- Las galerías importan componentes/partials productivos, no réplicas.
- Ninguna vista de galería llama APIs ni depende de una sesión real.
- Disclosures sigue siendo gate antes de la ficha corporal y Home mientras CML08
  no sea reemplazado explícitamente.
- Free siempre ofrece una continuación visible hacia Home.
- El storyboard no afirma que `training_frequency` afecte TDEE hasta resolver su
  regla en el solver.
- El cálculo productivo permanece en servicios internos; la UI no replica fórmulas.
- Web y Native comparten semántica, orden y contenido, pero conservan componentes y
  geometría propios de su plataforma.
- `admin_knowledge/` y su proyección documental quedan fuera de alcance.

## Work plan

### OFN00 — Baseline and inventory

- Congelar mediante fixtures el contenido inicial propuesto.
- Inventariar Login, Disclosures, onboarding, subscription y Home en ambas plataformas.
- Mapear cada vista a componentes existentes y detectar extracciones necesarias.
- Registrar diferencias de contenido o comportamiento sin corregirlas todavía.

Exit: matriz Web/Native/Gallery con una fila por vista y propietario claro.

### OFN01 — Storyboard contract

- Definir el modelo de datos de una vista de storyboard.
- Definir identificadores estables, orden, título, propósito y CTA de cada vista.
- Preparar fixtures compartidos conceptualmente, sin forzar JSX/HTML común.
- Definir navegación directa, anterior/siguiente y progreso.

Exit: contrato revisable que no depende de sesión, red ni base de datos.

### OFN02 — Native storyboard foundation

- Agregar `Onboarding` a `/dev/ui-gallery`.
- Incorporar marcos compacto y amplio.
- Renderizar las catorce vistas baseline con datos fijos y acciones inocuas.
- Mantener el storyboard separado de Expo Router, sesión y API.

Validation: `scripts/ci_mobile_visual_check.sh` con el test focalizado de galería.

Exit: todas las vistas pueden revisarse en la galería Native desde navegador y
development client.

### OFN03 — Web storyboard foundation

- Agregar el recorrido a `/app/dev/ui-system/`.
- Extraer partials productivos del onboarding web donde sea necesario.
- Mostrar viewport móvil y composición desktop sin duplicar markup productivo.
- Mantener forms, auth y compras como fixtures visuales sin submit efectivo.

Validation: tests focalizados de `notas.tests.test_ui_system_gallery` y onboarding.

Exit: todas las vistas pueden revisarse en la galería Web con los estilos reales.

### OFN04 — Content and information architecture review

- Revisar secuencia, cantidad de pasos, títulos, explicación y CTA.
- Validar específicamente la vista de navegación entre paneles.
- Confirmar qué datos se explican como necesarios y por qué.
- Reducir redundancia entre propuesta de valor, control humano y seguimiento.

Gate: aprobación humana explícita del orden y contenido antes de normalizar las
rutas productivas.

Exit: storyboard textual aprobado y fixtures actualizados en ambas galerías.

### OFN05 — Visual refinement

- Iterar ritmo, jerarquía, ilustración/iconografía, densidad y progreso.
- Revisar tamaños compactos, teclado potencial, scroll y targets táctiles.
- Alinear semánticamente Web y Native sin perseguir pixel parity.
- Comprobar contraste, roles, labels y reduced-motion cuando corresponda.

Validation: controles visuales focalizados durante cada iteración; ejecutar
`scripts/ci_mobile_iteration.sh` una sola vez al cerrar esta etapa.

Gate: aprobación visual/funcional del storyboard antes de integración.

### OFN06 — Training frequency semantics

- Determinar si `training_frequency` solo aporta contexto o modifica activity level,
  TDEE, objetivos, recomendaciones o confianza de la estimación.
- Evitar doble conteo entre actividad habitual y entrenamiento semanal.
- Documentar la regla aceptada y sus límites.
- Agregar pruebas puras del estimador y del NutritionSubjectContext.

Exit: semántica explícita, explicable y cubierta; si no afecta cálculo, el producto
lo comunica como contexto y no como variable del mantenimiento.

### OFN07 — Product flow normalization

- Conectar las vistas aprobadas a las rutas Web y Native.
- Mantener sesión/redirecciones en las rutas y presentación en componentes/partials.
- Evolucionar contratos API/persistencia solo si los nuevos datos lo requieren.
- Preservar aceptación versionada de disclosures y retorno seguro hacia Home.
- Integrar la elección Free/Basic/Pro sin acoplar la UI a un proveedor de cobro.

Validation: tests focalizados por frontera mientras se implementa.

Exit: ambos productos recorren la misma secuencia semántica con persistencia y gates
correctos.

### OFN08 — Integration and closure

- Ejecutar el gate local relevante una sola vez sobre el commit exacto a integrar.
- Para cambios mixtos de backend, schema, auth, billing o migraciones, usar el tier
  completo requerido por la política del repositorio.
- Probar el recorrido integrado y luego obtener evidencia distinta en staging/device.
- Actualizar documentación vigente y cerrar el ciclo sin tocar Knowledge Center.

Exit: Web, Native y galerías permanecen alineados y la evidencia de integración está
registrada sin duplicar suites equivalentes.

## Execution status — 2026-09-28

El ciclo alcanzó el gate conjunto de contenido y refinación visual. OFN00–OFN03
están implementados; OFN04–OFN05 quedan abiertos a la revisión humana del
storyboard. OFN06–OFN08 no comenzaron porque dependen de esa aprobación.

| Etapa | Estado | Evidencia |
|---|---|---|
| OFN00 | Complete | Inventario y diferencias consolidados en la matriz siguiente. |
| OFN01 | Complete | Contrato estable de catorce pasos en fixtures Web y Native. |
| OFN02 | Complete | Sección Onboarding disponible en `/dev/ui-gallery` con marcos de 414 y 375 pt. |
| OFN03 | Complete | Storyboard completo disponible en `/app/dev/ui-system/#onboarding-storyboard`. |
| OFN04 | Awaiting approval | Orden y contenido listos para revisión humana. |
| OFN05 | Awaiting approval | Primera composición visual inspeccionada; falta cerrar la iteración con feedback. |
| OFN06 | Not started | La UI solicita `training_frequency`, pero no afirma que modifique el cálculo. |
| OFN07 | Not started | Las rutas productivas permanecen sin cambios. |
| OFN08 | Not started | No corresponde integrar ni ejecutar gates amplios antes de la aprobación. |

### Executed inventory matrix

| # | Vista | Native gallery | Web gallery | Responsabilidad / diferencia pendiente |
|---:|---|---|---|---|
| 01 | Login | Fixture presentacional | Partial compartible | Auth real permanece en las rutas productivas. |
| 02 | Resultado y valor | Fixture presentacional | Partial compartible | Validar promesa y densidad del mensaje. |
| 03 | Estructura nutricional | Fixture presentacional | Partial compartible | Misma taxonomía, geometría propia por plataforma. |
| 04 | Navegación entre paneles | Componentes reales de panel | Markup visual equivalente | Validar que profundidad y sencillez queden explícitas. |
| 05 | Asistencia y control | Fixture presentacional | Partial compartible | No conecta AI ni aplica cambios. |
| 06 | Seguimiento | Fixture presentacional | Partial compartible | Métricas son datos de ejemplo, no historial real. |
| 07 | Disclosures | Fixture presentacional | Partial compartible | Aceptación versionada sigue en el flujo productivo. |
| 08 | Objetivo | Controles visuales | Partial compartible | No persiste selección. |
| 09 | Datos personales | Campos visuales | Partial compartible | No crea ni actualiza perfil. |
| 10 | Medidas | Campos visuales | Partial compartible | No crea `WeightLog`. |
| 11 | Actividad y entrenamiento | Controles visuales | Partial compartible | `training_frequency` se captura; su semántica sigue abierta. |
| 12 | Resumen | Fixture presentacional | Partial compartible | La cifra sirve para decidir formato; no ejecuta el solver. |
| 13 | Planes | Free / Basic / Pro | Free / Basic / Pro | Sin checkout, restauración ni asignación de plan. |
| 14 | Home inicial | Estado de llegada | Estado de llegada | No crea automáticamente el primer plan diario. |

### Validation evidence

- Native: `scripts/ci_mobile_visual_check.sh tests/contracts.test.ts`, 8/8 tests.
- Web: `manage.py test notas.tests.test_ui_system_gallery accounts.tests.test_onboarding`,
  8/8 tests con settings de desarrollo y el gate nutricional desactivado.
- Inspección visual: Login, paneles, actividad, planes y Home revisados en ambos
  storyboards; sin sesión, API, persistencia ni navegación productiva.
- No se ejecutó `ci_mobile_iteration.sh`: corresponde una sola vez cuando Felipe
  cierre la etapa de refinación visual.

## Implementation update — 2026-10-05

Felipe aprobó el storyboard Native refinado y autorizó una primera versión
funcional. El recorrido Native ahora:

- muestra las cinco vistas introductorias con swipe;
- mantiene Disclosures como gate antes de la ficha;
- captura y persiste objetivo, datos corporales, actividad, frecuencia de
  entrenamiento y preferencias alimentarias sin crear autoridades duplicadas;
- calcula mantenimiento y objetivos con el Target Estimator vigente;
- genera una propuesta concreta de Plan diario, la presenta para revisión y solo la
  aplica tras confirmación;
- permite elegir Free o continuar hacia suscripción, y reanuda etapas persistidas si
  la app se cierra.

La regla de OFN06 queda resuelta para esta versión: `activity_level` modifica TDEE y
`training_frequency` se conserva como contexto sin modificar el cálculo para evitar
doble conteo. OFN07 está completo en Native y pendiente en Web. OFN08 sigue pendiente
de integración/publicación y validación de despliegue.

Evidencia local de esta entrega:

- gate Native de iteración: lint, typecheck y 173 pruebas aprobadas;
- prueba integrada API: persistencia, estimación, generación, aplicación del Plan
  diario y finalización v2;
- 32 pruebas focalizadas de onboarding, identidad, perfil y contexto nutricional;
- migraciones y contrato OpenAPI regenerados sin drift.

## Review matrix

Cada vista debe revisarse con estas dimensiones:

| Dimensión | Pregunta |
|---|---|
| Propósito | ¿Qué debe comprender o decidir la persona? |
| Contenido | ¿La vista dice solo lo necesario para avanzar? |
| Continuidad | ¿Se entiende por qué viene antes y qué sigue después? |
| Profundidad | ¿Permite entender más sin abrumar? |
| Confianza | ¿Distingue cálculo, asistencia y decisión humana? |
| Comercial | ¿Free es una opción honesta y visible? |
| Plataforma | ¿La misma semántica funciona naturalmente en Web y Native? |
| Accesibilidad | ¿Se entiende sin depender solo de color, gesto o animación? |

## Validation strategy

Durante OFN02–OFN05 se usarán únicamente checks focalizados y Fast Refresh. No se
ejecutará typecheck global ni la suite móvil completa después de cada ajuste visual.

Al cerrar la refinación móvil se ejecutará una vez `ci_mobile_iteration.sh`. Antes de
integrar se elegirá el gate único que posea el riesgo final: `ci_mobile_checks.sh`
para una frontera exclusivamente móvil, o el gate completo cuando el cambio incluya
auth, billing, schema, migraciones u otras fronteras críticas.

La validación posterior a integración debe aportar evidencia diferente: recorrido
staging, configuración, migraciones o dispositivo físico; no una repetición de los
mismos tests locales.

## Resolved questions

1. `training_frequency` se persiste como contexto y no modifica TDEE en v2; evita
   doble conteo con `activity_level`.
2. Las cinco vistas explicativas se mantienen separadas y se recorren por swipe en
   Native.
3. El resumen muestra mantenimiento y objetivo nutricional calculados por el Target
   Estimator, no cifras calculadas en la UI.
4. Free es una elección explícita y completa el onboarding; Basic/Pro continúan a la
   vista de suscripción.
5. El primer Plan diario se genera como propuesta determinística, se revisa y se
   aplica antes de completar el onboarding. Queda en la biblioteca; no se calendariza
   ni fija en Home automáticamente.

## Remaining work

### Native integration and operational readiness

- aplicar la migración y confirmar el catálogo `solver_enabled` en staging;
- ejecutar smoke de cuenta nueva y reanudación en etapas persistidas;
- validar accesibilidad, teclado, scroll y swipe en dispositivo físico;
- validar compra/restauración al elegir Basic o Pro;
- revisar mensajes específicos cuando no exista una alternativa factible del Solver.

### Cross-platform completion

- implementar el producto Web sobre los mismos servicios y estado v2;
- mantener temporalmente `/api/v1/onboarding` v1 y retirarlo solo después de migrar
  Web y verificar consumidores;
- actualizar el storyboard Web para reflejar la secuencia final de quince vistas.

### Product evolution

- decidir si se guarda cada paso antes del análisis; la primera versión persiste la
  ficha completa al tocar “Analizar”;
- definir si el Plan diario aplicado se fija en Home o se calendariza mediante una
  decisión explícita posterior;
- agregar métricas de conversión y abandono por etapa;
- evaluar usos futuros de `training_frequency` con evidencia y pruebas nutricionales.

## Documentation closure

Cuando el flujo productivo quede aceptado, promover a documentación vigente:

- secuencia final y responsabilidad de cada vista;
- contrato definitivo de datos de onboarding;
- semántica resuelta de `training_frequency`;
- relación entre disclosures, plan comercial y Home;
- comandos de validación y evidencia de cierre.

El ciclo histórico `onboarding_nutrition_profile_cycle.md` no se reescribe: conserva
la historia del onboarding v1 que este ciclo evoluciona.
