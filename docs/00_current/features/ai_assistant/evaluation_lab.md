# Laboratorio interno de evaluación del asistente AI

Estado: activo  
Versión: `ai_assistant.evaluation_lab.v2`

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
un gate por escenario y un diagnóstico agrupado por capa responsable. Un pase
técnico tampoco equivale a calidad aprobada: utilidad, naturalidad, claridad y
siguiente paso requieren una anotación humana explícita.

## Capas de evidencia de v2

Lab v2 combina capas distintas sin confundir su alcance:

1. `task_dataset`: 64 casos versionados, ocho por familia, para objetivo,
   outcome y disponibilidad de capacidad;
2. `scenario_preflight`: datos reales, proyecciones canónicas y factibilidad del
   solver para el usuario seleccionado;
3. `live_validations`: doce trayectorias completas, repetibles entre 1 y 10 veces;
4. `quality_evaluation`: checks automáticos por dimensión y revisión humana
   obligatoria por trayectoria;
5. `product_feedback`: señal agregada de respuestas útiles/no útiles del usuario,
   sin incluir contenido ni comentarios en el reporte.

Los 64 casos son un gate determinista de routing, no un sustituto de las doce
conversaciones reales. Las pruebas live validan selección/argumentos de tools,
grounding, continuidad, límites de aprobación y resultado observable.

## Tres fases

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
por defecto, registra tokens y costo del proveedor sin consumir la cuota personal
del usuario seleccionado. Sólo ejecuta escenarios cuyo preflight está listo.

```bash
python manage.py evaluate_ai_assistant_lab \
  --live \
  --user-email usuario@example.com \
  --repetitions 3 \
  --output var/ai-evaluation/latest.json \
  --annotation-template-output var/ai-evaluation/review.json \
  --fail-on-regression
```

### 3. Calibración humana

Una ejecución live técnicamente sana termina en `awaiting_quality_review` hasta
que cada trayectoria tenga `pass` o `fail` en los cuatro criterios. El template
se completa y se reutiliza así:

```bash
python manage.py evaluate_ai_assistant_lab \
  --live \
  --user-email usuario@example.com \
  --repetitions 3 \
  --quality-annotations var/ai-evaluation/review.json \
  --output var/ai-evaluation/final.json \
  --fail-on-regression
```

Un candidato de modelo sólo puede aceptarse si todas sus repeticiones pasan los
checks duros, los checks de calidad automáticos y la revisión humana. Luna es el
baseline, Terra el escalamiento y Sol el benchmark opcional; Astra no forma parte
de esta matriz.

Para probar específicamente la integración comercial de créditos se debe optar
de forma explícita por `--charge-user-credits`. Un bloqueo de cuota se informa
como `blocked_by_credit_quota`; las tools o propuestas que no llegaron a
ejecutarse por ese bloqueo no se reportan como regresiones falsas.

Por defecto se eliminan al final únicamente las `NutritionProposal` pendientes y
las `AIPreparedAction` no confirmadas que fueron creadas por esa ejecución. Nunca
se eliminan ni restauran automáticamente alimentos, comidas, planes o programas.
Puede usarse `--keep-artifacts` cuando se necesite revisar las cards manualmente.

## Escenarios live

| Grupo | Escenarios | Outcome esperado | Frontera de escritura |
| --- | --- | --- | --- |
| Conversación | saludo, tema externo, capacidades y referencia ambigua | `response_only` o `clarification_required` | Sin artifacts inesperados |
| Memoria y continuidad | ficha conocida, datos agrupados/cards y cambio de dirección | `workspace_advanced` | Drafts temporales tipados |
| Recuperación | error de tool y recuperación | `response_only` | Sin falsa confirmación |
| Consultas | bibliotecas coherentes | `workspace_query` | Sólo lectura |
| Nutrición | comida 450 kcal y plan 2400 con 30/50/20 | `nutrition_proposal` | Sólo propuesta revisable |
| Cambio de producto | reemplazo de alimento a 200 g | `prepared_patch` | Patch preparado, nunca aplicado |

Para listar los escenarios sin acceder a un usuario:

```bash
python manage.py evaluate_ai_assistant_lab --list-scenarios
```

También se puede repetir `--scenario` para ejecutar un subconjunto.

## Lectura del reporte

El JSON conserva siete niveles de evidencia:

1. `task_dataset`: cobertura determinista y fallos de surface/routing;
2. `ground_truth`: verdad calculada directamente desde BBDD y solver;
3. `scenario_preflight`: readiness y bloqueos antes de consultar al modelo;
4. `live_validations`: transcripts, tools, estados y checks por repetición;
5. `quality_evaluation`: dimensiones automáticas, anotaciones y confiabilidad;
6. `product_feedback`: señal agregada de los últimos 30 días;
7. `diagnostics.by_domain`: clasificación de fallos por capa probable.

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

La revisión humana sigue siendo obligatoria para naturalidad, utilidad, claridad,
siguiente paso y calidad visual de las cards. Su ausencia produce estado pendiente,
nunca un pase implícito. El laboratorio automatiza coherencia, grounding, routing,
seguridad, outcome y estado; no pretende convertir UX en una cifra única.

## Feedback de producto

Cada respuesta textual del asistente expone controles de útil/no útil. El registro
queda ligado al propietario, chat e índice de mensaje, y puede corregirse sin crear
duplicados. La respuesta se referencia con un fingerprint; el reporte agregado no
exporta mensajes ni comentarios.

```bash
python manage.py report_ai_assistant_feedback --days 30
```

## Validación real histórica de v1 en staging — 18 de septiembre de 2026

La primera iteración completa del laboratorio se cerró contra el servicio Render
`srv-d964dm28qa3s738apvn0`, con el commit `df9fe47` activo mediante el deploy
`dep-damaeu3m8hqs73d3s6t0`.

### Ensayo focalizado

El job `job-damag26k1f9s73erd83g` ejecutó los escenarios de solver y plan diario.
Ambos pasaron:

- el solver trabajó sobre 30 candidatos elegibles y creó una propuesta óptima de
  448,54 kcal: carne magra cocida 120 g y plátano 240 g, con 33,94 g de proteína,
  54,82 g de carbohidratos y 10,39 g de grasa; la peor desviación fue 3,92%;
- el plan ejecutó `update_profile_draft`, `update_proposal_preferences` y
  `create_nutrition_engine_dailyplan_proposal_from_drafts`, conservando 2400 kcal
  y 30/50/20 como fuente de verdad;
- el proveedor consumió 29.521 tokens, con costo estimado de USD 0,020140 y cero
  créditos cargados al usuario;
- la limpieza eliminó las tres propuestas temporales y no dejó acciones preparadas.

### Matriz completa

El job `job-damahsou01pc73eut2ng` pasó los cuatro escenarios:

- bibliotecas canónicas: 13 alimentos, 32 comidas, 4 planes diarios y 2 programas;
- comida de 450 kcal: propuesta óptima de 449,88 kcal usando arroz blanco cocido,
  carne magra cocida y arándanos;
- reemplazo determinista: patch revisable para sustituir Papa por Jamón y fijar
  la porción en 200 g, sin aplicar el cambio;
- plan diario: propuesta revisable de 2400 kcal, 4 comidas y 30/50/20, sin aplicar.

La matriz completa consumió 59.626 tokens, con costo estimado de USD 0,034175 y
cero créditos del usuario. La limpieza eliminó tres `NutritionProposal` y una
`AIPreparedAction`; las bibliotecas finales no cambiaron.

### Defectos que el laboratorio hizo observables

La secuencia de ensayos detectó y permitió corregir fallos que una prueba visual
aislada no separaba con claridad: cobro de créditos en evaluaciones, vocabulario
de referencias del patch, pérdida de drafts entre llamadas, incoherencia entre
porcentajes y gramos, límite de contexto en el follow-up, tools fallidas contadas
como exitosas, confusión entre tamaño de página y total de biblioteca, búsquedas
libres que dejaban al solver sin candidatos y respuestas que declaraban una
propuesta sin haber ejecutado su creación.

Queda como revisión cualitativa pendiente evitar que el texto atribuya una meta
como «mantenimiento» cuando el usuario sólo entregó calorías y macros explícitos.
Ese rótulo no alteró los targets ni el resultado del motor, pero no debe tratarse
como un hecho declarado por el usuario.
