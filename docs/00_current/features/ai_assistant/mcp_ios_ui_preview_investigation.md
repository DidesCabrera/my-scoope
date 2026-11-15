# Vista previa MCP UI en ChatGPT para iPhone

Investigación del 14 de noviembre de 2026. La vista previa local y el MCP alojado
en staging se verifican por separado.

## Reproducción

1. Conectar el plugin privado «My Scoope Card Preview» mediante el túnel privado de OpenAI a `dev_meal_card_preview.py`.
2. En un chat nuevo de ChatGPT para iPhone, seleccionar el plugin y pedir `preview_minimal_card`.
3. La herramienta devuelve `{"ok":true,"data":{"message":"Vista mínima MCP"},"error":null}`. El área del componente queda como un rectángulo gris vacío.

`preview_minimal_card` sirve un HTML pequeño, con el texto visible «Vista mínima MCP visible» y solo `ui/initialize`, `ui/notifications/initialized` y el aviso de altura. No usa la card de comida, CSS externo, imágenes, datos de usuario ni llamadas adicionales desde el iframe. El recurso se registra con `_meta.ui.resourceUri` y `text/html;profile=mcp-app`.

## Comparación observada

| Cliente y conexión | Resultado |
| --- | --- |
| ChatGPT web + vista previa por túnel privado + `preview_minimal_card` | Tarjeta fucsia y texto visibles. |
| ChatGPT iPhone + vista previa por túnel privado + `preview_minimal_card` | Rectángulo gris vacío. |
| Safari del mismo iPhone + vista previa por túnel privado + `preview_minimal_card` | Rectángulo gris vacío. |
| ChatGPT web + vista previa por túnel privado + cards de comida y minuta | Componentes visibles e interactivos. |
| ChatGPT iPhone + vista previa por túnel privado + cards de comida y minuta | Datos disponibles para ChatGPT; componente gris vacío. |
| ChatGPT iPhone + MCP alojado en staging + card de comida | Card visible. |

El alias opcional `_meta["openai/outputTemplate"]` no cambió el resultado en iPhone. El texto que ChatGPT redacta sobre si la card se mostró no es evidencia confiable: en web afirmó que la tarjeta mínima no había aparecido cuando sí estaba visible.

## Alcance de la conclusión

La app iOS puede mostrar una card MCP de My Scoope desde staging. La vista previa por túnel privado funciona en ChatGPT web y devuelve datos al iPhone. El mismo fallo en Safari del iPhone descarta que sea exclusivo de la app nativa. No hay evidencia de un defecto en los estilos o datos de la card.

Una revisión posterior de los registros del servidor identificó un fallo concreto: tras reiniciar la vista previa, ChatGPT siguió leyendo `ui://myscoope-dev/meal-card-8c29a2b83a154b5393ce1f10ceb23cc5.html`, pero el nuevo proceso había registrado otro identificador aleatorio. `resources/read` respondió `Unknown resource` y HTTP 400. El servidor ahora anuncia URI versionados estables, acepta los URI aleatorios anteriores mediante plantillas de compatibilidad y conserva el MIME `text/html;profile=mcp-app`. Una prueba local del protocolo confirmó HTTP 200 y HTML para el URI antiguo que fallaba. La herramienta siguió respondiendo correctamente a través del túnel privado. Estas comprobaciones demuestran que se corrigió la lectura fallida; todavía no demuestran que el cliente iOS presente la tarjeta.

La prueba posterior en un chat nuevo del iPhone siguió mostrando el rectángulo gris. El registro de esa misma prueba sí muestra `ReadResourceRequest` exitoso para el HTML antiguo y una llamada exitosa a la herramienta. Por lo tanto, la falla que queda está después de la lectura del recurso, en la entrega o montaje del componente en ese cliente. Una diferencia adicional respecto al MCP de staging era el formato de respuesta HTTP: la vista previa usaba `text/event-stream` y staging configura `json_response=True`. Se alineó la vista previa con staging; la comprobación local confirmó HTTP 200, `application/json` y el HTML con MIME MCP Apps, y la llamada por el túnel devolvió la comida ficticia. La siguiente prueba en iPhone volvió a mostrar el rectángulo gris. Igualar el formato HTTP no resolvió el problema. Esto acota el fallo observado a la ruta de vista previa por túnel y cliente móvil, sin demostrar qué parte interna de ChatGPT lo causa.

La [guía de diagnóstico de OpenAI](https://developers.openai.com/plugins/deploy/troubleshooting) pide comprobar descriptor, MIME y recurso y, si persiste la falla, reunir registros y capturas para escalar. La [documentación de plugins](https://learn.chatgpt.com/docs/plugins) declara compatibilidad móvil, y las [pautas de plugins](https://developers.openai.com/plugins/plugin-guidelines) incluyen sus componentes UI.

## Verificación con el MCP alojado en staging

La card v6 se publicó en `origin/staging` en el commit
`26be90fd65e942706f5ea62baab925f44dd334b5`. La [ejecución de CI](https://github.com/DidesCabrera/my-scoope/actions/runs/43652667108)
terminó correctamente con nivel `staging-fast`, y el MCP alojado en Render quedó
`live` con ese commit. La primera prueba en iPhone mostró una card, pero el
usuario observó que conservaba la estética antigua. Esa prueba solo confirmó
que la ruta alojada podía presentar una UI; no verificó la versión nueva.

La configuración del servicio restringía `MYSCOOPE_MCP_ALLOWED_TOOLS` a las seis
herramientas anteriores. Se conservaron esos seis nombres y se añadieron
`read_food` y `read_dailyplan`; el despliegue de esa configuración quedó `live`.
Después se ejecutó **Refresh tools** en el plugin privado «My Scoope Staging» de
ChatGPT. La ficha del plugin pasó de **Read 5** a **Read 7** y mostró ambas
herramientas nuevas. El código desplegado anuncia
`ui://myscoope/meal-card-v6.html` para `read_meal`.

En un chat nuevo de ChatGPT web, `read_meal` con `meal_id=39` presentó la card
alojada. Con el viewport de Chrome en 424 px, se observaron las cinco pestañas
**Alimentos, Calorías, Macros, Dist y Alloc** y se verificó que cada una alterna
su panel. Después, en un chat nuevo de la app ChatGPT para iPhone, el usuario
confirmó que la card nueva aparece y que las cinco pestañas funcionan. Esta
observación verifica también la presentación en el cliente móvil real.

La vista previa por túnel privado sigue mostrando un rectángulo gris en iPhone;
publicar y refrescar el MCP alojado no demuestra que el túnel esté corregido.
Conservar las capturas y los registros de `resources/read` para escalar a OpenAI
si se necesita la vista previa local en iPhone.
