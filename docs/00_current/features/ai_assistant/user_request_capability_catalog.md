# Catálogo de requerimientos del usuario para el AI Assistant

Status: living baseline
Date: 2026-09-17

## Propósito

Este catálogo describe las solicitudes que una persona puede expresar al asistente en
lenguaje natural y la forma correcta de resolverlas en My Scoope. Su objetivo es:

- medir la cobertura real del asistente respecto de las funciones del producto;
- distinguir consultas, cambios deterministas, decisiones nutricionales y handoffs;
- detectar ambigüedades de alcance antes de modificar una entidad equivocada;
- convertir conversaciones reales fallidas en nuevas filas y regresiones;
- evitar que la cantidad de tools provider-facing sea confundida con capacidad real.

La lista es sistemática, pero deliberadamente extensible. No pretende anticipar cada
frase que una persona pueda escribir. Una petición nueva se incorpora como variante de
una capacidad existente o como una nueva capacidad cuando cambia el resultado de
producto, el alcance, las validaciones o el nivel de aprobación.

## Vocabulario de resolución

| Modo | Uso correcto | Resultado |
| --- | --- | --- |
| Lectura autónoma | Consultar, contar, buscar, explicar o comparar estado autorizado. | Respuesta respaldada por una lectura real. |
| Patch determinista | El usuario define el estado final exacto o una operación acotada. | Vista previa y confirmación confiable; después, commit atómico mediante commands. |
| Propuesta nutricional | La AI o el solver deben escoger alimentos, cantidades, estructura o alternativas. | `NutritionProposal` revisable, normalmente con varias alternativas. |
| Handoff confiable | La operación necesita una superficie especializada, permisos del dispositivo, pagos, importación o sharing. | Navegación a la UI exacta, conservando el contexto. |
| Aclaración | Hay más de un objetivo, entidad o alcance razonable. | Una pregunta breve que resuelve únicamente la ambigüedad bloqueante. |
| No soportado | El producto no tiene un command o flujo seguro que represente el resultado. | Explicación honesta; nunca simular que se realizó el cambio. |

Todo patch y toda propuesta requieren confirmación en la política vigente. Una futura
política de autoaplicación para cambios de bajo riesgo no debe inferirse de este
catálogo.

## Regla principal: determinismo frente a propuesta

Una solicitud es **determinista** cuando la persona ya eligió el qué y el cómo:

> En la comida Almuerzo cambia arroz por papa y deja la papa en 200 g.

Corresponde a un patch que reemplaza el `Food` del `MealFood` y actualiza su cantidad.
No corresponde llamar al solver ni crear una propuesta nutricional.

Una solicitud es **generativa u optimizadora** cuando el sistema debe decidir:

> En Almuerzo reemplaza el arroz por una opción con más fibra y ajusta todo a 450 kcal.

Corresponde a una propuesta nutricional. La AI formula la intención y las restricciones;
el backend y el solver calculan y validan alternativas.

Una petición puede ser mixta. En ese caso el resultado debe conservar como restricciones
los cambios exactos pedidos y proponer solamente las decisiones abiertas.

## Resolución obligatoria de alcance

Antes de operar, el asistente debe resolver estas dimensiones:

1. **Superficie:** biblioteca, borrador, objeto compartido, propuesta, programa plantilla,
   plan fijado o programa calendarizado.
2. **Entidad:** objeto reutilizable o snapshot incorporado en otra entidad.
3. **Cardinalidad:** una coincidencia, varias coincidencias o ninguna.
4. **Propiedad:** propio editable, compartido legible, snapshot histórico o global.
5. **Temporalidad:** plantilla futura, instancia activa, día pasado/presente o día futuro.
6. **Resultado:** valor exacto indicado por el usuario o decisión delegada a AI/solver.
7. **Impacto:** una entidad, varias entidades relacionadas o cambio masivo.

Los IDs nunca se inventan. Los nombres se resuelven contra una proyección canónica y
paginada de la superficie correspondiente.

### Palabras particularmente ambiguas

| Expresión | Posibles significados |
| --- | --- |
| “Porción del alimento” | `default_portion_g` de Food; gramos de un MealFood; gramos dentro del snapshot de un plan; gramos de un día calendarizado. |
| “Comida del plan” | Meal reutilizable de biblioteca o Meal snapshot dentro de DailyPlan. |
| “Programa activo” | `ProgramCalendarization`, no la plantilla `Program` de origen. |
| “Cámbialo en todos” | Biblioteca, copias futuras, snapshots existentes o días futuros de una calendarización. Exige aclaración. |
| “Mi plan” | DailyPlan de biblioteca, plan fijado para hoy, plan dentro de un programa o día calendarizado. |

## Matriz de cobertura

Leyenda de cobertura actual:

- **Cubierta:** existe frontera AI, validación y ejecución coherentes.
- **Parcial:** existe parte del flujo, pero falta alcance, datos, continuidad o calidad.
- **UI:** el producto lo hace; el asistente sólo debe hacer handoff actualmente.
- **Brecha:** falta una capacidad segura de producto o su adapter para AI.

### Ficha y preferencias

| ID | Solicitud o ejemplos | Resolución | Cobertura actual | Observación |
| --- | --- | --- | --- | --- |
| PR-01 | “¿Cuál es mi peso/objetivo/nivel de actividad?” | Lectura | Cubierta | Debe distinguir dato persistido de dato faltante. |
| PR-02 | “Cambia mi peso a 78 kg” | Patch/draft confirmable | Cubierta | Actualiza ficha, no un registro histórico de peso. |
| PR-03 | “Soy vegetariano”, “no quiero lactosa” | Patch/draft confirmable | Cubierta | La preferencia debe quedar tipada cuando afecte seguridad. |
| PR-04 | “Olvida mi preferencia por desayunos dulces” | Patch/draft confirmable | Parcial | Debe soportar eliminación explícita, no sólo agregar texto. |
| PR-05 | “Usa mis preferencias para crear el plan” | Lectura + propuesta | Parcial | Requiere continuidad entre lectura de memoria y generación. |

### Alimentos

| ID | Solicitud o ejemplos | Resolución | Cobertura actual | Observación |
| --- | --- | --- | --- | --- |
| F-01 | Listar, contar, buscar o consultar alimentos de mi biblioteca | Lectura | Cubierta | Usa la proyección canónica de la biblioteca y devuelve total, página, `has_more` y `next_offset`. |
| F-02 | Consultar macros, calorías, porción o procedencia de un alimento | Lectura | Parcial | La respuesta sólo puede afirmar campos realmente disponibles. |
| F-03 | “Crea avena con 13 P, 68 C y 7 G por 100 g” | Patch determinista | Cubierta | Nombre y macros son exactos; requiere confirmación. |
| F-04 | Crear alimento desde foto/etiqueta | Handoff y confirmación especializada | UI | OCR propone valores; el usuario confirma el alimento privado. |
| F-05 | Renombrar un alimento | Patch determinista | Cubierta | Debe detectar homónimos antes de preparar el patch. |
| F-06 | Cambiar proteínas, carbohidratos o grasas | Patch determinista | Cubierta | El backend recalcula energía; la AI no inventa el total final. |
| F-07 | Cambiar porción sugerida, mínimo, máximo o paso | Patch determinista | Brecha | El modelo posee esos campos, pero `food.update` sólo admite nombre y macros. |
| F-08 | Cambiar fibra, azúcar, sodio o grasa saturada | Patch determinista | Brecha | Existen campos operacionales, pero no están en el patch general. |
| F-09 | Desactivar/eliminar un alimento | Patch destructivo | Cubierta parcial | `food.delete` desactiva; la vista previa debe explicar el efecto sobre composiciones existentes. |
| F-10 | Duplicar, ordenar o borrar varios alimentos | Patch masivo o handoff | UI | Requiere commands/adapters de lote antes de exponerlo a AI. |
| F-11 | Compartir o guardar un alimento recibido | Handoff | UI | Sharing e Inbox mantienen validaciones propias. |
| F-12 | Comparar alimentos y cantidades | Lectura/comparación | Parcial | La comparación dinámica/guardada existe, pero no toda está expuesta como capacidad conversacional. |
| F-13 | “Habilita este alimento para el solver” | No soportado para usuario | Brecha intencional | La aptitud del solver depende de una proyección gobernada, no de un booleano elegido sin evidencia. |

### Comidas de biblioteca

| ID | Solicitud o ejemplos | Resolución | Cobertura actual | Observación |
| --- | --- | --- | --- | --- |
| M-01 | Listar, contar, buscar o ver una comida con sus alimentos | Lectura | Cubierta | La colección canónica excluye comidas incrustadas y borradores, y pagina sin confundir total con página. |
| M-02 | Crear una comida vacía con nombre exacto | Patch determinista | Cubierta | Queda borrador hasta tener composición. |
| M-03 | Crear una comida con alimentos y gramos indicados | Patch determinista compuesto | Cubierta | Un patch puede crear Meal y referenciarla al agregar alimentos. |
| M-04 | “Créame una comida de 450 kcal” | Propuesta nutricional | Parcial | Ya admite kcal-only con reparto heurístico 30/50/20 y conserva el objetivo tras respuestas breves; aún depende de candidatos elegibles suficientes. |
| M-05 | Crear N alternativas con kcal/macros/restricciones | Propuesta/portafolio | Parcial | Debe respetar el N solicitado dentro de límites y declarar calidad/factibilidad. |
| M-06 | Renombrar o eliminar una comida | Patch determinista/destructivo | Cubierta | Sólo sobre la comida propia exacta. |
| M-07 | Agregar o quitar un alimento concreto | Patch determinista | Cubierta | Quitar es destructivo y requiere vista previa. |
| M-08 | Reemplazar Y por Z y dejarlo en 200 g | Patch determinista | Cubierta | `meal.update_food` admite `food_id` y `quantity`. |
| M-09 | Cambiar sólo los gramos de un alimento | Patch determinista | Cubierta | Debe resolver el `MealFood`, no sólo la Meal. |
| M-10 | Reordenar alimentos | Patch determinista | UI | Existe command, falta operación de workspace patch. |
| M-11 | “Con los mismos alimentos, acerca esta comida a 30/40/30” | Propuesta nutricional | Brecha parcial | Debe fijar identidades, optimizar cantidades y mostrar desviación alcanzada. |
| M-12 | “Mantén proteína, baja 100 kcal” | Propuesta nutricional | Brecha parcial | Requiere restricciones duras/blandas explícitas y diagnóstico de factibilidad. |
| M-13 | Copiar, guardar o compartir una comida | Handoff | UI | No debe confundirse copiar con cambiar la original. |
| M-14 | Cambiar la hora de una comida de biblioteca | Aclaración | No aplica | Meal no tiene hora; la hora pertenece a DailyPlanMeal o al snapshot calendarizado. |

### Planes diarios de biblioteca

| ID | Solicitud o ejemplos | Resolución | Cobertura actual | Observación |
| --- | --- | --- | --- | --- |
| DP-01 | Listar, contar, buscar o consultar planes | Lectura | Cubierta | La proyección canónica excluye drafts y `source=program`, igual que la biblioteca web. |
| DP-02 | Crear, renombrar o eliminar un plan | Patch | Cubierta | La creación puede continuar con operaciones de composición en el mismo patch. |
| DP-03 | Agregar, reemplazar o quitar una comida | Patch determinista | Cubierta | El plan recibe snapshots; no enlaza una Meal viva. |
| DP-04 | Cambiar nombre, hora o nota de una comida del plan | Patch determinista | Cubierta | Actúa sobre `DailyPlanMeal` y su Meal snapshot según el campo. |
| DP-05 | Cambiar alimentos o porciones dentro de una comida del plan | Patch determinista | Cubierta parcial | Puede actuar sobre la Meal snapshot, pero la resolución debe evitar la Meal de biblioteca. |
| DP-06 | Reordenar comidas | Patch determinista | UI | Existe command, falta operación de workspace patch. |
| DP-07 | Copiar, guardar, compartir o fijar como plan de hoy | Handoff | UI | El plan fijado tiene semántica de ejecución propia. |
| DP-08 | Ajustar calorías conservando alimentos y estructura | Propuesta proporcional | Cubierta | Escala cantidades de snapshots; no modifica Meals reutilizables. |
| DP-09 | Ajustar kcal y distribución de macros conservando alimentos | Propuesta de optimización | Parcial | El solver debe declarar tolerancias y factibilidad, no prometer coincidencia exacta. |
| DP-10 | Generar un plan completo con N comidas | Propuesta/portafolio | Parcial | La biblioteca y el universo de candidatos deben ser explícitos. |
| DP-11 | Redistribuir kcal/macros entre comidas sin cambiar el total | Propuesta | Brecha parcial | Requiere restricciones por comida y por día. |
| DP-12 | Comparar planes o comparar uno con objetivos | Lectura/comparación | Cubierta parcial | Comparación nutricional disponible; creación/actualización de comparación guardada sigue en UI. |
| DP-13 | “Hazme un plan de 2400 kcal con 1,8 g/kg” o “con distribución 30/50/20” | Propuesta nutricional | Cubierta | Captura PPK o distribución completa, los relaciona con peso y energía y rechaza contradicciones en vez de elegir silenciosamente. |
| DP-14 | Ajustar carbohidratos por hora de entrenamiento o diferenciar día de entrenamiento y descanso | Propuesta contextual | Brecha | Falta una agenda de entrenamiento diaria confiable; no debe inferirse desde actividad general ni simular periodización. |

### Programas plantilla

| ID | Solicitud o ejemplos | Resolución | Cobertura actual | Observación |
| --- | --- | --- | --- | --- |
| PG-01 | Listar, contar, buscar o consultar programas | Lectura | Parcial | Listado y conteo usan la visibilidad web, incluidas copias compartidas aceptadas; falta alinear el detalle de todos los compartidos legibles. |
| PG-02 | Crear programa con nombre y duración | Patch determinista | Cubierta | La duración es parte del estado exacto. |
| PG-03 | Renombrar o eliminar programa | Patch | Cubierta | Eliminar no equivale a cancelar una calendarización activa. |
| PG-04 | Agregar, duplicar o eliminar semana | Patch | Cubierta | Eliminar semana es destructivo. |
| PG-05 | Asignar/quitar/reemplazar un plan en semana y día | Patch determinista | UI | Existe command; decisión 0195 todavía lo deja fuera del patch genérico. |
| PG-06 | Reordenar semanas o días | Patch determinista | UI | Existen commands, faltan adapters de AI. |
| PG-07 | Rellenar días vacíos con planes existentes | Patch compuesto o propuesta | Brecha | Determinista si el usuario indica el mapeo; propuesta si AI decide. |
| PG-08 | Generar/optimizar un programa completo | Propuesta por etapas | Brecha | Necesita objetivos por día/semana, variedad, repetición y límites de escala. |
| PG-09 | Copiar, guardar o compartir programa | Handoff | UI | Sharing opera sobre snapshots portables. |
| PG-10 | Activar/calendarizar programa | Handoff confirmable | UI | Requiere fecha, timezone, revisión de días vacíos y posible reemplazo del activo. |

### Programa activo y calendario

| ID | Solicitud o ejemplos | Resolución | Cobertura actual | Observación |
| --- | --- | --- | --- | --- |
| C-01 | Consultar programa activo, fechas, progreso o historial | Lectura | Cubierta parcial | La consulta debe distinguir plantilla y calendarización. |
| C-02 | Pausar, reanudar o cancelar | Patch de ciclo de vida | Cubierta | Cancelar es destructivo. |
| C-03 | Cambiar notificaciones, hora general o zona horaria | Handoff | UI | Afecta eventos y dispositivos; conserva formulario especializado. |
| C-04 | Cambiar nombre/hora de una comida en un día futuro | Patch sobre snapshot | UI | Existen commands de snapshot; faltan adapters AI y política temporal. |
| C-05 | Agregar, reemplazar, quitar o reordenar comidas/alimentos futuros | Patch o revisión | UI | Pasado y presente con evidencia no deben reescribirse. |
| C-06 | Ajustar porción de un alimento en un día futuro | Patch determinista | UI | Debe identificar día, meal key y food key del snapshot. |
| C-07 | “Aplica este cambio a todos los días futuros” | Revisión calendarizada | Brecha parcial | Es cambio masivo; requiere preview de días afectados y decisión explícita. |
| C-08 | Registrar comida completada/omitida, alimento preparado o nota | Evento de ejecución | UI | Es evidencia append-only, no edición de la plantilla. |
| C-09 | Registrar peso o revisión de periodo | Evento/revisión | UI | Debe preservar fecha y contexto de calendarización. |
| C-10 | Reoptimizar el resto del programa según progreso | Propuesta + revisión futura | Brecha | No puede alterar pasado/presente; requiere métricas y alternativas. |

### Propuestas, comparaciones, Inbox, sharing y cuenta

| ID | Solicitud o ejemplos | Resolución | Cobertura actual | Observación |
| --- | --- | --- | --- | --- |
| X-01 | Listar/ver propuestas y su validación | Lectura | Cubierta | Debe mostrar estado real. |
| X-02 | Elegir otra alternativa de una propuesta | Acción confirmable | UI | El servidor vuelve a validar el payload almacenado. |
| X-03 | Aprobar, rechazar, cancelar, eliminar o aplicar propuesta | Patch de ciclo de vida | Cubierta | Aprobar y aplicar son estados separados. |
| X-04 | Iterar una propuesta: “más económica”, “menos repetida” | Nueva revisión de propuesta | Parcial | Debe conservar objetivo, restricciones y deltas entre revisiones. |
| X-05 | Crear/actualizar/renombrar comparación guardada | Lectura, patch o handoff | Parcial | Sólo renombrar está en workspace patch. |
| X-06 | Consultar recibidos, enviados y favoritos | Lectura | Cubierta | Debe usar Inbox normalizado. |
| X-07 | Guardar, marcar favorito, descartar o eliminar recibido | Handoff | UI | Guardar crea copia propia separada. |
| X-08 | Compartir Food/Meal/DailyPlan/Program | Handoff | UI | Requiere snapshot, canal, destinatario y controles antiabuso. |
| X-09 | Consultar plan comercial, créditos, pagos o documentos | Lectura | Cubierta | Nunca debe revelar datos de otra cuenta. |
| X-10 | Comprar, cambiar o cancelar suscripción | Handoff | UI | El modelo nunca opera directamente sobre el proveedor de pagos. |

### Consultas analíticas y educativas

| ID | Solicitud o ejemplos | Resolución | Cobertura actual | Observación |
| --- | --- | --- | --- | --- |
| A-01 | “¿Cuántas kcal/macros tiene esta comida/plan?” | Lectura + cálculo de producto | Cubierta parcial | Los números finales provienen del backend. |
| A-02 | “¿Qué alimento aporta más proteína?” | Lectura/comparación | Parcial | Debe declarar el conjunto comparado y no razonar sobre una página truncada. |
| A-03 | “¿Por qué el solver no encontró solución?” | Diagnóstico estructurado | Parcial | Ya separa cero candidatos elegibles y expone conteos/readiness; falta completar inviabilidad, seguridad y baja calidad en todo el pipeline visible. |
| A-04 | Explicar una propuesta y sus diferencias | Lectura + explicación | Parcial | Debe usar payload y métricas confiables. |
| A-05 | Consejo nutricional general sin modificar datos | Conversación | Cubierta con límites | No debe fingir personalización clínica ni crear estado implícitamente. |
| A-06 | Solicitud de riesgo médico o ingesta extrema | Orientación segura | Cubierta con límites | Puede informar y pedir contexto; no sustituye atención profesional. |

## Combinaciones frecuentes

Una interacción real puede agrupar varias operaciones:

| Petición | Resultado esperado |
| --- | --- |
| “Crea tofu y tempeh, crea una comida Cena y agrégalos en 180 g y 120 g” | Un patch atómico con dos `food.create`, un `meal.create` y dos `meal.add_food` por referencias. |
| “En Almuerzo cambia arroz por papa a 200 g y renómbrala Almuerzo post-entreno” | Un patch con `meal.update_food` y `meal.rename`. |
| “Crea una comida de 450 kcal, vegetariana, dame tres opciones” | Una propuesta nutricional con tres alternativas, no tres Meals persistidas. |
| “Usa los mismos alimentos del plan y llévalo a 2.000 kcal” | Propuesta proporcional sobre snapshots del DailyPlan. |
| “En el programa activo cambia todos los lunes futuros” | Aclarar el cambio concreto; luego preparar una revisión calendarizada de alcance múltiple. |

## Política de ambigüedad

El asistente no debe pedir confirmaciones conversacionales redundantes cuando ya tiene
los datos necesarios. Sí debe preguntar cuando la respuesta cambia el objetivo:

- dos o más entidades visibles comparten nombre;
- la entidad existe tanto en biblioteca como en un snapshot;
- “todos” puede incluir pasado, presente o futuro;
- una cantidad no indica unidad;
- el usuario pide una distribución de macros sin aclarar gramos o porcentaje energético;
- reemplazar un alimento podría afectar restricciones tipadas de alergia/dieta;
- el usuario pide modificar una entidad compartida que sólo es legible.

Después de resolver la ambigüedad, respuestas breves como “sí”, “la segunda” o “sólo
los días futuros” deben continuar el objetivo pendiente; no deben reiniciar el routing.

## Contrato de factibilidad del solver

Toda operación de optimización debe devolver, como mínimo:

- universo y cantidad de candidatos considerados;
- restricciones duras y preferencias blandas;
- estado matemático separado del estado de calidad del producto;
- objetivo alcanzado, desviaciones y tolerancias;
- razones estructuradas de fallo o fallback;
- alternativas realmente distintas cuando se solicitaron;
- confirmación de que ninguna entidad fue modificada durante el cálculo.

“No encontré una combinación válida” no es una explicación suficiente. Debe distinguir,
por ejemplo, entre cero alimentos habilitados, datos nutricionales incompletos,
restricción de seguridad desconocida, modelo inviable o solución factible de baja
calidad.

## Cómo mantener este catálogo

Cada incidencia o petición nueva debe producir una de estas acciones:

1. agregar una variante lingüística a una fila existente y una regresión;
2. dividir una fila si aparecen alcances o niveles de riesgo diferentes;
3. agregar una fila si el resultado de producto es genuinamente nuevo;
4. actualizar la cobertura cuando se implemente una frontera completa;
5. no marcar una capacidad como cubierta sólo porque existe una tool: debe funcionar de
   extremo a extremo con resolución, autorización, preview/aprobación y resultado real.

La matriz debe revisarse junto con el catálogo canónico de capacidades, los workspace
patches, las proposals, los commands de dominio y las superficies web/móvil. Las
features administrativas permanecen fuera del asistente del usuario final.

## Evidencia ejecutable y ciclo de iteración

El catálogo no se considera validado por la mera existencia de una tool. La regresión
local se ejecuta con:

```bash
scripts/ci_ai_assistant_capability_catalog.sh
```

Ese gate comprueba la estructura de las 82 solicitudes, las proyecciones de biblioteca,
la paginación, el routing de continuaciones breves, los patches deterministas, los
diagnósticos del solver y el harness del proveedor real. Los casos de mayor prioridad
tienen esta evidencia directa:

| IDs | Evidencia principal |
| --- | --- |
| F-01, M-01, DP-01, PG-01 | `test_ai_workspace_library_coherence.py` |
| M-04, A-03 | `test_nutrition_solver_meal_proposal.py` y `test_solver_food_candidates_query.py` |
| DP-13 | `test_macro_target_policy.py` y `test_nutrition_engine_target_estimator.py` |
| M-08 | `test_workspace_patch_can_replace_meal_food_and_set_exact_quantity` |
| Continuaciones como “sí, claro” | `test_tool_selection_workspace_patch.py` |
| Integridad del catálogo | `test_user_request_capability_catalog.py` |

Para validar lenguaje natural y datos reales de staging se usa el escenario explícito
`bibliotecas_coherentes` del gate de proveedor real. Antes de hacer llamadas, se puede
listar el catálogo; la ejecución live consume proveedor/créditos y requiere usuario:

```bash
python manage.py validate_ai_assistant_real_provider --list-scenarios
python manage.py validate_ai_assistant_real_provider \
  --live --user-email usuario@example.com \
  --scenario bibliotecas_coherentes \
  --fail-on-hard-regression
```

El escenario calcula los totales esperados desde las mismas proyecciones canónicas que
usa la web y exige que cada respuesta visible devuelva `TOTAL: N`. Así una discrepancia
entre datos persistidos, tool y texto del modelo se convierte en un fallo reproducible.
