# Nutrition Solver App Cycle

Status: completed
Date: 2026-07-02
Activated: 2026-07-02
Closed: 2026-07-02

## Estado de implementación

- S1: iniciado y documentado. El primer patch no mueve código; crea el mapa de extracción vigente en `docs/current/architecture/nutrition_solver_extraction_map.md` y registra la decisión en `docs/decisions/0044-nutrition-solver-extraction-start.md`.
- S2: completado. Introduce contratos explícitos de input/result de optimización dentro del engine actual en `notas/application/nutrition_engine/contracts.py`, sin crear todavía la app física.
- S3: completado. Amplía pruebas de escenarios base, warnings, parciales e imposibles y agrega un wrapper contractual `optimize_meal_portions()` que no mueve la app ni cambia el algoritmo.
- S4: completado. Hace explícitos scoring/status y diagnostics mediante `OptimizationScoringConfig`, `OptimizationStatusAssessment`, `assess_optimization_status`, `score_direction`, `issue_counts` y reason codes serializables.
- S5: completado. Crea la app Django física `nutrition_solver` como shell registrado en `INSTALLED_APPS`, con README y tests de import/instalación, sin mover todavía lógica productiva.
- S6: completado. Mueve modelos y contratos puros a `nutrition_solver/domain/models.py` y `nutrition_solver/application/contracts.py`, dejando imports puente en `notas.application.nutrition_engine`.
- S7: completado. Mueve `portion_solver`, `validators` y constantes nutricionales estables a `nutrition_solver`, manteniendo imports puente desde `notas.application.nutrition_engine`.
- S8: completado. Crea el adapter/query `notas.Food -> nutrition_solver.domain.models.SolverFood` en `notas/application/queries/solver_food_candidates.py`, sin exponer Food Catalog ni payloads externos.
- S9: completado. Expone una tool read-only de preview para `ai_assistant` llamada `preview_nutrition_solver_candidates`, basada en el adapter operacional S8 y sin writes ni referencias de catálogo maestro.
- S10: completado. Crea una propuesta revisable `create_meal` generada por `nutrition_solver`, persistida como `NutritionProposal` pendiente de revisión y sin aplicar cambios finales.
- S11: cancelado/diferido por decisión estratégica. No se crea UI directa del solver; el punto de contacto del usuario debe ser `ai_assistant`, que solicita propuestas revisables mediante tools allowlisted.

## Cierre del ciclo

Este ciclo se considera cerrado en S10 + hotfix. La separación alcanzó el objetivo estratégico: `nutrition_solver` existe como motor interno separado, con contratos puros, lógica determinística extraída, adapter seguro desde `notas.Food`, preview controlada para `ai_assistant` y generación de `NutritionProposal` revisables sin aplicar cambios finales.

La UI directa de solver se descarta como requisito de cierre porque expondría una capacidad técnica que debe permanecer detrás del asistente. El usuario conversa con `ai_assistant`; el solver calcula y diagnostica; `notas` conserva la revisión, aprobación y persistencia operativa.

## Contexto

My Scoope ya cuenta con un núcleo determinístico de generación nutricional dentro de:

```text
notas/application/nutrition_engine/
```

Ese bounded context ya concentra piezas relevantes del futuro motor:

- estimación de targets nutricionales;
- templates de comidas por día;
- selección de candidatos alimentarios;
- solver de porciones;
- validadores estrictos;
- modelos de datos puros para macros, alimentos candidatos, porciones resueltas y diagnósticos.

En paralelo, el proyecto ya separó o está separando dominios estratégicos en apps o fronteras más explícitas:

```text
food_catalog      -> catálogo maestro y curaduría alimentaria
ai_assistant      -> conversación, provider LLM, tools, guardrails y propuestas revisables
notas             -> gestión operativa de Foods, Meals, DailyPlans, Programs, Comparators y Proposals
```

Dado este estado, el motor de optimización no debe diseñarse como una función auxiliar de `notas`, ni como lógica generada por el LLM externo. Debe evolucionar como un sistema determinístico, testeable y reutilizable.

## Decisión de planificación

Planificar la separación progresiva de `notas/application/nutrition_engine` hacia una app Django independiente llamada tentativamente:

```text
nutrition_solver
```

La separación no debe ser inmediata ni agresiva. El primer objetivo es conservar el motor actual, estabilizar sus contratos y preparar una extracción segura.

## Tesis del ciclo

El AI Assistant puede interpretar lenguaje natural, pedir aclaraciones y explicar resultados, pero la calidad nutricional de una propuesta debe depender principalmente del solver.

Flujo deseado:

```text
Usuario
  -> AI Assistant interpreta intención y restricciones
  -> nutrition_solver calcula o evalúa la mejor solución posible
  -> Proposal Review conserva la propuesta revisable
  -> Humano aprueba
  -> notas persiste Meal / DailyPlan / Program operativo
```

El LLM no debe inventar porciones finales como fuente de verdad. Puede sugerir intención, contexto y preferencias, pero el resultado nutricional debe pasar por contratos y validación determinística.

## Decisión estratégica de UX

El solver no tendrá, por ahora, una UI directa para usuarios finales. La interacción humana debe ocurrir mediante `ai_assistant` y Proposal Review:

```text
Usuario
  -> AI Assistant interpreta intención
  -> tool allowlisted solicita propuesta al solver
  -> nutrition_solver calcula resultado determinístico
  -> NutritionProposal queda pendiente de revisión
  -> humano aprueba/aplica desde el flujo existente
```

Esta decisión evita duplicar formularios técnicos, mantiene el solver como motor interno y concentra la experiencia de usuario en una interfaz conversacional más natural.

## Alcance vigente de la app

`nutrition_solver` es responsable de:

- targets nutricionales y tolerancias;
- restricciones explícitas;
- candidatos alimentarios operativos;
- selección y combinación de alimentos;
- resolución de porciones;
- scoring de soluciones;
- validación de porciones humanas;
- diagnóstico de diferencias contra targets;
- explicación estructurada de por qué una solución es óptima, aceptable, parcial o imposible;
- evaluación de propuestas generadas por otros flujos;
- contratos reutilizables por AI Assistant, Proposal Review, MCP/tools internos y tests.

`nutrition_solver` no será responsable de:

- persistir `Food`, `Meal`, `DailyPlan` o `Program` finales;
- administrar el catálogo maestro de alimentos;
- importar fuentes externas;
- exponer datos directamente a MCP;
- renderizar UI;
- decidir navegación, breadcrumbs o templates;
- aplicar propuestas aprobadas.

## Relación con apps existentes

### `notas`

`notas` conserva la persistencia operativa:

```text
Food / Meal / DailyPlan / Program / NutritionProposal
```

El solver puede recibir candidatos derivados desde `notas.Food`, pero debe hacerlo mediante adapters o contratos de entrada. No debe depender de vistas, requests, templates ni presentación.

Regla:

```text
notas persiste y presenta.
nutrition_solver calcula y diagnostica.
```

### `food_catalog`

`food_catalog` sigue siendo fuente maestra de alimentos curados, pero los flujos operativos no consumen `CatalogFood` directamente.

Regla vigente a preservar:

```text
food_catalog.CatalogFood publicado
  -> materialización explícita
  -> notas.Food snapshot operativo
  -> nutrition_solver usa candidatos derivados de notas.Food
```

Esto protege la estabilidad histórica de Meals, DailyPlans, Programs y propuestas.

### `ai_assistant`

`ai_assistant` debe usar el solver como herramienta interna controlada, no como reemplazo de sus reglas.

El assistant puede:

- convertir lenguaje natural en targets y restricciones;
- solicitar al solver una propuesta;
- explicar warnings y trade-offs;
- generar una `NutritionProposal` revisable.

El assistant no debe:

- saltarse validaciones del solver;
- confiar en porciones inventadas por el proveedor externo;
- aplicar writes directos sin review/aprobación;
- enviar al proveedor datos innecesarios del solver o del usuario.

### MCP / tools

MCP y tools deben seguir siendo bordes controlados.

El solver puede alimentar futuras tools internas como:

```text
estimate_nutrition_targets
optimize_dailyplan_draft
validate_dailyplan_against_targets
explain_solver_result
```

Pero esas tools deben respetar las reglas ya definidas para `ai_assistant`: allowlist, guardrails, contexto mínimo, propuestas revisables y bloqueo de writes directos.

## Contratos deseados

La app debe tender hacia contratos explícitos, serializables y fáciles de testear.

Ejemplo conceptual:

```text
NutritionTargets
- kcal
- protein_g
- carbs_g
- fat_g
- tolerance_percent

SolverFoodCandidate
- food_id
- name
- role
- kcal_per_100g
- protein_per_100g
- carbs_per_100g
- fat_per_100g
- min_g
- max_g
- step_g
- required

SolverConstraint
- type
- severity
- payload

OptimizationInput
- targets
- meal_slots
- candidate_foods
- constraints
- preferences

OptimizationResult
- status: optimal / acceptable / partial / impossible
- score
- proposed_meals
- totals
- target_diff
- warnings
- diagnostics
- explanation
```

Estos nombres pueden ajustarse durante implementación, pero el principio debe mantenerse: entradas y salidas explícitas, sin depender de estructuras improvisadas del chat o de la UI.

## Pros de separar como app Django

### Claridad de responsabilidad

El solver deja de ser una subpieza escondida en `notas` y pasa a ser un sistema de dominio con misión propia.

### Mejor trabajo con AI developers

La separación permite asignar ciclos acotados:

```text
AI Developer A -> scoring y constraints
AI Developer B -> tests de casos imposibles
AI Developer C -> adapter desde notas.Food
AI Developer D -> tools controladas para ai_assistant
AI Developer E -> Proposal Review y explicación de resultados
```

Cada ciclo puede limitar archivos, tests y contratos, reduciendo modificaciones accidentales.

### Mejor testabilidad

El solver debe tener una batería de tests propia para casos como:

- targets explícitos completos;
- targets parciales estimados;
- alimentos insuficientes;
- exceso de grasa inevitable;
- porciones mínimas/máximas;
- snacks vs comidas principales;
- planes de 1 a 6 comidas;
- resultados imposibles pero explicables;
- estabilidad determinística del mismo input.

### Mejor integración con IA

El LLM puede explicar y conversar, pero el solver entrega un resultado auditable y repetible. Esto mejora confianza del usuario y reduce riesgo de propuestas nutricionales inconsistentes.

### Mejor evolución futura

El solver puede crecer hacia:

- optimización multi-día;
- optimización de Programs;
- variedad semanal;
- adherencia/preferencias;
- costo aproximado;
- restricciones digestivas o de ingredientes;
- plantillas por objetivo;
- comparación de soluciones alternativas;
- modo rápido vs modo avanzado.

## Contras y riesgos

### Sobrearquitectura prematura

Crear una app grande antes de estabilizar contratos podría generar abstracciones innecesarias. La extracción debe ser progresiva.

### Duplicación de cálculos

My Scoope ya calcula macros, KPIs, alloc y PPK en servicios existentes. El solver no debe crear una segunda verdad nutricional incompatible.

Mitigación:

```text
reutilizar constantes y helpers puros existentes,
o extraer contratos compartidos antes de duplicar lógica.
```

### Fricción con `notas`

El solver necesitará alimentos operativos y eventualmente DailyPlans existentes. Si se conecta directamente al ORM en todos lados, perderá independencia.

Mitigación:

```text
adapters explícitos en bordes,
contratos puros en el núcleo,
tests unitarios sin base de datos cuando sea posible.
```

### Complejidad inicial

Nueva app implica documentación, tests, imports, settings y frontera conceptual adicional. Se justifica solo si el ciclo se mantiene simple y orientado a contratos.

## Estrategia de separación progresiva

### Fase 0 — Documentar y proteger el estado actual

Objetivo: dejar explícito que `notas/application/nutrition_engine` es el precursor del futuro `nutrition_solver`.

Tareas sugeridas:

- documentar frontera y objetivo del ciclo;
- identificar módulos actuales del motor;
- listar contratos actuales equivalentes a futuros contratos;
- agregar tests de guardrail si falta protección de dependencias.

### Fase 1 — Estabilizar contratos dentro de `notas`

Objetivo: mejorar el motor sin moverlo aún.

Tareas sugeridas:

- normalizar naming de macros hacia `_g` donde corresponda en contratos nuevos;
- distinguir targets diarios vs targets por comida;
- definir `OptimizationInput` y `OptimizationResult` internos;
- consolidar status de solución;
- agregar tests de scoring/diagnostics.

### Fase 2 — Crear app física mínima

Objetivo: crear `nutrition_solver` sin cambiar comportamiento productivo.

Estructura inicial sugerida:

```text
nutrition_solver/
  __init__.py
  apps.py
  domain/
  services/
  adapters/
  tests/
```

No se requieren modelos Django propios al inicio.

La app puede partir reexportando o moviendo contratos puros de forma controlada, con compatibilidad temporal para imports antiguos.

### Fase 3 — Mover núcleo puro

Objetivo: mover progresivamente lógica sin dependencias Django directas.

Candidatos naturales:

```text
target_estimator.py
meal_templates.py
portion_solver.py
validators.py
candidate_selector.py
models.py
```

Cada movimiento debe incluir:

- imports de compatibilidad temporal si corresponde;
- tests equivalentes antes/después;
- documentación de frontera actualizada.

### Fase 4 — Crear adapters hacia `notas`

Objetivo: separar lectura ORM de cálculo.

Ejemplos:

```text
nutrition_solver/adapters/notas_foods.py
nutrition_solver/adapters/notas_dailyplans.py
```

Los adapters convierten modelos operativos en candidatos puros del solver. El núcleo no importa modelos Django.

### Fase 5 — Integración con AI Assistant y Proposal Review

Objetivo: usar el solver como fuente de propuestas revisables.

Tareas sugeridas:

- tool interna para optimizar draft de DailyPlan;
- tool interna para validar propuesta contra targets;
- generación de `NutritionProposal` con diagnóstico del solver;
- explanation segura para chat;
- no aplicar writes directos.

### Fase 6 — UI operacional

Objetivo: permitir que usuarios soliciten optimización desde flujos existentes.

Posibles entradas:

- desde DailyPlan detail;
- desde creación de DailyPlan;
- desde AI Assistant;
- desde futuro onboarding nutricional;
- desde Program detail cuando exista optimización multi-día.

## Orden sugerido de patches

```text
Patch S1: docs + mapa del nutrition_engine actual
Patch S2: contratos internos OptimizationInput/Result sin mover app — completado
Patch S3: tests de casos base, warnings e imposibles — completado
Patch S4: scoring/status más explícito — completado
Patch S5: crear app nutrition_solver vacía + README + tests de import — completado
Patch S6: mover modelos/contratos puros con compatibilidad — completado
Patch S7: mover portion_solver y validators — completado
Patch S8: adapter notas.Food -> SolverFoodCandidate — completado
Patch S9: tool interna read/preview para ai_assistant — próximo
Patch S10: propuesta revisable generada por solver
Patch S11: UI mínima para solicitar optimización desde DailyPlan
```

El orden puede ajustarse según el avance de Food Catalog y AI Assistant. La regla es no mover piezas productivas hasta que los contratos y tests estén claros.

## Criterios de éxito

El ciclo puede considerarse exitoso cuando:

- existe una app `nutrition_solver` con núcleo puro y tests propios;
- `notas` consume el solver mediante adapters o servicios estables;
- `ai_assistant` puede solicitar validación/optimización sin inventar resultados finales;
- las propuestas del solver incluyen diagnóstico y explicación;
- los casos imposibles devuelven razones útiles en vez de fallar silenciosamente;
- los cálculos nutricionales siguen siendo consistentes con los KPIs operativos;
- los ZIPs/exportaciones pueden aislar el solver para trabajo con AI developers.

## Decisión operativa al cierre

La app `nutrition_solver` ya existe y contiene la capa pura/ejecutable inicial. El trabajo pendiente no es separar más por separar, sino mejorar calidad y explicación manteniendo la frontera actual:

```text
nutrition_solver calcula y diagnostica
ai_assistant interpreta intención y solicita tools
notas adapta ORM, crea NutritionProposal y aplica solo tras revisión
```

Cualquier UI directa del solver queda fuera de este ciclo y requiere una decisión de producto separada.


## Hito S8 — Adapter `notas.Food` -> candidatos puros del solver

S8 crea el adapter operacional en:

```text
notas/application/queries/solver_food_candidates.py
```

La decisión es mantener el adapter del lado de `notas`, porque ahí viven el ORM, permisos de lectura y visibilidad. La app `nutrition_solver` sigue recibiendo dataclasses puras (`SolverFood`) y no importa `notas`, `food_catalog` ni `ai_assistant`.

Regla vigente:

```text
notas.Food solver_enabled + visible + readable
  -> notas.application.queries.solver_food_candidates
  -> nutrition_solver.domain.models.SolverFood
  -> OptimizationInput / optimize_meal_portions
```

En S8 todavía no se conectaba UI, AI Assistant, MCP/tools ni Proposal Review. Ese hito dejó la entrada estable que luego S9/S10 usaron para preview y propuestas revisables desde AI Assistant.

Criterios de aceptación S8:

- listar solo alimentos operacionales `solver_enabled=True`, activos, visibles y legibles por el usuario;
- excluir `Food Catalog` IDs, referencias externas y payloads de snapshots;
- convertir porciones mínimas/máximas/step a `PortionBounds`;
- inferir un rol solver simple cuando el caller no entrega uno explícito;
- mantener `nutrition_solver` libre de imports hacia `notas`, `food_catalog` y `ai_assistant`;
- cubrir la frontera con tests.

## Resultado final del ciclo

Al cierre, el sistema queda con esta frontera vigente:

```text
food_catalog.CatalogFood publicado
  -> notas.Food snapshot operativo
  -> notas adapter/query solver-ready
  -> nutrition_solver optimiza con contratos puros
  -> notas crea NutritionProposal pending_review
  -> AI Assistant explica y solicita revisión/aprobación
```

Afirmaciones de cierre:

- `nutrition_solver` ya existe como app Django separada.
- los modelos/contratos puros viven en `nutrition_solver`;
- el solver de porciones y validadores estrictos viven en `nutrition_solver`;
- `notas` conserva adapters ORM, propuestas revisables y persistencia operativa;
- `ai_assistant` puede previsualizar candidatos y solicitar propuestas;
- el solver no aplica writes finales ni aprueba propuestas;
- el solver no consume Food Catalog directo, IDs de catálogo ni payloads externos;
- la UI directa del solver queda fuera de alcance y diferida por decisión estratégica.

## Ciclos futuros sugeridos

- Mejorar calidad del solver: restricciones, preferencias, variedad, exclusiones, máximos por alimento y scoring.
- Mejorar AI Assistant -> Solver: extracción de intención, aclaraciones, explicación de trade-offs y selección de tool correcta.
- Mejorar Proposal Review: comparación antes/después, warnings visibles, razón de status y diagnósticos por macro.
- Regresar a Food Catalog para aumentar calidad/cobertura de datos, que alimentará indirectamente mejores candidatos solver-ready.
