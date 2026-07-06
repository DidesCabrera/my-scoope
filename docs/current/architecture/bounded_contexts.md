# Bounded Contexts

## Objetivo

My Scoope sigue siendo un monolito Django modular. Los bounded contexts no son
apps Django separadas todavía: son fronteras explícitas de responsabilidad dentro
de `notas/application/` para que el sistema pueda crecer sin ambigüedad.

La fuente ejecutable de esta clasificación está en:

- `notas/application/bounded_contexts.py`

Los tests verifican que los paquetes públicos de `notas/application/` estén
asignados a un contexto y que las dependencias entre contextos respeten la
matriz declarada.

## Contextos actuales

| Contexto | Paquetes | Responsabilidad |
|---|---|---|
| Shared Kernel | `dto`, `resolvers`, `validation` | DTOs, validadores y resolvers pequeños compartidos entre varios contextos. Debe mantenerse liviano. |
| Read Models | `queries` | Lecturas optimizadas, querysets, proyecciones y helpers de performance/prefetch. |
| Domain Services | `services`, `use_cases` | Commands, integraciones, cache builders, access helpers, imports y operaciones de servicio. |
| Nutrition Engine | `nutrition_engine` | Núcleo determinístico del motor: targets, templates, solver de porciones, selección de candidatos y validación estricta. |
| AI Nutrition Flow | `ai_intake` | Brief conversacional, historial, generación de propuestas e iteraciones sobre el motor. |
| AI Integration | `ai_tools` | Contratos internos expuestos a API/MCP. Orquesta tools seguras sin ser dueño de reglas del motor. |
| Proposal Review | `proposals` | Contratos, validadores y aplicadores del flujo revisar/aprobar/aplicar. |

## Matriz de dependencias permitidas

| Contexto origen | Puede depender de | Motivo |
|---|---|---|
| Shared Kernel | — | Contratos compartidos livianos, sin dependencia hacia features. |
| Read Models | Shared Kernel, Domain Services | DTOs/validadores y helpers existentes de nutrición/food para construir lecturas. No debe depender de chat IA, motor nutricional ni tools MCP/API. |
| Domain Services | Shared Kernel, Read Models, Proposal Review | Comandos y servicios coordinan contratos, lecturas y aplicadores de propuestas. |
| Nutrition Engine | — | El núcleo del motor debe mantenerse determinístico y sin acoplamiento a Django reads, services, proposals, chat IA ni API/MCP. |
| AI Nutrition Flow | Shared Kernel, Read Models, Domain Services, Nutrition Engine | El flujo conversacional puede leer contexto, reutilizar services y llamar al motor. El motor no debe importar el flujo de vuelta. |
| AI Integration | Shared Kernel, Read Models, Domain Services, AI Nutrition Flow | El adapter application de API/MCP orquesta entrypoints seguros hacia lecturas, comandos y casos de uso IA, pero no importa internals del motor directamente. |
| Proposal Review | Shared Kernel, Domain Services | Reutiliza payload contracts y comandos de creación sin depender del chat ni de tools IA/MCP. |

Esta matriz está declarada como `APPLICATION_CONTEXT_DEPENDENCY_POLICIES`. Si una
nueva importación cruza contextos fuera de esta política, los tests fallan.

## Reglas operativas

- `shared_kernel` no debe depender de contextos de feature como IA, propuestas o services.
- `read_models` no debe depender de `ai_intake`, `nutrition_engine` ni `ai_tools`.
- `nutrition_engine` es un bounded context propio: no debe importar `ai_tools`, `ai_intake`, `proposals`, `queries` ni `services`.
- `ai_intake` es el flujo conversacional: puede importar el motor, pero el motor no puede importar el flujo de vuelta.
- `ai_tools` no debe importar el motor directamente; debe entrar por casos de uso de `ai_intake` o contratos application estables.
- `proposals` no debe depender de `ai_tools` ni del flujo conversacional de `ai_intake`.
- Los adapters HTTP/MCP siguen fuera de application: `interface` y `mcp_server` son bordes, no contextos de negocio.

## Contratos compartidos

Cuando un helper debe ser usado por varios contextos, preferir ubicarlo en un
paquete compartido liviano antes que hacer depender un contexto de otro.

Ejemplo aplicado:

- La normalización de trazabilidad de iteraciones de propuestas vive ahora en
  `notas/application/dto/proposal_iteration_trace.py`.
- `queries`, `ai_tools`, `presentation` y `ai_intake` pueden usar ese contrato sin
  acoplarse al bounded context del chat nutricional.


## Áreas internas de Domain Services

`domain_services` sigue siendo un bounded context de application, pero ya no debe operar como un cajón ambiguo. Sus entradas directas bajo `notas/application/services/` se declaran como áreas internas en `APPLICATION_SERVICE_AREAS`.

| Área | Entradas | Responsabilidad |
|---|---|---|
| Access | `access` | Helpers de ownership/capabilities usados por bordes y application. |
| Cache Builders | `cache` | Proyecciones derivadas y summaries cacheados. |
| Entity Commands | `commands` | Operaciones write-side de foods, meals, daily plans, programs, sharing y proposals. |
| Comparisons | `comparisons` | Payloads, snapshots y helpers de comparaciones guardadas. |
| Food Catalog Services | `food_imports` | Normalización/importación legacy dentro de `notas`; debe evolucionar hacia Food Catalog App como fuente maestra que alimenta snapshots operativos `notas.Food`. |
| Notifications | `notifications` | Builders de contenido saliente. |
| Nutrition Services | `nutrition` | Agregación nutricional, totales, KPIs y helpers de peso. |
| Auth Integration | `mcp_user_tokens`, `oauth_authorization_codes` | Servicios de tokens MCP y códigos OAuth. |

### Matriz interna de services

| Área origen | Puede depender de | Motivo |
|---|---|---|
| Access | — | Puede consultar read models, pero no coordina otras áreas de service. |
| Cache Builders | Food Catalog | Reutiliza normalización de nombres/display de alimentos. |
| Entity Commands | Cache Builders, Comparisons, Food Catalog, Nutrition Services | Coordina servicios de menor nivel como entrypoint de escritura. |
| Comparisons | — | Mantiene helpers de comparación autocontenidos. |
| Food Catalog Services | — | Área base de importación/normalización legacy; no debe hacer depender Meals/DailyPlans directamente de fuentes externas. |
| Notifications | — | No coordina reglas de negocio ni commands. |
| Nutrition Services | Food Catalog | Agregaciones nutricionales reutilizan normalización de alimentos. |
| Auth Integration | — | OAuth/MCP token services se mantienen aislados de features. |

Esta matriz está declarada como `APPLICATION_SERVICE_AREA_DEPENDENCY_POLICIES`. Si aparece una importación nueva entre áreas no permitidas, los tests fallan.

## Cómo agregar un contexto o paquete

1. Crear o mover el paquete en `notas/application/`.
2. Asignarlo en `APPLICATION_BOUNDED_CONTEXTS`.
3. Declarar su política de dependencias en `APPLICATION_CONTEXT_DEPENDENCY_POLICIES`.
4. Agregar la regla de dependencia mínima que corresponda en los tests.
5. Si el paquete nuevo vive bajo `services`, asignar también su área en `APPLICATION_SERVICE_AREAS` y declarar su política en `APPLICATION_SERVICE_AREA_DEPENDENCY_POLICIES`.
6. Documentar la responsabilidad en este archivo.

Si una dependencia nueva parece necesaria, preferir un contrato compartido pequeño
en `shared_kernel` antes que importar un feature context desde otro feature
context.
