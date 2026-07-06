# Domain Model Boundaries

## Objetivo

`notas.domain.models` sigue siendo el punto público de compatibilidad para los
modelos Django del monolito. El objetivo de este documento es hacer explícitas
sus fronteras y permitir una modularización física progresiva sin romper imports
existentes como:

- `from notas.domain.models import Food, Meal, DailyPlan`

La fuente ejecutable de esta clasificación está en:

- `notas/domain/model_boundaries.py`

Los tests verifican que cada clase `models.Model` del dominio pertenezca a una
sola frontera y que las relaciones entre modelos no crucen fronteras fuera de la
matriz permitida. Desde el Patch 29, los tests leen tanto el módulo de
compatibilidad `notas/domain/models.py` como los módulos ya extraídos en
`notas/domain/model_modules/`.

## Estado Patch 29

El primer split físico ya se hizo con grupos de bajo riesgo:

| Frontera | Módulo físico | Contrato público |
|---|---|---|
| Auth Integration | `notas/domain/model_modules/auth_integration.py` | reexportado desde `notas.domain.models` |
| Comparisons | `notas/domain/model_modules/comparisons.py` | reexportado desde `notas.domain.models` |

Esto reduce el tamaño del archivo legacy sin cambiar la app Django, las
migraciones ni los imports usados por el resto del sistema.

## Estado Patch 30

El segundo split físico mueve dos fronteras adicionales:

| Frontera | Módulo físico | Contrato público |
|---|---|---|
| Identity & User State | `notas/domain/model_modules/identity.py` | reexportado desde `notas.domain.models` |
| Sharing | `notas/domain/model_modules/sharing.py` | reexportado desde `notas.domain.models` |

`sharing.py` usa referencias ORM diferidas por nombre para apuntar a `Food`,
`Meal`, `DailyPlan`, `DailyPlanMeal` y `Program` sin crear imports circulares
contra el módulo de compatibilidad.

## Estado Patch 31

El tercer split físico mueve la frontera de propuestas IA a un módulo propio:

| Frontera | Módulo físico | Contrato público |
|---|---|---|
| AI Proposals | `notas/domain/model_modules/proposals.py` | reexportado desde `notas.domain.models` |

`proposals.py` mantiene referencias ORM diferidas por nombre hacia `DailyPlan` y
`NutritionProposal` para evitar imports circulares con el módulo de compatibilidad.
Esto deja el dominio de revisión IA más visible sin cambiar la app Django, las
migraciones ni los imports públicos existentes.

## Estado Patch 32

Se crea la app Django física `food_catalog` como frontera independiente del catálogo maestro.

La frontera alimentaria que permanece dentro de `notas` debe interpretarse como **Operational Food Snapshot**, no como el catálogo maestro final.

Regla vigente:

```text
food_catalog = catálogo maestro interno / curaduría / publicación futura
notas.Food = única verdad nutricional operacional
MCP = solo consume notas.Food
```

## Estado Patch 34

`food_catalog` ahora define modelos maestros persistentes propios:

| Modelo | Responsabilidad |
|---|---|
| `CatalogFood` | alimento maestro/canónico del catálogo; no operacional |
| `CatalogFoodPortion` | porciones curadas del alimento maestro |
| `CatalogFoodAlias` | aliases y nombres localizados para búsqueda/curaduría |
| `CatalogFoodSource` | evidencia, fuente, licencia, hashes y atribución |
| `CatalogImportBatch` | ejecución de importaciones/dry-runs de catálogo |

Estos modelos viven fuera de `notas` y no participan en la matriz de relaciones de `notas.domain.models`.

La regla operacional no cambia:

```text
Meals/DailyPlans/Programs/Proposals/Comparators/Solver/MCP -> notas.Food
Food Catalog master models -> solo curaduría/publicación interna
```

Desde Patch 35 existe un protocolo interno de snapshot hacia `notas.Food`, ubicado en `notas/application/services/food_catalog_snapshots.py`. Es el único puente permitido desde `notas.application` hacia `food_catalog` y su salida operacional es siempre `notas.Food`.

## Estado Patch 38

La frontera MCP queda endurecida alrededor de alimentos operativos.

Aunque el nombre histórico `list_food_catalog` sigue existiendo en MCP/API, la lectura pasa por `notas.Food` y debe devolver solo `food_id` operacional. Identificadores del catálogo maestro, como trazas de snapshot, no forman parte del contrato MCP.

```text
MCP / AI planning -> notas.Food.id
MCP / AI planning -X-> food_catalog.CatalogFood.id
```

## Estado Patch 39

Se agrega un bridge interno para backfill desde alimentos operativos confiables hacia Food Catalog:

```text
notas.Food global/verificado/activo
    -> notas/application/services/commands/food_catalog_backfill.py
    -> food_catalog.CatalogFood candidato maestro
```

Este bridge vive en `notas` porque lee modelos operativos. `food_catalog` sigue sin importar `notas`. El comando no modifica `notas.Food`, no publica automáticamente `CatalogFood` y no altera la disponibilidad MCP.

## Fronteras actuales

| Frontera | Modelos | Responsabilidad |
|---|---|---|
| Identity & User State | `Plan`, `Profile`, `Subscription`, `WeightLog` | Perfil, suscripción y estado personal del usuario. |
| Auth Integration | `MCPUserToken`, `OAuthClient`, `OAuthAuthorizationCode` | Estado de integración externa, tokens MCP y OAuth. |
| Operational Food Snapshot | `Food`, `FoodSourceMetadata`, `FoodPortion`, `FoodAlias`, `FoodLocalizedName`, `FoodImportBatch` | Modelos actuales de alimento operativo y metadata alimentaria dentro de `notas`; deben evolucionar hacia snapshots operativos alimentados por Food Catalog App. |
| Meals | `Meal`, `MealFood`, `MealAccess` | Meals reutilizables, composición meal-food y metadata de acceso de meals. |
| Daily Plans | `DailyPlan`, `DailyPlanMeal` | Planes diarios y comidas adjuntas. |
| Programs | `Program`, `ProgramDay` | Programas semanales y días copiados desde DailyPlans. |
| AI Proposals / Chat Assistant | `AiNutritionChat`, `NutritionProposal`, `NutritionProposalAuditEvent` | Chat IA, AI Assistant sobre chat existente, propuestas revisables y auditoría. |
| Sharing | `DailyPlanShare`, `ProgramShare`, `MealShare`, `FoodShare`, `DailyPlanMealShare` | Registros de Inbox/share entre usuarios. |
| Comparisons | `SavedComparison` | Comparaciones guardadas y snapshots. |

## Matriz de relaciones permitidas

| Frontera origen | Puede referenciar modelos de | Motivo |
|---|---|---|
| Identity & User State | — | Estado base de usuario, sin dependencia a features. |
| Auth Integration | — | Tokens/códigos externos aislados de features. |
| Operational Food Snapshot | — | Los alimentos operativos son fundacionales para Meals/DailyPlans; la app Food Catalog debe alimentarlos mediante protocolos internos, no reemplazarlos directamente. |
| Meals | Operational Food Snapshot, Daily Plans | Meals componen `notas.Food` y mantienen vínculos legacy/auxiliares con planes diarios. |
| Daily Plans | Meals | Los planes diarios adjuntan meals. |
| Programs | Daily Plans | Los programas guardan días copiados desde DailyPlans. |
| AI Proposals | Daily Plans | Las propuestas pueden referenciar el DailyPlan aplicado/generado. |
| Sharing | Operational Food Snapshot, Meals, Daily Plans, Programs | Los share records apuntan a la entidad compartida. |
| Comparisons | — | Persisten payloads autocontenidos, no relaciones ORM a entidades comparadas. |

Esta matriz está declarada como `DOMAIN_MODEL_DEPENDENCY_POLICIES`. Si un modelo
nuevo crea una relación hacia otra frontera sin actualizar esta política, el test
falla.

## Decisión Food Catalog híbrido

La frontera actual `Food Catalog` dentro de `notas.domain.models` no debe interpretarse como el destino final de Food Catalog App.

Decisión vigente:

```text
food_catalog.CatalogFood = fuente maestra/canónica, versionada y trazable
notas.Food = única verdad nutricional operacional usada por Meals, DailyPlans, Programs, Proposals, Comparators, Solver y MCP
```

Por lo tanto, la futura extracción de Food Catalog debe hacerse como app/sistema maestro que alimenta a `notas.Food`, no como movimiento directo e inmediato del modelo operativo `Food` fuera de `notas`.

Meals, DailyPlans, Programs, Proposals, Comparators, Solver y MCP deben seguir dependiendo de `notas.Food` para preservar estabilidad histórica. Si un alimento operativo se origina desde Food Catalog, debe conservar una referencia trazable opcional y sus valores nutricionales como snapshot.

MCP no debe importar ni consultar `food_catalog`. Herramientas con nombres históricos como `list_food_catalog` deben entenderse como lectura de alimentos operativos disponibles desde `notas.Food`.

Desde Patch 33, `food_catalog/application/contracts.py` puede describir candidatos y snapshots internos. Desde Patch 34, `food_catalog.models` persiste alimentos maestros y evidencia. Desde Patch 35, `notas/application/services/food_catalog_snapshots.py` materializa snapshots publicados hacia `notas.Food`. Desde Patch 37, `food_catalog/infrastructure/imports/` y los comandos `dry_run_catalog_usda_foods_json` / `import_catalog_usda_foods_json` permiten importar candidatos maestros sin escribir `notas.Food`. Desde Patch 39, `notas/application/services/commands/food_catalog_backfill.py` permite sembrar Food Catalog desde `notas.Food` globales/verificados/activos, sin modificar la verdad operacional. Ninguno de estos elementos es herramienta MCP, y `CatalogFood` sigue sin ser modelo operativo.

Ver también:

- `docs/decisions/0009-food-catalog-hybrid-source-snapshot.md`
- `docs/decisions/0010-mcp-operational-food-boundary.md`
- `docs/current/features/food_catalog/food_catalog_app.md`

## Patch 41 · AI Assistant sobre chat existente

La próxima etapa de IA no debe crear una UI paralela. Debe evolucionar la frontera actual `AI Proposals / Chat Assistant`:

```text
AiNutritionChat
NutritionProposal
NutritionProposalAuditEvent
```

El LLM externo, cuando se integre, debe vivir detrás de una capa de orquestación y tools controladas. No debe crear relaciones ORM directas hacia Food Catalog ni saltarse el patrón proposal-first.

Reglas de frontera:

```text
AI Assistant -> usa chat existente
AI Assistant -> puede crear/mostrar NutritionProposal mediante servicios de aplicación
AI Assistant -X-> food_catalog
AI Assistant -X-> writes directos a Meal/DailyPlan/Program
AI Assistant -X-> aplicación sin aprobación humana
```

Las tools alimentarias expuestas al AI Assistant deben operar con `notas.Food.id`, igual que MCP.


## Patch 42 · app `ai_assistant` y ChatEngine

Se crea la app Django independiente `ai_assistant` como frontera de orquestación IA. Esta app no mueve modelos desde `notas` y no introduce modelos propios en esta etapa.

Responsabilidad:

```text
ai_assistant = contratos conversacionales, futuros providers LLM, prompts, tools permitidas, safety y audit
```

No responsabilidad:

```text
ai_assistant -X-> Food/Meal/DailyPlan/Program
ai_assistant -X-> food_catalog
ai_assistant -X-> persistencia del chat actual mientras AiNutritionChat siga en notas
```

El chat actual queda desacoplado mediante:

```text
ai_assistant.application.chat_engines.ChatEngine
notas.application.ai_intake.chat_engine.DeterministicNutritionIntakeChatEngine
```

Así, el flujo existente sigue funcionando, pero la view ya no necesita conocer directamente el motor interno de parsing/intake.

## Regla operativa

- Mantener `from notas.domain.models import ...` como contrato compatible.
- Antes de crear un modelo nuevo, asignarlo a una frontera en
  `DOMAIN_MODEL_BOUNDARIES`.
- Si una frontera se mueve a un módulo físico, declararla en
  `DOMAIN_MODEL_MODULE_BY_BOUNDARY_SLUG`.
- Si un modelo nuevo necesita una `ForeignKey`, `OneToOneField` o
  `ManyToManyField` hacia otra frontera, declarar la dependencia y documentar el
  motivo.
- Preferir payloads/snapshots autocontenidos cuando una relación ORM crearía un
  acoplamiento innecesario entre fronteras.

## Próxima etapa sugerida

La modularización física puede continuar de forma incremental:

1. introducir modelos maestros en la app `food_catalog` sin mover `notas.Food`;
2. migrar importadores/curaduría hacia `food_catalog`;
3. mover `meals` y `dailyplans` en patches separados o consecutivos si los tests
   de relación permanecen estables;
4. dejar `programs` para el final del split de modelos centrales, porque depende
   de DailyPlans y está muy conectado con UI/cache/gráficos.

## Food Catalog import adapters

Desde Patch 36, los adaptadores puros de importación pertenecen a:

```text
food_catalog/application/imports/
```

Estos módulos pueden leer y transformar fuentes externas, pero no son fuente operacional para Meals, DailyPlans, Programs, Proposals, Solver ni MCP. `notas` conserva wrappers temporales para rutas históricas de importación; esos wrappers son una excepción explícita de migración y no habilitan acceso directo desde MCP a `food_catalog`.

La persistencia catalog-first de Patch 37 vive en `food_catalog/infrastructure/imports/`, fuera de los contratos puros. Puede usar `food_catalog.models`, pero no puede importar `notas` ni MCP.

El backfill operacional de Patch 39 es la excepción inversa y vive en `notas`: puede leer `notas.Food` y escribir candidatos de catálogo, pero no puede hacer que `CatalogFood` sea leído por MCP ni por los flujos operativos.


## Patch 40 · cierre Food Catalog

La frontera Food Catalog / Notas queda estabilizada al cierre del ciclo Patch 32-40:

```text
food_catalog.CatalogFood -> catálogo maestro
notas.Food -> snapshot operacional
MCP -> solo notas.Food
```

Las entidades operacionales de `notas` no deben crear relaciones directas hacia `CatalogFood`. Los campos de traza en `notas.Food` son metadata primitiva para auditoría y sincronización controlada, no una dependencia operacional.

La app `food_catalog` tampoco debe importar `notas`. Los bridges que necesiten leer `notas.Food` viven en `notas`, como el backfill operacional.
