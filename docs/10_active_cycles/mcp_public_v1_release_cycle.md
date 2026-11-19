# MCP público v1 · biblioteca y propuesta revisable

Status: active
Estado de implementación: v1 integrada en `main` y desplegada en producción;
postulación pública pendiente de requisitos de cuenta y revisión de OpenAI.
Fecha: 2026-11-19.

## Resultado y corte de producto

Una persona con cuenta autorizada conecta My Scoope desde un cliente MCP, encuentra
alimentos, comidas y minutas visibles para ella, abre sus fichas nutricionales y
puede crear una propuesta nutricional pendiente de revisión.
My Scoope autentica, decide la visibilidad, calcula los datos y guarda la propuesta;
el cliente externo solicita y presenta resultados. La primera versión pública
tiene siete tools: seis lecturas y una creación revisable.

| Recorrido | Descubrimiento | Ficha |
| --- | --- | --- |
| Alimentos operacionales | `list_food_catalog` con búsqueda | `read_food` |
| Comidas visibles | `search_user_meals` | `read_meal` |
| Minutas visibles | `search_user_dailyplans` | `read_dailyplan` |

La búsqueda de minutas proyecta la misma capacidad `search_user_dailyplans` del
catálogo canónico del asistente nutricional y usa su query de producto. Las tools
MCP no duplican lógica nutricional. En el asistente interno, las consultas pueden
entrar por `query_workspace`; las micro-tools canónicas siguen disponibles para
MCP y compatibilidad. Las tres fichas de entidad ya tienen componentes MCP Apps.

La configuración de este perfil debe fijar explícitamente
`MYSCOOPE_MCP_ALLOWED_TOOLS` a los seis nombres de lectura de la tabla y
`create_nutrition_engine_dailyplan_proposal`. Esta última tool ya está
implementada y genera una `NutritionProposal` para una nueva minuta a partir
de un `NutritionBrief` estructurado; no cambia ninguna minuta existente.
El valor vacío habilita toda la superficie registrada y no corresponde al corte
público v1. Otras propuestas, preparaciones, suplementos, calendario y aplicación
de cambios quedan para una versión posterior con evaluación propia. El acceso
sigue sujeto a autenticación, entitlement PRO y scopes `myscoope:read` y
`myscoope:proposals:create` para la tool de propuesta.

En la prueba previa de “Component in Codex”, la conexión de staging falló con
`oauth_scope_not_allowed`: ChatGPT solicitó ambos scopes, pero el cliente OAuth
estaba registrado solo para lectura. La conexión volvió a completarse tras
autorizar creación de propuestas revisables y reconectar. El bloqueo era de
configuración de ese cliente, no una exigencia universal de OpenAI de tener tools
de escritura. Este antecedente debe ser un caso obligatorio del smoke de v1.

```text
MYSCOOPE_MCP_ALLOWED_TOOLS=list_food_catalog,read_food,search_user_meals,read_meal,search_user_dailyplans,read_dailyplan,create_nutrition_engine_dailyplan_proposal
```

## Hitos y evidencia de avance

| Hito | Estado al 19-11-2026 | Cierre verificable |
| --- | --- | --- |
| 1. Fijar v1 | Cerrado: seis lecturas, tres entidades y creación de propuesta revisable, con allowlist exacta de siete tools. | Mantener el contrato público en la siguiente versión. |
| 2. Robustecer el producto | Código integrado mediante PR #155; gate `full` de la PR aprobado, servicios Django y MCP de producción en el merge `f9d46e112c2aadfef00c2e02f288c1845f6874f6` y perfil de siete tools configurado. Página pública de la integración disponible. | Cuenta demo PRO, datos reproducibles y revisión final de privacidad. |
| 3. Validar el recorrido | Parcial: OAuth público anuncia ambos scopes, el backend ya reconoce el recurso MCP, el servidor exige token y la página pública responde. El escaneo del portal se detiene porque la cuenta conectada no tiene PRO. | Reconectar una cuenta de prueba PRO, descubrir las siete tools, ejecutar búsqueda → ficha → propuesta y los casos de permisos. |
| 4. Presentar a OpenAI | El plugin existente está `Not published` y `Review status Unavailable`; todavía no se ha enviado esta versión. La organización está verificada como individuo, pero la verificación empresarial de My Scoope SpA no ha comenzado. | Completar identidad empresarial, cuenta de revisor, video real, países, ejecución de casos, ZIP definitivo y envío a revisión. |

En la cuenta de correo personal hay confirmación de recepción de una postulación
«My Scoope» del 13-05-2026 y un caso de soporte por verificación (08802667).
Las respuestas de soporte del 13 y 15 de mayo solicitaron descripción y grabación
del error. No se encontró en esa correspondencia una decisión de aprobación o
rechazo; antes de retomar el portal hay que consultar el estado del borrador o
revisión anterior. Ese envío histórico no acredita esta v1 MCP.

## Casos de revisión propuestos

Estos casos son borradores; requieren una cuenta de demostración PRO con alimentos,
dos comidas y dos minutas de nombres distinguibles. Registrar IDs y resultados
esperados desde esos datos reales antes de ejecutar. Estado de los ocho: **no
ejecutados** en un cliente externo para esta versión.

| Tipo | Solicitud natural | Resultado observable |
| --- | --- | --- |
| Positivo | «Busca avena en mis alimentos y muéstrame su información nutricional». | `list_food_catalog` y `read_food`; valores respaldados por la ficha devuelta. |
| Positivo | «Encuentra mi comida Desayuno y ábrela». | `search_user_meals` y `read_meal`; composición y nutrientes de esa comida. |
| Positivo | «Muéstrame la minuta Día de entrenamiento». | `search_user_dailyplans` y `read_dailyplan`; tarjeta de la minuta correcta. |
| Positivo | «¿Cuál de mis comidas contiene más proteína, Desayuno o Almuerzo?». | Búsqueda y lectura de ambas comidas; comparación fundada en sus valores devueltos. |
| Positivo | «Propón una nueva minuta diaria de 2500 kcal para revisar en My Scoope». | `create_nutrition_engine_dailyplan_proposal` recibe un `NutritionBrief` válido y crea una propuesta pendiente, sin aplicar una minuta. |
| Negativo | «Aplica de inmediato la propuesta a mi minuta». | Explicar que la aprobación se realiza en My Scoope; ninguna tool de aplicación. |
| Negativo | «Agrega un suplemento a mi minuta». | Explicar el límite y orientar a My Scoope; ninguna tool de suplementos. |
| Negativo | «Muéstrame la minuta privada de otra persona». | No afirmar acceso ni revelar contenido; ninguna ficha ajena autorizada. |

## Bloqueos concretos para la postulación

1. Preparar y conectar una cuenta demo PRO, con datos propios reproducibles y
   acceso para revisión sin pasos adicionales. La reconexión del plugin en el
   portal solicitó ambos scopes, pero la cuenta conectada recibió
   `mcp_pro_required`; no se debe desactivar la exigencia PRO para superar el
   escaneo. No guardar credenciales en el repositorio.
2. Verificar desde esa cuenta las siete tools descubiertas, búsqueda → ficha →
   propuesta, visibilidad, revocación y permisos. La URL pública de la ficha es
   <https://www.myscoope.com/integrations/mcp/>; sitio, soporte, privacidad y
   términos responden públicamente.
3. Completar en OpenAI la verificación empresarial para publicar bajo My Scoope
   SpA. Actualmente solo aparece aprobada la verificación individual de Felipe
   Dides. La identidad pública no se puede atribuir a la empresa hasta verificarla.
4. Grabar y alojar una demostración real del recorrido, confirmar países y
   declaración comercial, ejecutar cinco casos positivos y tres negativos,
   finalizar el ZIP y enviarlo a revisión. El borrador local de paquete tiene
   manifest, endpoint OAuth, logo y ocho casos; no contiene video ni credenciales
   de revisión y no es apto todavía para envío.

OpenAI exige una URL MCP real y estable, verificación del publicador, materiales
de listing, acceso de revisor y pruebas. La aprobación y la publicación son pasos
distintos. Fuentes vigentes consultadas:
[requisitos de revisión MCP](https://developers.openai.com/plugins/deploy/app-review),
[envío de plugins](https://developers.openai.com/plugins/deploy/submission) y
[guías de plugins](https://developers.openai.com/plugins/plugin-guidelines).

Texto preliminar para el listing, sujeto a confirmar marca, publicador y alcance
comercial: **My Scoope** — «Consulta tus alimentos, comidas y minutas de My Scoope
desde ChatGPT o Codex. Abre sus fichas nutricionales y crea una propuesta para
revisión. My Scoope controla los datos, los permisos y la aplicación de cambios».
