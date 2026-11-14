# Card de comidas en conversaciones externas

## Resultado buscado

Mostrar una comida de My Scoope como card interactiva de solo lectura dentro de
ChatGPT u otro cliente compatible con MCP Apps. El identificador de la comida
selecciona un objeto legible para el usuario autenticado; el modelo no aporta
nutrientes ni HTML. La UI de My Scoope muestra los valores calculados por el backend.

## Decisión de implementación

La web usa `card_main_meal.html` y `card_child_meal.html` con múltiples includes,
CSS global, contexto Django y acciones propias de la web. Esos templates no son
HTML autónomo para un iframe. La card MCP representa el mismo DTO que ya entrega
`read_meal_tool`: título, energía, barras de macronutrientes y detalle de cada
alimento. En escritorio muestra una tabla con aportes calóricos, distribución y
porcentajes de cada macro; en móvil muestra filas y pestañas para explorar esos
datos. Las barras de cada alimento se calculan a partir de los valores numéricos
del DTO. La card no replica las acciones de edición de la web.

```text
ChatGPT / cliente MCP Apps
  → search_user_meals(query, limit ≤ 10) → meal_id
  → read_meal(meal_id)
  → MCP FastMCP (scope myscoope:read)
  → dispatch_tool_call
  → Django /app/ai-tools/read-meal/
  → read_meal_tool → get_meal_detail → MealDTO
  → structuredContent + ui://myscoope/meal-card-v3.html
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
La card completa `ui/initialize` y `ui/notifications/initialized` antes de recibir
`ui/notifications/tool-result`; también comunica su altura al host con
`ui/notifications/size-changed`. El detalle móvil alterna localmente entre
Alimentos, Calorías, Macros, Dist y Alloc.
El URI incluye versión porque los clientes pueden cachear recursos. La versión 2
corrigió un timeout de inicialización descubierto en una conversación real. La
versión 3 incorpora tokens y receta del contrato visual común; la versión 2 sigue
disponible para conversaciones anteriores.

La sección «En conversación» de la galería web (`/app/dev/ui-system/`, solo en
DEBUG) sirve exactamente `meal_card_v3.html` en un iframe aislado. Su host de prueba
reproduce el saludo MCP Apps y envía datos sintéticos. Permite revisar claro,
oscuro, 1100/390/320 px, dos comidas de ejemplo, nombres largos, vacío y error.
El archivo fuente editable
es `meal_card_v3.source.html`; `npm run generate:ui` produce el HTML servido tanto
por la galería como por MCP. `npm run check:ui` detecta desincronización.

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
los datos del endpoint existente. El smoke de navegador simula el saludo del
iframe y comprueba render,
tabla, barras, pestañas móviles, ancho móvil, tema oscuro, error y texto HTML no
ejecutable. Este smoke
usa datos sintéticos y requiere Playwright Chromium de `e2e/requirements.txt`.

## Configuración y prueba en una conversación real

1. Conectar un endpoint MCP privado por Secure MCP Tunnel o HTTPS de staging.
   Configurar autenticación por usuario y `MYSCOOPE_MCP_USER_TOKENS_ONLY=true`;
   no usar el token legado de una cuenta compartida para pruebas con datos reales.
2. Registrar en staging un cliente OAuth con el callback exacto mostrado por
   ChatGPT y únicamente el scope `myscoope:read`. En ChatGPT Plugins, añadir el
   servidor MCP personalizado para uso privado y refrescar sus metadatos después
   de desplegar esta versión. Confirmar
   que aparecen `search_user_meals`, `read_meal` y el recurso
   `ui://myscoope/meal-card-v3.html`. Si el servicio usa
   `MYSCOOPE_MCP_ALLOWED_TOOLS`, añadir ambos nombres a la lista existente y
   ejecutar **Refresh tools** en la configuración del plugin de ChatGPT.
3. Con una comida de prueba perteneciente a la cuenta de prueba, pedir “Muestra la
   comida [nombre]”. Verificar selección de tool, `meal_id`, datos, card visible,
   cambio de pestañas y ausencia de errores de consola. Probar ID inexistente y
   una comida privada de otra cuenta: ninguna debe mostrar datos.
4. Repetir en un cliente MCP sin UI para comprobar que el resultado textual y
   estructurado sigue siendo útil. Comprobar por separado si la versión de Codex
   usada renderiza MCP Apps; la documentación oficial garantiza la UI en ChatGPT,
   pero la compatibilidad de otros clientes depende de su implementación.

La prueba en ChatGPT requiere el despliegue explícito del servidor MCP de staging,
un endpoint accesible desde ese cliente y una cuenta autorizada. La presencia del
código en `origin/staging` no activa por sí sola el servicio MCP si su despliegue
automático está deshabilitado. La integración selecciona `staging-fast` por los
archivos de aplicación cambiados.

### Evidencia de staging: 14 de noviembre de 2026

- `origin/staging` publicó `b052f6e87110460f3adf0461a4c6beb22bed937d`; la
  [ejecución de CI](https://github.com/DidesCabrera/my-scoope/actions/runs/43612250767)
  terminó correctamente con nivel `staging-fast`. El despliegue manual del MCP
  `dep-dbs87hjl550s73foegb0` quedó `live` con ese mismo commit.
- El plugin personal de ChatGPT se conectó por OAuth a staging con
  `myscoope:read`. El filtro `MYSCOOPE_MCP_ALLOWED_TOOLS` conservó sus cuatro
  herramientas previas y añadió `search_user_meals` y `read_meal`.
- En una conversación real, la búsqueda devolvió Meals visibles para la cuenta
  conectada. `read_meal` mostró la card v2 dentro del chat; las pestañas Nutrición
  y Alimentos funcionaron. Un ID inexistente devolvió `not_found`, `data: {}` y
  un estado de error sin datos nutricionales.
- La separación entre usuarios se verificó en pruebas Django. No se consultó una
  comida privada de otra cuenta en la conversación real.

El contrato OpenAPI se genera con las versiones fijadas en `requirements.txt`.
Un aparente desfase local se debió a usar Pydantic 2.13.4 en vez de la versión
fijada 2.14.3; con 2.14.3 el contrato publicado coincide con el generado.

Referencias oficiales: [Add UI to your MCP server](https://developers.openai.com/plugins/build/chatgpt-ui),
[Connect and test your plugin](https://developers.openai.com/plugins/deploy/connect-chatgpt).
