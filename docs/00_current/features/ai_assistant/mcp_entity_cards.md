# Cartas de alimento y minuta en conversaciones externas

## Resultado y contrato

Las lecturas autorizadas `read_food(food_id)` y `read_dailyplan(dailyplan_id)` presentan tarjetas de solo lectura en clientes compatibles con MCP Apps. El alimento muestra nombre, nutrición y distribución por 100 g o 100 ml según `portion_unit`, que es la base del `FoodDTO` operativo. La minuta muestra nombre, conteo de comidas y alimentos, totales nutricionales y una lista de comidas con hora, alimentos y calorías. No se calculan nutrientes desde texto generado por el modelo; los valores provienen de `FoodDTO` y `DailyPlanDTO` del backend.

Ambas herramientas se proyectan desde el catálogo canónico del AI Assistant y usan el scope `myscoope:read`. `read_food` llama a `/app/ai-tools/read-food/`; `read_dailyplan` conserva `/app/ai-tools/read-dailyplan/`. Esos endpoints aplican autenticación y visibilidad. La respuesta MCP mantiene `ok/data/error` y `structuredContent` cuando el cliente no presenta interfaz. Los recursos versionados son `ui://myscoope/food-card-v1.html` y `ui://myscoope/dailyplan-card-v1.html`.

La vista reutiliza `entity_card_v1.source.html`, tokens de `design/ui-contract.json` y el mismo patrón visual de la comida. `npm run generate:ui` produce `entity_card_v1.html`; `npm run check:ui` exige sincronía. Los dos recursos entregan ese HTML y el iframe selecciona la entidad según el resultado autorizado. El documento tiene fondo exterior transparente, usa `textContent` para datos variables y muestra un estado neutro si falla la lectura. Comunica su altura al host con MCP Apps.

## Iteración y validación

La sección «En conversación» de `/app/dev/ui-system/` ofrece tres entidades y anchos 1100, 760, 570, 390 y 320 px con datos ficticios. El servidor `mcp_server/dev_meal_card_preview.py`, conectado únicamente al túnel privado de desarrollo, expone `preview_food_card`, `preview_dailyplan_card` y CSS de la fuente editable. Una nueva ejecución genera URI de recurso distintos para evitar HTML antiguo en caché; después se actualizan las herramientas del plugin privado. El servidor no consulta Django ni usa datos de cuentas.

Pruebas locales: `scripts/test_mcp.sh`, `mcp_server/browser_smoke_entity_card.py`, `notas.tests.test_ui_system_gallery` y las pruebas de autorización de `/ai-tools/read-food/` y `/ai-tools/read-dailyplan/`. La revisión en un iframe de ChatGPT sigue siendo necesaria para confirmar dimensiones del host; las capturas de la galería y Chromium son aproximaciones.

Esta fase es una implementación local para revisión visual. No cambia la lista de herramientas permitidas del servicio de staging, no despliega el MCP y no activa capacidades para usuarios.
