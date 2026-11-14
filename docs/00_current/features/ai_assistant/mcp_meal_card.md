# Card de comidas en conversaciones externas

## Resultado buscado

Mostrar una comida de My Scoope como card interactiva de solo lectura dentro de
ChatGPT u otro cliente compatible con MCP Apps. El identificador de la comida
selecciona un objeto legible para el usuario autenticado; el modelo no aporta
nutrientes ni HTML. La UI de My Scoope muestra los valores calculados por el backend.

## Decisión de implementación

La web usa `card_main_meal.html` y `card_child_meal.html` con múltiples includes,
CSS global, contexto Django y acciones propias de la web. Esos templates no son
HTML autónomo para un iframe. La card MCP es un adaptador visual pequeño del mismo
DTO que ya entrega `read_meal_tool` y conserva la estructura principal: título,
energía, macronutrientes y alimentos con cantidades. No intenta replicar las
acciones de edición de la web.

```text
ChatGPT / cliente MCP Apps
  → search_user_meals(query, limit ≤ 10) → meal_id
  → read_meal(meal_id)
  → MCP FastMCP (scope myscoope:read)
  → dispatch_tool_call
  → Django /ai-tools/read-meal/
  → read_meal_tool → get_meal_detail → MealDTO
  → structuredContent + ui://myscoope/meal-card-v1.html
  → card HTML en iframe
```

`search_user_meals` y `read_meal` están definidos en el catálogo canónico del AI
Assistant y proyectados por MCP. La búsqueda está limitada a diez resultados y
no monta UI; la lectura de detalle sí monta la card. La autorización, visibilidad
de Meals propias o públicas no draft, y
cálculo nutricional permanecen en Django. El iframe no recibe tokens, no hace
peticiones de red y no puede modificar la comida. La card usa `textContent` para
mostrar nombres, evita interpretar HTML de datos y muestra un estado neutro ante
un resultado fallido.

El descriptor de `read_meal` anuncia `_meta.ui.resourceUri` y el recurso usa
`text/html;profile=mcp-app`. El resultado MCP incluye `structuredContent` con el
contrato `ok/data/error`; así sigue siendo útil en clientes que no renderizan UI.
La card recibe `ui/notifications/tool-result` y alterna localmente entre Nutrición
y Alimentos. El URI incluye versión porque los clientes pueden cachear recursos.

## Validación local reproducible

Desde un checkout con dependencias instaladas:

```bash
PYTHON_BIN=/ruta/a/python scripts/test_mcp.sh
DJANGO_SETTINGS_MODULE=miapp.settings.dev NUTRITION_ONBOARDING_GATE_ENABLED=false \
  /ruta/a/python manage.py test \
  notas.tests.test_ai_tools_api_read_endpoints \
  notas.tests.test_ai_tools_api_permission_boundaries \
  notas.tests.test_ai_read_tools --noinput
/ruta/a/python mcp_server/browser_smoke_meal_card.py \
  --screenshot /tmp/meal-card.png
```

La suite MCP comprueba la proyección del catálogo, la búsqueda acotada, el scope de lectura, el URI y
MIME del recurso, el resultado estructurado, la ruta HTTP autenticada y un fallo
de lectura sin comida en la respuesta. La suite Django protege la autorización y
los datos del endpoint existente. El smoke de navegador comprueba render,
pestañas, ancho móvil, tema oscuro, error y texto HTML no ejecutable. Este smoke
usa datos sintéticos y requiere Playwright Chromium de `e2e/requirements.txt`.

## Prueba pendiente en una conversación real

1. Conectar un endpoint MCP privado por Secure MCP Tunnel o HTTPS de staging.
   Configurar autenticación por usuario y `MYSCOOPE_MCP_USER_TOKENS_ONLY=true`;
   no usar el token legado de una cuenta compartida para pruebas con datos reales.
2. En ChatGPT Plugins, añadir el servidor MCP personalizado, instalarlo para uso
   interno y refrescar sus metadatos después de desplegar esta versión. Confirmar
   que aparecen `search_user_meals`, `read_meal` y el recurso
   `ui://myscoope/meal-card-v1.html`.
3. Con una comida de prueba perteneciente a la cuenta de prueba, pedir “Muestra la
   comida [nombre]”. Verificar selección de tool, `meal_id`, datos, card visible,
   cambio de pestañas y ausencia de errores de consola. Probar ID inexistente y
   una comida privada de otra cuenta: ninguna debe mostrar datos.
4. Repetir en un cliente MCP sin UI para comprobar que el resultado textual y
   estructurado sigue siendo útil. Comprobar por separado si la versión de Codex
   usada renderiza MCP Apps; la documentación oficial garantiza la UI en ChatGPT,
   pero la compatibilidad de otros clientes depende de su implementación.

La prueba en ChatGPT requiere el despliegue explícito del servidor MCP de staging,
un endpoint accesible desde ese cliente y una cuenta de prueba autorizada. La
presencia del código en `origin/staging` no activa por sí sola el servicio MCP si
su despliegue automático está deshabilitado. La integración selecciona
`staging-fast` por los archivos de aplicación cambiados.

Referencias oficiales: [Add UI to your MCP server](https://developers.openai.com/plugins/build/chatgpt-ui),
[Connect and test your plugin](https://developers.openai.com/plugins/deploy/connect-chatgpt).
