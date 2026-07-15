# Testing Strategy

## Objetivo

Los tests deben proteger los contratos que más se rompen al crecer el sistema.

## Prioridades

### 1. Services y commands

Agregar tests para:

- payload parsing;
- snapshots;
- add/remove/reorder;
- comandos de guardado;
- comandos de aplicación de propuestas;
- permisos/capabilities.

### 2. Arquitectura

Mantener tests que aseguren:

- `domain` no importa `application`, `presentation` ni `interface`;
- `application` no importa `presentation`;
- `application` no importa `interface`;
- `presentation` no importa `interface`;
- `mcp_server/myscoope_mcp` no importa Django ni módulos internos de `notas` directamente;
- el root URLConf solo agrega módulos en `notas/interface/urls/`;
- los imports HTTP/UI tolerados en `application` y `presentation` no crecen sin decisión explícita.

Los imports HTTP/UI existentes en capas internas se tratan como deuda controlada: si desaparecen, se deben eliminar del allowlist; si aparece uno nuevo, el test debe fallar hasta moverlo a la capa correcta o documentar el bridge.

### Estado Patch 17

El Patch 17 reduce deuda existente en `application` quitando dependencias a `django.shortcuts` desde queries de detalle y tools MCP/API. La regla operativa queda:

- los helpers `get_object_or_404` pertenecen preferentemente a `interface` o a bridges explícitos;
- `application` puede resolver lecturas con querysets y excepciones de modelo, siempre que el adapter traduzca esas excepciones a contratos estables;
- cuando una excepción `ObjectDoesNotExist` cruza hacia `ai_tools`, se mapea como `not_found` sin exponer detalles internos;
- cada reducción de allowlist debe quedar acompañada por tests focalizados para impedir regresiones.

### 3. Regresiones UI lógicas

Cuando un bug se repite, agregar test si puede representarse sin navegador.

Ejemplos:

- eliminar elemento intermedio compacta posiciones;
- modo edición se mantiene tras submit;
- comparación guardada conserva snapshot;
- rutas de comparadores e inbox siguen registradas.

## Uso de ZIPs

Para cambios de arquitectura o tests, usar export `full`.

Para cambios de UI simples, usar export `ai`.

### Estado Patch 18

El Patch 18 inicia el adelgazamiento de views grandes moviendo construcción de viewmodels de propuestas desde `interface/views/proposals.py` hacia módulos explícitos de `presentation/proposals/`.

Regla operativa:

- `interface/views` orquesta request, permisos, mensajes, redirects y render;
- `presentation/proposals/list_page.py` concentra estado visual, acciones y URLs de la lista de propuestas;
- `presentation/proposals/entity_page.py` construye el contrato visual para revisar la entidad propuesta sin acciones propias de la entidad;
- cada extracción debe mantener tests focalizados sobre el contrato presentation para reducir riesgo antes de adelgazar más views.

### Estado Patch 19

El Patch 19 elimina la ambigüedad entre `application/queries/` y `application/services/queries/` moviendo los helpers de lectura/performance a:

- `notas/application/queries/performance/dailyplan_queries.py`
- `notas/application/queries/performance/meal_queries.py`

Regla operativa:

- las lecturas, querysets optimizados y helpers de prefetch viven bajo `notas/application/queries/`;
- `notas/application/services/` se reserva para comandos, integraciones, cache, access, notifications y servicios con comportamiento de negocio;
- `notas/application/services/queries/` no debe recrearse;
- los imports legacy hacia `notas.application.services.queries` quedan bloqueados por tests de arquitectura.

### Estado Patch 20

El Patch 20 centraliza el bridge `get_object_or_404` usado por page builders de `presentation/pages/` en:

- `notas/presentation/pages/object_lookup.py`

Regla operativa:

- los módulos de page builders no deben importar `django.shortcuts` directamente;
- si un page builder necesita resolver un objeto opcional para componer un viewmodel, debe usar el bridge centralizado;
- el allowlist de arquitectura pasa de varias excepciones dispersas a una sola excepción documentada;
- el siguiente paso natural es mover esa responsabilidad completamente hacia `interface` o hacia queries que retornen contratos sin 404 HTTP cuando el flujo permita tocar las views involucradas.

### Estado Patch 21

El Patch 21 adelgaza `notas/interface/views/ai_intake.py` moviendo contratos visuales y composición de cards del chat nutricional hacia:

- `notas/presentation/pages/ai_intake_page.py`

Regla operativa:

- `interface/views/ai_intake.py` debe concentrarse en request, sesión, mensajes, redirects, render y orquestación de casos de uso;
- `presentation/pages/ai_intake_page.py` concentra viewmodels, headers, cards generadas, trazabilidad visible y contratos de lista/detalle del chat;
- los tests de cards generadas deben importar desde `presentation`, no desde helpers privados de la view;
- si una extracción deja una inconsistencia de imports legacy, debe alinearse en el mismo patch antes de validar `manage.py check`.

### Estado Patch 22

El Patch 22 adelgaza `notas/interface/views/dailyplans.py` moviendo la composición de contextos renderizados hacia:

- `notas/presentation/pages/dailyplan_contexts.py`

Regla operativa:

- `interface/views/dailyplans.py` debe concentrarse en request, permisos, formularios, mensajes, redirects y render;
- `presentation/pages/dailyplan_contexts.py` arma los contextos `BaseVM` para listas, detalles, edición, creación y configuración de DailyPlans;
- la navegación contextual de Programas para un DailyPlan se resuelve en presentation junto con la composición del breadcrumb;
- los tests de presentation deben validar los contratos de contexto para que futuras extracciones de views sean seguras.

### Estado Patch 23

El Patch 23 centraliza contratos semánticos de propuestas en:

- `notas/application/proposals/contracts.py`

Regla operativa:

- los intents, labels de estado, aplicabilidad y metadatos visuales base de propuestas no deben reimplementarse en `interface` ni `presentation`;
- `interface/views/proposals.py` puede decidir qué comando ejecutar, pero debe resolver el intent usando el contrato de application;
- `presentation/proposals/proposal_review_viewmodels.py` puede componer UI, pero debe leer capacidades y labels desde el contrato compartido;
- las propuestas generadas por IA/MCP siguen el flujo seguro: crear propuesta revisable, aprobar explícitamente y aplicar solo intents soportados.

### Estado Patch 24

El Patch 24 hace explícitos los bounded contexts de `notas/application/` en:

- `notas/application/bounded_contexts.py`
- `docs/00_current/architecture/bounded_contexts.md`

Regla operativa:

- cada paquete público de `notas/application/` debe pertenecer a un bounded context;
- `shared_kernel` debe mantenerse liviano y no depender de feature contexts;
- `nutrition_engine` debe seguir siendo núcleo independiente del motor, sin importar orquestadores, tools, proposals, queries o services;
- `ai_tools` debe entrar al flujo nutricional por casos de uso de `ai_intake`, no importando internals del motor;
- `proposals` no debe depender del adapter IA/MCP ni del chat nutricional.

Esta etapa no separa apps Django nuevas: primero deja explícita y testeada la propiedad de paquetes para que futuras extracciones sean seguras.


### Estado Patch 25

El Patch 25 convierte la clasificación de bounded contexts en una matriz de
dependencias ejecutable:

- `notas/application/bounded_contexts.py` declara ahora `APPLICATION_CONTEXT_DEPENDENCY_POLICIES`;
- `notas/tests/test_bounded_contexts.py` falla si un contexto importa otro fuera de esa matriz;
- la trazabilidad de iteraciones de propuestas se mueve a `notas/application/dto/proposal_iteration_trace.py` para que `queries` no dependa de `ai_intake`.

Regla operativa:

- los contextos nuevos deben declarar dueño, responsabilidad y dependencias permitidas;
- si un contrato cruza varios contextos, debe vivir en shared kernel antes que crear una dependencia feature → feature;
- `read_models` no debe volver a importar `ai_intake`, `nutrition_engine` ni `ai_tools`.

### Estado Patch 26

El Patch 26 separa el contexto amplio `AI Nutrition` en dos bounded contexts más explícitos:

- `nutrition_engine`: núcleo determinístico del motor nutricional;
- `ai_nutrition_flow`: flujo conversacional, brief, generación de propuestas e iteraciones.

Regla operativa:

- `ai_nutrition_flow` puede depender de `nutrition_engine`;
- `nutrition_engine` no puede depender de `ai_nutrition_flow` ni de otros orquestadores;
- `ai_integration` debe entrar al motor por el flujo/use case de `ai_intake`, no importando `nutrition_engine` directamente;
- `read_models` no puede depender ni del flujo IA ni del motor.

### Estado Patch 27

El Patch 27 hace más explícito el interior del bounded context `domain_services` mediante áreas de servicio declaradas en:

- `notas/application/bounded_contexts.py`

Regla operativa:

- cada entrada directa de `notas/application/services/` con código Python debe pertenecer a un área de servicio;
- las áreas de servicio tienen una matriz de dependencias propia;
- `commands` puede coordinar servicios de menor nivel, pero áreas como `food_catalog`, `comparisons`, `notifications` y `auth_integration` no deben empezar a importar commands;
- carpetas legacy vacías preservadas por ZIP no cuentan como entradas activas, pero cualquier módulo Python nuevo sí debe ser asignado.

### Estado Patch 28

El Patch 28 declara fronteras ejecutables para los modelos del dominio en:

- `notas/domain/model_boundaries.py`
- `docs/00_current/architecture/domain_model_boundaries.md`

Regla operativa:

- `notas/domain/models.py` puede seguir siendo un archivo único por compatibilidad Django, pero cada modelo debe pertenecer a una frontera explícita;
- las relaciones ORM entre fronteras deben estar permitidas por `DOMAIN_MODEL_DEPENDENCY_POLICIES`;
- antes de dividir físicamente `models.py`, los tests deben asegurar que no se pierda propiedad ni se creen dependencias accidentales;
- cualquier modelo nuevo debe agregarse a `DOMAIN_MODEL_BOUNDARIES` en el mismo patch que lo introduce.

### Estado Patch 29

El Patch 29 inicia la modularización física de `notas.domain.models` con grupos de bajo riesgo:

- `notas/domain/model_modules/auth_integration.py`
- `notas/domain/model_modules/comparisons.py`

Regla operativa:

- `notas.domain.models` sigue siendo el contrato público de importación para todos los modelos;
- cualquier frontera movida físicamente debe declararse en `DOMAIN_MODEL_MODULE_BY_BOUNDARY_SLUG`;
- los tests de dominio deben leer tanto el módulo legacy de compatibilidad como los módulos extraídos;
- antes de mover fronteras centrales como `food_catalog`, `meals`, `dailyplans` o `programs`, se debe validar que no se generen migraciones nuevas por el cambio de ubicación física.

### Estado Patch 30

El Patch 30 continúa la modularización física de `notas.domain.models` moviendo
fronteras adicionales de bajo/medio riesgo a módulos propios:

- `notas/domain/model_modules/identity.py`
- `notas/domain/model_modules/sharing.py`

Regla operativa:

- `notas.domain.models` sigue siendo el contrato público de importación;
- cualquier split físico debe actualizar `DOMAIN_MODEL_MODULE_BY_BOUNDARY_SLUG`;
- si un módulo extraído necesita referenciar modelos de otra frontera, debe usar
  referencias ORM diferidas por nombre cuando eso evite imports circulares;
- cada split debe validar `makemigrations --check --dry-run` para confirmar que
  mover clases no genera cambios de esquema.

### Estado Patch 31

El Patch 31 continúa la modularización física de `notas.domain.models` moviendo
la frontera de propuestas IA a:

- `notas/domain/model_modules/proposals.py`

Regla operativa:

- `notas.domain.models` sigue siendo el contrato público de importación para
  `AiNutritionChat`, `NutritionProposal` y `NutritionProposalAuditEvent`;
- las relaciones desde propuestas hacia otros modelos deben usar referencias ORM
  diferidas por nombre si eso evita imports circulares;
- cada frontera movida físicamente debe quedar declarada en
  `DOMAIN_MODEL_MODULE_BY_BOUNDARY_SLUG`;
- el split de propuestas debe validar contratos de proposals, queries, viewmodels
  e intake, porque es una frontera usada por IA, MCP/API y revisión humana.

