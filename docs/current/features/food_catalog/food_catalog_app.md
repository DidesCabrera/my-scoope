# Food Catalog App

## Estado

Decisión vigente: Food Catalog debe evolucionar como una aplicación/sistema independiente dentro de MyScoope.

No debe ser tratado como una extensión menor del entorno de gestión alimentaria ni como un importador de `Food`.

## Decisión

MyScoope separa conceptualmente dos sistemas:

```text
Food Catalog App
    Responsable de adquirir, investigar, normalizar, validar, versionar y publicar alimentos confiables.

Nutrition Management App
    Responsable de usar alimentos ya publicados para construir Meals, DailyPlans, Programs, Comparators, Proposals y Explore.
```

El entorno de gestión nutricional consume alimentos a través de un contrato definido. No conoce ni depende de fuentes externas, procesos de importación, agentes de investigación, acuerdos con marcas ni reglas de licenciamiento.

## Motivación

La base de datos de alimentos no es una tabla auxiliar. Es un activo estratégico del producto.

La experiencia previa con USDA mostró que una fuente técnicamente ordenada puede producir una mala experiencia para usuarios hispanohablantes si los nombres, porciones, categorías y alimentos no son naturales para la región objetivo.

La evaluación de FatSecret mostró que una base comercial puede tener gran cobertura y excelente experiencia de búsqueda, pero también restricciones de persistencia, atribución y dependencia estratégica.

Por lo tanto, MyScoope debe construir una base alimentaria propia, curada, trazable y local, combinando fuentes persistentes, carga directa de marcas, alimentos creados por usuarios y revisión profesional.

## Principio central

```text
Food Catalog App produce alimentos canónicos.
Nutrition Management App consume alimentos canónicos.
```

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
- cálculo de KPIs de planes.

Estos sistemas solo deben usar alimentos ya publicados o alimentos privados creados por el usuario bajo contrato estable.

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

Esa información queda disponible para auditoría, administración y curaduría, pero no contamina el core de Meals/DailyPlans/Programs.

## Contrato mínimo sugerido

```python
@dataclass(frozen=True)
class PublishedFoodSnapshot:
    food_id: int
    display_name: str
    category: str | None
    country: str | None
    serving_basis: str
    calories_kcal_per_100g: Decimal
    protein_g_per_100g: Decimal
    carbs_g_per_100g: Decimal
    fat_g_per_100g: Decimal
    fiber_g_per_100g: Decimal | None
    sugar_g_per_100g: Decimal | None
    sodium_mg_per_100g: Decimal | None
    verification_status: str
    version: str
```

## Contrato de entrada para candidatos

Todo flujo de ingreso debe producir candidatos estructurados.

```python
@dataclass(frozen=True)
class FoodCandidate:
    candidate_id: str
    source_type: str
    source_name: str
    source_license_status: str
    display_name: str
    canonical_name: str | None
    brand_name: str | None
    country: str | None
    language: str
    is_branded: bool
    nutrients_per_100g: dict
    serving_options: list
    aliases: list[str]
    evidence: list
    confidence_score: Decimal | None
    warnings: list[str]
    review_status: str
```

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

## Implicancias para implementación futura

El sistema puede iniciar dentro del monolito Django, pero con frontera explícita.

Estructura futura sugerida:

```text
food_catalog/
  domain/
  application/
  infrastructure/
    providers/
    importers/
  presentation/
  management/commands/
```

Mientras siga dentro de `notas`, debe respetar la frontera conceptual:

```text
notas/food_catalog/...
```

o servicios equivalentes claramente separados.

No se deben seguir agregando importadores o reglas de catálogo dentro de views, formularios o flujos de gestión nutricional.

## Roadmap sugerido

### Etapa 1 — Documentación y contrato

- cerrar esta decisión en docs;
- definir contrato `FoodCandidate`;
- definir contrato `PublishedFoodSnapshot`;
- documentar fuentes permitidas/no permitidas;
- documentar estados de revisión.

### Etapa 2 — Reestructuración interna mínima

- aislar importadores existentes;
- revisar y reparar import USDA como fuente secundaria;
- crear capa de candidatos antes de crear `Food`;
- registrar fuente/licencia/confianza.

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

## Decisión operativa actual

La prioridad ya no es integrar una gran BBDD externa como fuente principal.

La prioridad es construir Food Catalog App como sistema propio, con una base inicial pequeña pero confiable, natural para LATAM/España y defendible legalmente.
