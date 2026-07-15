# Food Catalog App

## Estado

Decisión vigente: Food Catalog debe evolucionar como una aplicación/sistema independiente dentro de MyScoope.

No debe ser tratado como una extensión menor del entorno de gestión alimentaria ni como un importador de `Food`.

Desde Patch 32 existe la app física `food_catalog`. Desde Patch 33 existe su primer contrato interno ejecutable:

```text
food_catalog/application/contracts.py
```

Desde Patch 34 existen los primeros modelos maestros persistentes:

```text
food_catalog/models.py
```

El contrato define candidatos, evidencia, nutrientes normalizados, snapshots publicados y payloads preparados para protocolos internos hacia `notas.Food`. Los modelos maestros persisten alimentos canónicos, porciones, aliases, fuentes/evidencia e import batches. Desde Patch 35 existe el primer protocolo de snapshot operacional hacia `notas.Food`. Desde Patch 36 los adaptadores puros de importación viven en `food_catalog/application/imports/`. Desde Patch 37 existen comandos propios y acciones admin iniciales para importar candidatos maestros en `food_catalog` sin escribir `notas.Food`. Desde Patch 39 existe un backfill interno desde alimentos operativos confiables de `notas.Food` hacia candidatos maestros de `food_catalog`. Desde Patch 40 el ciclo queda cerrado con tests de frontera adicionales y export focalizado reforzado. Nada de esto se expone a MCP.

## Decisión

MyScoope separa conceptualmente dos sistemas:

```text
Food Catalog App
    Responsable de adquirir, investigar, normalizar, validar, versionar y publicar alimentos confiables.

Nutrition Management App
    Responsable de usar alimentos ya publicados para construir Meals, DailyPlans, Programs, Comparators, Proposals y Explore.
```

El entorno de gestión nutricional consume alimentos a través de `notas.Food`. No conoce ni depende de fuentes externas, procesos de importación, agentes de investigación, acuerdos con marcas ni reglas de licenciamiento.

MCP sigue la misma regla operacional: no accede a Food Catalog directamente y solo puede usar alimentos disponibles como `notas.Food`.

## Motivación

La base de datos de alimentos no es una tabla auxiliar. Es un activo estratégico del producto.

La experiencia previa con USDA mostró que una fuente técnicamente ordenada puede producir una mala experiencia para usuarios hispanohablantes si los nombres, porciones, categorías y alimentos no son naturales para la región objetivo.

La evaluación de FatSecret mostró que una base comercial puede tener gran cobertura y excelente experiencia de búsqueda, pero también restricciones de persistencia, atribución y dependencia estratégica.

Por lo tanto, MyScoope debe construir una base alimentaria propia, curada, trazable y local, combinando fuentes persistentes, carga directa de marcas, alimentos creados por usuarios y revisión profesional.

## Principio central

```text
Food Catalog App produce alimentos maestros/canónicos.
Protocolos internos materializan o actualizan notas.Food.
Nutrition Management App y MCP consumen únicamente notas.Food.
```

## Decisión híbrida: fuente maestra y snapshot operativo

Food Catalog App no reemplaza inicialmente a `notas.Food`.

MyScoope separa dos responsabilidades:

```text
food_catalog.CatalogFood
    fuente maestra del catálogo; curada, versionada, trazable y publicable

notas.Food
    snapshot operativo; usado por MealFood, Meals, DailyPlans, Programs, Comparators y Proposals
```

La relación deseada es:

```text
CatalogFood publicado
    ↓ crea / sugiere / refresca explícitamente
notas.Food snapshot
    ↓ usado por el core nutricional
MealFood / Meal / DailyPlan / Program / Proposal
```

Regla dura:

```text
Meals, DailyPlans, Programs, Proposals, Comparators, Solver y MCP no deben depender directamente de CatalogFood.
Deben depender de notas.Food para preservar estabilidad operativa e histórica.
```

Esta decisión evita que una actualización del catálogo maestro cambie automáticamente los cálculos de planes ya creados. Cuando un `Food` operativo se origine desde Food Catalog, debe conservar los valores nutricionales necesarios como snapshot y, opcionalmente, una referencia trazable al alimento maestro.

Si un alimento existe solo como `CatalogFood` y todavía no fue materializado como `notas.Food`, no existe para MCP ni para los flujos operativos de planificación.

Ninguna entidad de gestión nutricional debe alimentarse directamente desde:

- FatSecret;
- USDA/FoodData Central;
- Open Food Facts;
- tablas públicas;
- planillas de marcas;
- agentes de IA;
- scraping;
- carga manual no revisada.

Toda fuente debe entrar primero como candidato y pasar por reglas explícitas.

## Límite de sistema

### Dentro de Food Catalog App

- investigación de fuentes alimentarias;
- definición de fuentes permitidas y licencias;
- importación controlada;
- normalización a nutrientes por 100 g;
- aliases y nombres naturales en español;
- nombres regionales;
- porciones comunes;
- deduplicación;
- equivalencias;
- estados de confianza;
- revisión humana/profesional;
- versionado nutricional;
- publicación de alimentos globales;
- retiro/deprecación de alimentos;
- auditoría de origen;
- carga directa de marcas;
- generación asistida de candidatos con IA.

### Fuera de Food Catalog App

- composición de Meals;
- composición de DailyPlans;
- composición de Programs;
- comparadores nutricionales;
- propuestas IA sobre planes/comidas;
- Explore;
- sharing/inbox;
- cálculo de KPIs de planes;
- herramientas MCP y AI tools operativas.

Estos sistemas solo deben usar alimentos disponibles como `notas.Food`, ya sea porque fueron creados por el usuario, importados, publicados como globales o materializados desde Food Catalog mediante protocolos internos.

## Tipos de alimentos/candidatos

### Natural Verified

Alimentos naturales, genéricos o preparaciones base, curados desde fuentes públicas, oficiales, académicas o profesionalmente validadas.

Ejemplos:

- pechuga de pollo cocida;
- arroz blanco cocido;
- avena tradicional;
- palta;
- marraqueta;
- lentejas cocidas.

### Brand Verified

Productos comerciales entregados directamente por marcas o validados a partir de etiqueta nutricional verificable.

Ejemplos:

- yogur griego de marca local;
- whey protein;
- barras proteicas;
- productos con código de barra.

Regla: la marca puede entregar datos, pero MyScoope mantiene la revisión antes de publicar.

### User Created

Alimentos creados por usuarios para uso personal.

Pueden convertirse en candidatos al catálogo global solo si pasan por revisión, normalización y trazabilidad.

### External Temporary

Resultados externos temporales provenientes de APIs con restricciones de persistencia o atribución.

No alimentan el catálogo canónico salvo que exista permiso explícito compatible con las reglas de MyScoope.

FatSecret entra en esta categoría mientras no exista acuerdo comercial que permita persistencia amplia y condiciones de atribución aceptables.

## Estados sugeridos

```text
external_candidate
manual_candidate
brand_submitted
normalized
pending_review
needs_more_evidence
reviewed
verified
published
rejected
deprecated
archived
```

## Contrato de salida hacia gestión nutricional

El contrato de consumo debe ser estable y simple.

Food Catalog publica alimentos maestros. La gestión nutricional y MCP deben recibir o usar snapshots operativos en `notas.Food`, no depender del detalle interno de importación o curaduría.

El entorno de gestión nutricional necesita alimentos con:

```text
id interno estable
nombre visible natural
macros por 100 g
kcal por 100 g
porciones comunes opcionales
estado de publicación/confianza
snapshot nutricional usable
```

No necesita conocer:

```text
fuente original
licencia específica
proceso de importación
si fue investigado por IA
si vino de marca
si vino de tabla pública
si fue deduplicado
```

Esa información queda disponible para auditoría, administración y curaduría, pero no contamina el core de Meals/DailyPlans/Programs ni el contrato MCP.

## Contratos internos ejecutables

Desde Patch 33, el contrato interno vive en:

```text
food_catalog/application/contracts.py
```

Desde Patch 36, los contratos y adaptadores puros de importación viven en:

```text
food_catalog/application/imports/
```

Esta carpeta contiene DTOs de importación, normalizadores, validaciones defensivas y adaptadores USDA. Son piezas de adquisición/curaduría, no herramientas MCP y no escriben directamente Meals, DailyPlans, Programs ni Proposals.

Desde Patch 37, la persistencia de importación catalog-first vive fuera de la capa pura de aplicación:

```text
food_catalog/infrastructure/imports/
```

Esta capa puede usar Django y `food_catalog.models` para crear `CatalogFood`, `CatalogFoodSource` y `CatalogImportBatch`, pero no importa `notas` ni MCP. Los comandos iniciales son:

```text
python manage.py dry_run_catalog_usda_foods_json <path> --source-version <version>
python manage.py import_catalog_usda_foods_json <path> --source-version <version>
```

Desde Patch 39, el backfill desde alimentos operativos confiables vive deliberadamente en `notas`, porque lee `notas.Food`:

```text
notas/application/services/commands/food_catalog_backfill.py
python manage.py backfill_catalog_from_operational_foods --dry-run
python manage.py backfill_catalog_from_operational_foods
```

Este bridge crea candidatos maestros y evidencia en `food_catalog`, pero no actualiza el alimento operativo de origen, no publica automáticamente el catálogo y no cambia el contrato MCP.

Estos comandos importan candidatos maestros, no alimentos operacionales. Para que un candidato publicado esté disponible en Meals o MCP, sigue siendo obligatorio materializarlo como `notas.Food` mediante el protocolo de snapshot.

Este contrato no es una herramienta MCP ni una API pública para planificación. Es una capa de payloads puros para que Food Catalog pueda construir datos curados antes de que un protocolo backend futuro los materialice como `notas.Food`.

Contratos principales:

```text
NutrientProfilePer100g
CatalogServingOption
CatalogEvidenceItem
CatalogFoodCandidate
PublishedFoodSnapshot
OperationalFoodSnapshotPayload
```

Reglas de estos contratos:

```text
no importan django
no importan notas
no importan mcp_server
no crean registros en base de datos
no reemplazan a notas.Food
```

`PublishedFoodSnapshot` representa una publicación estable de Food Catalog. Su salida hacia gestión nutricional es `OperationalFoodSnapshotPayload`, que usa nombres compatibles con `notas.Food`, pero sigue siendo solo un payload interno.

El protocolo real que escribe o refresca `notas.Food` vive en `notas/application/services/food_catalog_snapshots.py` desde Patch 35.

## Modelos maestros persistentes

Desde Patch 34, Food Catalog posee tablas propias para persistir la curaduría del catálogo maestro:

```text
CatalogFood
CatalogFoodPortion
CatalogFoodAlias
CatalogFoodSource
CatalogImportBatch
```

Estos modelos viven en `food_catalog.models` y representan el estado maestro de investigación, normalización, evidencia, revisión y publicación. Sus IDs pertenecen al catálogo maestro y no son IDs operacionales de alimentos.

Regla dura:

```text
CatalogFood.id o CatalogFood.catalog_ref no son food_id válidos para Meals, DailyPlans, Programs, Proposals, Solver ni MCP.
```

La única forma de hacer disponible un alimento maestro para planificación es mediante un protocolo backend explícito que cree o refresque un `notas.Food` snapshot. Desde Patch 35, ese protocolo inicial vive en `notas/application/services/food_catalog_snapshots.py`.

## Contrato de entrada para candidatos

Todo flujo de ingreso debe producir candidatos estructurados mediante `CatalogFoodCandidate`. Un candidato puede contener:

```text
candidate_ref
source_type
source_name
source_license_status
display_name
canonical_name
brand_name
country
language
is_branded
nutrients_per_100g
serving_options
aliases
evidence
confidence_score
warnings
review_status
```

Un candidato no es operacional. Debe ser revisado, publicado y luego materializado internamente como `notas.Food` antes de estar disponible para Meals, DailyPlans, Programs, Proposals, Solver o MCP.

## Fuentes prioritarias

### Alimentos naturales/genéricos

Priorizar fuentes públicas, oficiales o académicas con licencia clara o uso permitido.

Fuentes a investigar/usar según país:

- Chile: INTA / tablas chilenas de composición de alimentos;
- España: BEDCA;
- LATAM: FAO/INFOODS y tablas nacionales;
- base técnica secundaria: USDA/FoodData Central cuando sirva como referencia nutricional;
- curaduría profesional propia cuando no exista fuente regional suficiente.

### Productos comerciales

Priorizar levantamiento directo con marcas y etiquetas nutricionales verificables.

Flujo esperado:

```text
marca entrega ficha nutricional
↓
MyScoope valida formato y consistencia
↓
se normaliza a 100 g
↓
se revisa evidencia/etiqueta
↓
se publica como Brand Verified
```

### Fuentes externas cerradas

APIs como FatSecret pueden investigarse, pero no deben poblar la base canónica salvo que exista permiso explícito para:

- persistir nombres;
- persistir macros;
- persistir porciones;
- usar datos en planes históricos;
- publicar alimentos en catálogo global;
- cumplir atribución de forma aceptable para UX/producto.

## Uso de IA/agentes

La IA puede asistir el proceso de curaduría, pero no debe publicar alimentos automáticamente.

Uso permitido:

```text
agente investigador → encuentra fuentes permitidas
agente normalizador → convierte a contrato MyScoope
agente QA → detecta inconsistencias
agente UX local → propone nombre natural, aliases y porciones
agente crítico → recomienda aprobar/rechazar/solicitar evidencia
humano/profesional → aprueba publicación
```

Regla dura:

```text
AI genera candidatos trazables. MyScoope publica solo después de revisión.
```

## Criterios de calidad

Un alimento no debe publicarse si:

- no tiene fuente o evidencia clara;
- la licencia está restringida o es incierta;
- los macros no cuadran razonablemente con las kcal;
- no puede normalizarse a 100 g;
- el nombre visible no es natural para usuarios hispanohablantes;
- se confunde con otro alimento existente;
- no se sabe si corresponde a alimento crudo/cocido;
- no se sabe si incluye piel, aceite, salsa, líquido u otra preparación relevante.

## Implicancias para implementación

El sistema inicia dentro del monolito Django, pero con frontera explícita.

Desde Patch 32 existe la app física:

```text
food_catalog/
  application/
  domain/
  infrastructure/
  management/commands/
  migrations/
  tests/
```

Modelos futuros recomendados dentro de esa app:

```text
CatalogFood
CatalogFoodPortion
CatalogFoodAlias
CatalogFoodSource
CatalogImportBatch
CatalogFoodVersion
```

`notas.Food` debe mantenerse como entidad operativa del producto nutricional. En una etapa futura puede recibir campos trazables, por ejemplo una referencia opcional al alimento maestro y metadata de snapshot, pero no debe convertirse en un proxy obligatorio de `CatalogFood`.

La app `food_catalog` creada en Patch 32 no define modelos todavía. Los modelos maestros deben introducirse en patches posteriores y no deben ser consumidos directamente por MCP ni por entidades operativas de `notas`.

Aunque Food Catalog siga dentro del monolito, debe respetar la frontera conceptual:

```text
food_catalog/...
```

No se deben seguir agregando importadores o reglas de catálogo dentro de views, formularios o flujos de gestión nutricional.

No se deben agregar herramientas MCP que consulten `food_catalog`. Las herramientas MCP pueden conservar nombres históricos como `list_food_catalog`, pero deben leer `notas.Food` y devolver IDs operativos de `notas.Food`.

## Roadmap sugerido

### Etapa 1 — Documentación y contrato

- cerrar esta decisión en docs;
- definir contrato `FoodCandidate`;
- definir contrato `PublishedFoodSnapshot`;
- documentar fuentes permitidas/no permitidas;
- documentar estados de revisión;
- documentar que `notas.Food` es snapshot operativo y `CatalogFood` será fuente maestra.

### Etapa 2 — Reestructuración interna mínima

- aislar importadores existentes;
- revisar y reparar import USDA como fuente secundaria;
- crear capa de candidatos antes de crear/actualizar snapshots operativos `Food`;
- registrar fuente/licencia/confianza;
- definir protocolos internos para `create_operational_food_snapshot` y `refresh_operational_food_snapshot`;
- asegurar que esos protocolos creen/actualicen `notas.Food` y no expongan `CatalogFood` al MCP.

### Etapa 3 — Natural Verified Seed

- lista inicial de 100-300 alimentos fitness hispanohablantes;
- nombres naturales en español;
- aliases regionales;
- normalización a 100 g;
- revisión manual.

### Etapa 4 — Brand Verified Intake

- plantilla CSV/XLSX para marcas;
- importador dry-run;
- validación de kcal/macros;
- evidencia de etiqueta;
- publicación controlada.

### Etapa 5 — Agentes de investigación

- comando interno para generar candidatos;
- evidencia y licencia por fuente;
- QA automático;
- revisión humana antes de publicar.



## Estado Patch 40 · cierre del ciclo 32-40

Patch 40 cierra el ciclo de separación de Food Catalog.

El estado vigente queda definido así:

```text
food_catalog.CatalogFood
    fuente maestra interna de curaduría

notas.Food
    snapshot operacional y única verdad nutricional de planificación

MCP
    consumidor de herramientas operativas; solo ve notas.Food
```

Guardas ejecutables agregadas o reforzadas:

- `food_catalog.application` no importa Django, `notas` ni MCP;
- `food_catalog.infrastructure` no importa `notas` ni MCP;
- comandos de `food_catalog` no importan `notas` ni MCP;
- modelos maestros no referencian entidades operacionales como Meals, DailyPlans, Programs o Proposals;
- DTOs de alimentos para AI/MCP exponen `food_id` operacional, no `catalog_food_id`;
- campos de trazabilidad en `notas.Food` siguen siendo metadata primitiva, no `ForeignKey` a `CatalogFood`;
- el modo de exportación `foodcatalog` incluye tests de frontera para futuras iteraciones.

A partir de este punto, nuevos trabajos deberían tratar Food Catalog como una app separada ya establecida. La siguiente etapa natural es construir capacidades de curaduría, versionado y publicación controlada sobre esta frontera, no volver a mezclar el catálogo maestro con los flujos operativos.

## Decisión operativa actual

La prioridad ya no es integrar una gran BBDD externa como fuente principal.

La prioridad es construir Food Catalog App como sistema propio, con una base inicial pequeña pero confiable, natural para LATAM/España y defendible legalmente.

## Estado Patch 38 · frontera MCP endurecida

MCP no es consumidor de Food Catalog.

El nombre `list_food_catalog` existe solo por compatibilidad histórica con el protocolo MCP/API. Su significado vigente es:

```text
listar alimentos operativos disponibles desde notas.Food
```

No significa buscar en `food_catalog.CatalogFood`, no expone `catalog_food_id` y no puede crear snapshots. La disponibilidad de alimentos para IA/MCP depende de procesos internos que materializan o actualizan `notas.Food`.

