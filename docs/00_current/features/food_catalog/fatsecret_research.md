# Food Catalog · Research FatSecret API

## Estado

Investigación inicial para evaluar FatSecret como proveedor externo del subsistema Food Catalog.

Esta etapa no implementa integración técnica todavía. Su objetivo es definir el criterio de decisión antes de tocar el core nutricional.

## Decisión preliminar

FatSecret puede ser una fuente externa valiosa para acelerar cobertura de alimentos, marcas, porciones y códigos de barra.

No debe convertirse en la fuente de verdad de MyScoope.

Mientras no exista un acuerdo explícito que permita persistir datos nutricionales, porciones, nombres y marcas en la BBDD de MyScoope, y mientras la atribución no sea compatible con la UX deseada, FatSecret debe tratarse como fuente externa temporal/no canónica.

La fuente de verdad debe ser Food Catalog App: un sistema propio de MyScoope, con alimentos normalizados, trazables, versionables y publicados bajo estados de confianza.

```text
FatSecret / USDA / Open Food Facts / Carga manual / Validación profesional
        ↓
Food Catalog ingestion layer
        ↓
Normalización + deduplicación + control de calidad
        ↓
Catálogo canónico MyScoope
        ↓
Meals / DailyPlans / Programs / Comparators / Proposals / Explore
```

## Principio arquitectónico

MyScoope no delega su modelo nutricional a proveedores externos.

Los proveedores externos entregan candidatos alimentarios. Todo candidato debe pasar por un contrato interno antes de poder alimentar entidades de gestión nutricional.

## Hallazgos relevantes

### Cobertura y capacidades

FatSecret Platform API declara una base global de alimentos y nutrición, con alimentos comunes, productos de marca, restaurantes, imágenes y datos localizados.

Capacidades relevantes para MyScoope:

- búsqueda de alimentos por texto;
- detalle nutricional por alimento;
- búsqueda por código de barras;
- localización por región e idioma en cuentas habilitadas;
- datos de alimentos comunes, productos comerciales y restaurantes;
- posibles atributos avanzados según edición de API.

### Endpoints inicialmente relevantes

| Necesidad MyScoope | Endpoint/capacidad FatSecret | Uso esperado |
| --- | --- | --- |
| Buscar candidatos externos | Food Search | Búsqueda asistida desde creación/importación de alimentos. |
| Obtener detalle nutricional | Food Details | Preview y normalización antes de guardar. |
| Buscar por código de barras | Barcode lookup | Flujo mobile/PWA para productos comerciales. |
| Localizar resultados | Region/language | Evaluar Chile, España, México, Argentina y Colombia. |

## Riesgos y restricciones a validar

### 1. Persistencia y cache

La documentación de FatSecret distingue datos almacenables y no almacenables. Antes de implementar, hay que confirmar expresamente qué campos se pueden guardar indefinidamente en la base de datos de MyScoope.

Riesgo: crear un catálogo propio a partir de datos externos podría incumplir términos si se almacenan campos no permitidos.

### 2. Atribución

FatSecret exige atribución en ciertos tiers. Antes de usar resultados en UI, hay que confirmar si MyScoope debe mostrar badge/snippet de FatSecret en:

- búsqueda externa;
- preview de candidato;
- ficha de Food importado;
- foods usados dentro de Meals y DailyPlans;
- alimentos compartidos o publicados.

### 3. Pricing y límites

La edición gratuita puede no cubrir todas las capacidades necesarias. Barcode, localización avanzada, imágenes o endpoints nuevos pueden requerir Premier o habilitación especial.

Antes de implementar, hay que estimar costo para:

- 1.000 búsquedas mensuales;
- 10.000 búsquedas mensuales;
- 100.000 búsquedas mensuales;
- uso intensivo por profesionales;
- cache local permitido vs consultas repetidas obligatorias.

### 4. Calidad y confianza

Aunque el proveedor declare datos verificados, MyScoope debe mantener estados propios de confianza.

Estados sugeridos:

```text
external_candidate
imported
normalized
pending_review
verified
rejected
deprecated
```

### 5. Duplicados y equivalencias

La integración puede introducir duplicados con alimentos existentes de usuario, core catalog o USDA.

Ejemplos esperados:

```text
Avena
Avena tradicional
Quaker Avena
Oats
Rolled oats
```

El sistema debe tratar deduplicación como parte del contrato de Food Catalog, no como detalle de UI.

## Contrato interno sugerido

El entorno de gestión alimentaria no debe conocer estructuras FatSecret.

Todo proveedor externo debe transformarse a un candidato canónico.

```python
@dataclass(frozen=True)
class CanonicalFoodCandidate:
    provider: str
    provider_food_id: str
    provider_serving_id: str | None
    name: str
    brand_name: str | None
    country: str | None
    language: str | None
    serving_description: str | None
    serving_quantity_g: Decimal | None
    calories_kcal_per_100g: Decimal
    protein_g_per_100g: Decimal
    carbs_g_per_100g: Decimal
    fat_g_per_100g: Decimal
    fiber_g_per_100g: Decimal | None
    sugar_g_per_100g: Decimal | None
    sodium_mg_per_100g: Decimal | None
    source_url: str | None
    attribution_required: bool
    verification_status: str
    confidence_score: Decimal | None
```

## Preguntas que bloquean implementación

Antes de codear una integración real, responder:

1. ¿Qué tier de FatSecret permite búsqueda, detalle, barcode y localización?
2. ¿Qué campos pueden guardarse indefinidamente en la BBDD de MyScoope?
3. ¿Qué atribución exige cada tier y dónde debe mostrarse?
4. ¿La localización incluye regiones prioritarias para MyScoope: CL, ES, MX, AR y CO?
5. ¿Barcode está disponible en el tier objetivo?
6. ¿Hay límites por día, por mes o por usuario final?
7. ¿Se permite usar datos importados en contenidos compartidos con clientes?
8. ¿Se permite que alimentos importados pasen a catálogo global visible para otros usuarios?
9. ¿Cómo se deben borrar o actualizar datos si FatSecret cambia o retira contenido?
10. ¿Cuál es el costo estimado por usuario profesional activo?

## Spike técnico recomendado

Crear una prueba aislada, sin modificar modelos ni views productivas.

Alcance mínimo:

```text
services/food_catalog/providers/fatsecret/
```

Objetivos:

- autenticar contra FatSecret con variables de entorno;
- ejecutar búsqueda por texto;
- leer detalle de un alimento;
- probar barcode si el tier lo permite;
- transformar respuesta a `CanonicalFoodCandidate`;
- no persistir datos reales todavía;
- dejar fixtures sanitizadas para tests.

Variables de entorno previstas:

```text
FATSECRET_CLIENT_ID=
FATSECRET_CLIENT_SECRET=
FATSECRET_API_BASE_URL=https://platform.fatsecret.com/rest/server.api
FATSECRET_REGION=CL
FATSECRET_LANGUAGE=es
```

## Criterio de avance a Etapa 2

Avanzar solo si se cumple:

- términos de persistencia/cache compatibles con el catálogo canónico;
- atribución aceptable para la UX de MyScoope;
- endpoint de búsqueda estable;
- detalle nutricional suficiente para kcal, proteína, carbohidratos y grasa por 100 g;
- costo razonable para uso inicial;
- localización útil para al menos Chile y España, o alternativa clara para compensar.

## Criterio de rechazo temporal

No integrar todavía si:

- no se permite guardar datos nutricionales normalizados;
- la atribución obligatoria invade demasiado la experiencia de planes/meals;
- barcode o localización requieren un plan comercial no viable;
- la calidad de resultados en español es baja;
- los términos impiden promover alimentos importados a catálogo global.

## Resultado esperado de la etapa

Al cerrar esta etapa debe existir una decisión explícita:

```text
FatSecret no se usará como base principal del catálogo canónico sin acuerdo comercial/legal específico.

Food Catalog App priorizará fuentes persistentes, alimentos naturales verificados, carga directa de marcas, alimentos creados por usuarios y curaduría profesional.
```

La decisión principal del sistema queda documentada en:

```text
docs/00_current/features/food_catalog/food_catalog_app.md
```

```text
FatSecret aprobado como provider externo experimental
FatSecret aprobado solo para búsqueda/barcode sin persistencia
FatSecret postergado por restricciones legales/comerciales
FatSecret descartado
```

La decisión debe quedar registrada en `docs/20_decisions/` si se avanza a implementación.
