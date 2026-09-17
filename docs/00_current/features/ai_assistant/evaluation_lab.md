# Laboratorio interno de evaluación del asistente AI

Estado: activo  
Versión: `ai_assistant.evaluation_lab.v1`

## Propósito

El laboratorio permite evaluar el asistente sin depender de la interfaz web y
sin interpretar una conversación a simple vista. Usa el mismo runtime, las
mismas tools y las mismas proyecciones que producción, pero separa explícitamente
las causas posibles de un mal resultado:

- comprensión del lenguaje y conservación del contexto;
- selección o ejecución de tools;
- datos realmente disponibles en las bibliotecas;
- candidatos habilitados para el solver;
- inviabilidad o baja calidad del solver;
- guardrails y fronteras de aprobación;
- grounding de la respuesta visible;
- transporte del proveedor y observabilidad;
- mutaciones inesperadas de entidades finales.

No entrega una nota única que pueda ocultar una regresión grave. El resultado es
un gate por escenario y un diagnóstico agrupado por capa responsable.

## Dos fases

### 1. Preflight determinista

Es el modo por defecto. No llama al proveedor ni consume créditos. Para el usuario
seleccionado:

- calcula los totales desde las mismas proyecciones de biblioteca que usa la web;
- cuenta alimentos activos, visibles y habilitados para el solver;
- ejecuta una prueba pura del solver para una comida de 450 kcal con 30/50/20;
- resuelve entidades reales para el caso de reemplazo de alimento;
- determina qué escenarios están listos y cuáles están bloqueados por fixture o datos.

```bash
python manage.py evaluate_ai_assistant_lab \
  --user-email usuario@example.com
```

### 2. Evaluación live sin UI

`--live` ejecuta las conversaciones con el proveedor configurado. Consume uso y,
si corresponde, créditos. Sólo ejecuta escenarios cuyo preflight está listo.

```bash
python manage.py evaluate_ai_assistant_lab \
  --live \
  --user-email usuario@example.com \
  --output var/ai-evaluation/latest.json \
  --fail-on-regression
```

Por defecto se eliminan al final únicamente las `NutritionProposal` pendientes y
las `AIPreparedAction` no confirmadas que fueron creadas por esa ejecución. Nunca
se eliminan ni restauran automáticamente alimentos, comidas, planes o programas.
Puede usarse `--keep-artifacts` cuando se necesite revisar las cards manualmente.

## Escenarios iniciales

| Escenario | Catálogo vivo | Verdad esperada | Frontera de escritura |
| --- | --- | --- | --- |
| `bibliotecas_coherentes` | F-01, M-01, DP-01, PG-01 | Totales de proyecciones canónicas | Sólo lectura |
| `comida_450_kcal` | M-04, A-03 | Solver ejecutable con alimentos operacionales reales | Sólo propuesta revisable |
| `reemplazo_alimento_200g` | M-08 | Meal, alimento origen, reemplazo y 200 g resueltos desde BBDD | Sólo patch preparado |
| `plan_2400_distribucion_30_50_20` | DP-13 | 2400 kcal y macros 30/50/20, sin sustituir la solicitud | Sólo propuesta revisable |

Para listar los escenarios sin acceder a un usuario:

```bash
python manage.py evaluate_ai_assistant_lab --list-scenarios
```

También se puede repetir `--scenario` para ejecutar un subconjunto.

## Lectura del reporte

El JSON conserva cuatro niveles de evidencia:

1. `ground_truth`: verdad calculada directamente desde BBDD y solver;
2. `scenario_preflight`: readiness y bloqueos antes de consultar al modelo;
3. `live_validation`: transcript, tools, estados y checks del proveedor real;
4. `diagnostics.by_domain`: clasificación de fallos por capa probable.

Cada escenario registra conteos antes y después. Un escenario de lectura no puede
crear artifacts; uno de propuesta debe crear al menos una propuesta sin alterar
las bibliotecas; uno de patch debe crear una acción preparada sin aplicarla.

## Método de iteración sobre el catálogo vivo

Cuando aparezca una incidencia:

1. se vincula el escenario al ID del catálogo vivo;
2. se incorpora una verdad esperada calculable, no escrita a mano cuando exista
   una fuente canónica;
3. se declara qué fixture necesita y qué mutación está permitida;
4. se reproduce primero en preflight y luego live;
5. se corrige la capa diagnosticada;
6. se agrega una regresión determinista al gate local;
7. sólo entonces se repite el ensayo live en staging.

El gate local incluye los contratos del laboratorio:

```bash
scripts/ci_ai_assistant_capability_catalog.sh
```

La revisión humana sigue siendo obligatoria para naturalidad, utilidad de la
explicación y calidad visual de las cards. El laboratorio automatiza coherencia,
grounding, routing, seguridad y estado; no pretende convertir UX en una cifra.
