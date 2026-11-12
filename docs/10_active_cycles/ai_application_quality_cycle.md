# Ciclo de calidad medible del AI Assistant

Estado: implementación local inicial; evaluación live y revisión humana pendientes
Base: `origin/staging` `d5d31c6045dd216b8d87836124e2a079be71109b`
Autoridad: `docs/00_current/features/ai_assistant/`, registro de tools y servicios de producto

## Resultado buscado

El asistente debe entender solicitudes, seleccionar capacidades autorizadas,
conservar contexto, iterar y comunicar resultados verdaderos. Las propuestas
nutricionales dependen también de los alimentos operacionales y del solver; un
resultado imposible o insuficiente debe producir un diagnóstico útil y ninguna
propuesta ficticia. Suplementos existe como módulo de producto, pero aún no como
capacidad del asistente. Preparaciones evoluciona en paralelo y su contrato AI
debe fijarse después de cerrar el módulo.

## Unidad de evaluación

Cada caso define petición, fixture, outcome observable, efectos permitidos,
efectos prohibidos, capa responsable y revisión humana. Los resultados se reportan
por escenario y repetición. No se promedian fallos de autorización, grounding o
aprobación con respuestas buenas de otras tareas.

| Capa | Evidencia y fallo atribuible |
| --- | --- |
| Comprensión y conversación | Objetivo, referencias, hechos capturados, continuidad, iteración y parada; fallo del asistente si el producto tenía una capacidad suficiente. |
| Tools y aplicación | Selección, argumentos, ownership, resultado y efectos permitidos; fallo de contrato o ejecución si la tool no cumple. |
| Catálogo operacional | Visibilidad, vigencia, datos nutricionales y elegibilidad; insuficiencia de datos cuando no hay candidatos adecuados. |
| Solver | Factibilidad, restricciones, desviación y calidad calculada; fallo o limitación del solver cuando los insumos eran válidos. |
| Proveedor | Transporte, seguimiento post-tool, latencia, tokens, costo y degradación. |
| Presentación | Texto y cards fieles al estado, claridad, utilidad y siguiente paso. |

Un error del catálogo o solver no exonera al asistente de explicar la limitación
sin inventar resultados. Un error del asistente no se imputa al solver por el solo
hecho de que la solicitud era nutricional.

## Estándar de aceptación

1. **Fronteras duras:** cero accesos ajenos, cambios finales sin aprobación,
   propuestas ficticias, afirmaciones de escritura sin tool exitosa, o mutaciones
   persistentes inesperadas. Toda repetición debe pasar.
2. **Resultado por escenario:** el outcome y las restricciones declaradas pasan
   en cada repetición de los escenarios críticos. Las tareas con datos
   insuficientes pasan sólo si se identifica la causa, se evita la falsa
   propuesta y se ofrece un siguiente paso viable.
3. **Calidad humana:** utilidad, naturalidad, claridad y siguiente paso deben
   recibir `pass` explícito en cada trayectoria. Las cards y la calidad culinaria
   requieren revisión adicional cuando correspondan. Sin revisión: `pending`.
4. **Confiabilidad:** baseline y candidato usan el mismo fixture y tres
   repeticiones iniciales. Una falla dura rechaza el candidato. Reportar tasa
   por escenario e intervalo; no usar una tasa global como puerta de aprobación.
5. **Costo y rendimiento:** medir p50/p95 de latencia, tokens, costo estimado,
   reintentos y degradaciones por outcome. Comparar costo sólo entre candidatos
   que superen los puntos anteriores. Definir presupuesto y límites de corrida
   antes de cualquier llamada pagada.

Los umbrales de latencia y costo para rollout se fijarán desde la línea base
medida, no desde una cifra inventada. Una degradación post-tool en un escenario
crítico bloquea el avance aunque la respuesta parezca aceptable.

## Ejecución por etapas

| Etapa | Entregable verificable | Estado |
| --- | --- | --- |
| 1. Inventario | Catálogo de solicitudes actualizado, incluyendo suplementos y preparaciones, con cobertura honesta. | Implementado localmente; falta integración. |
| 2. Negativos nutricionales | Preflight de escasez y trayectoria que pruebe explicación sin propuesta; ampliar a inviabilidad y calidad insuficiente usando fixtures controlados. | Casos sin candidatos e inviabilidad implementados localmente; calidad insuficiente de propuesta parcial pendiente. |
| 3. Dataset gobernado | Casos con procedencia, permiso, clasificación, outcome y efectos; separar desarrollo, regresiones y holdout reservado. | Metadatos y separación 54/18 implementados localmente en 72 casos; desarrollo es el preflight por defecto y holdout exige selección explícita. El reporte congela versiones y huellas de tools. Faltan fixtures y criterios específicos por caso y un conjunto de regresiones separado. |
| 4. Paridad AI/MCP | Matriz de capacidades expuestas con schema, ownership, entitlement, errores, efectos y outcome de extremo a extremo. | Paridad de nombres, descripciones, schemas y rutas implementada localmente; faltan pruebas de resultado y autorización por capacidad. |
| 5. Suplementos | Lectura owner-scoped y handoff de edición, respetando Pro/flag y la regla de no sumar nutrición de etiqueta. | Lecturas y routing de handoff implementados localmente; faltan trayectorias live, navegación UI específica y revisión humana. |
| 6. Preparaciones | Revisión del contrato final del módulo, luego lectura y handoff de composición con tests sobre versión, porción y permisos. | Dependiente del trabajo paralelo; sin cambios al módulo aquí. |
| 7. Comparación live | Baseline y candidato con fixtures sintéticos o autorizados, tres repeticiones, costo acotado, reporte por capa y revisión humana. | Tope autorizado: USD 2. Pendiente de identificador de cuenta aislada de staging, credencial configurada y revisión humana. |
| 8. Rollout | Cohorte, métricas, alarma, disparador de rollback y evidencia de despliegue. | Pendiente de aprobación de activación. |

## Evidencia inicial de staging (12 de noviembre de 2026)

La cuenta de prueba `myscoope@gmail.com` respondió dos turnos con el modelo
`gpt-5.6-luna`: una consulta contó un alimento, coherente con su biblioteca; una
solicitud de comida de 450 kcal invocó una tool y dejó el chat activo sin
propuesta asociada. La vista previa persistida explicó que sólo estaba disponible
Humillas y que faltaba variedad para una solución suficiente. Ambos eventos de
uso terminaron `completed`; el costo estimado del proveedor fue USD 0,001098 y
USD 0,001672, USD 0,002770 en total. No se ha revisado la trayectoria completa
ni su calidad humana.

El staging evaluado estaba en el commit `3b569223d65da312e4bec3411cb157cf3b92cae9`,
anterior a esta implementación local. Un preflight directo de `comida_450_kcal`
en ese build se canceló tras unos tres minutos sin resultado. La causa probable
es el probe de hasta 250 candidatos del laboratorio: la tool de comida usa 40
por defecto. La corrección local limita el probe a 40 y lo omite para escenarios
que no lo necesitan; debe volver a medirse en staging después de integrar el
commit corregido. El proceso temporal de Render genera costo de cómputo separado
del consumo de OpenAI.

## Siguiente corrida permitida

Ejecutar los tests locales de contratos y el preflight sin proveedor. Para el caso
`comida_sin_candidatos`, usar una cuenta aislada con una minuta propia y cero
alimentos aptos para solver; no reutilizar una cuenta real. El escenario no forma
parte del conjunto por defecto porque exige el fixture opuesto al de propuestas
factibles. `--list-scenarios` lo muestra y `--scenario` lo selecciona. Su evaluación
live consume proveedor. Felipe autorizó un gasto máximo de USD 2; antes de la
corrida faltan el identificador de la cuenta aislada y una credencial configurada
en el entorno. El enlace de gestión de claves no proporciona esa credencial.

Antes de comparar modelos se congelan commit, runtime, prompt, schemas, tools,
fixture, dataset y grader. El holdout se mantiene fuera del contexto enviado al
modelo y separado de ejemplos usados para ajustes. El reporte final declara por
escenario `pass`, `fail`, `pending` o `blocked_by_fixture`, con causa y responsable.
