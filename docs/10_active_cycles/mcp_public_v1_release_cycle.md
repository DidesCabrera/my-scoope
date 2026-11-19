# MCP público v1 · biblioteca y propuesta revisable

Status: active
Estado de implementación: local; sin despliegue ni postulación pública.
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
| 1. Fijar v1 | Definido: seis lecturas, tres entidades y creación de propuesta revisable. Falta validar el corte con usuarios. | Contrato y allowlist exactos, ejemplos representativos. |
| 2. Robustecer el producto | Búsqueda de minutas y proyección MCP implementadas localmente; 206 pruebas MCP, 29 pruebas Django relevantes y lint pasan. Fichas y OAuth ya existen. | Datos de demo, revisión de privacidad y servicio remoto con el perfil v1. |
| 3. Validar el recorrido | Pendiente para esta versión. Hay evidencia previa de cards con datos ficticios y de comidas en staging, no del recorrido completo de v1. | Conexión real ChatGPT/Codex, siete tools descubiertas, búsqueda → ficha → propuesta, pruebas de permisos y revisión visual en web y móvil. |
| 4. Presentar a OpenAI | Antecedente de envío en mayo de 2026; estado actual sin verificar. Esta versión no se ha enviado. | Resolver el estado del envío anterior; identidad empresarial verificada, URL pública estable, materiales de listing, video real, acceso de revisor, casos ejecutados, scan y envío a revisión. |

En la cuenta de correo personal hay confirmación de recepción de una postulación
«My Scoope» del 13-05-2026 y un caso de soporte por verificación (08802667).
Las respuestas de soporte del 13 y 15 de mayo solicitaron descripción y grabación
del error. No se encontró en esa correspondencia una decisión de aprobación o
rechazo; antes de retomar el portal hay que consultar el estado del borrador o
revisión anterior. Ese envío histórico no acredita esta v1 MCP.

## Casos de revisión propuestos

Estos casos son borradores; requieren una cuenta de demostración con alimentos,
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

1. Integrar el cambio local en staging con el gate que seleccione CI, y desplegar
   backend y MCP con allowlist v1 explícita. Después comprobar OAuth, PRO, scopes,
   revocación, visibilidad y las siete tools desde un cliente real. El cliente OAuth
   debe autorizar `myscoope:read` y `myscoope:proposals:create`, y la conexión debe
   renovarse con ambos permisos antes del recorrido.
2. Preparar una cuenta demo PRO, con datos propios reproducibles y acceso para
   revisión sin pasos adicionales. No guardar credenciales en el repositorio.
3. Verificar en la web pública los enlaces de sitio, soporte, privacidad y
   términos, la cobertura de datos que devuelven las tools y el origen HTTPS
   definitivo del servidor MCP.
4. Grabar y alojar una demostración real del recorrido, completar listing,
   icono, países y declaración comercial; ejecutar cinco casos positivos y tres
   negativos con el mismo artefacto que se enviará a revisión.

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
