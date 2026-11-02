# Alineación de la web con la experiencia móvil

Estado: alineación de navegación y lenguaje implementada en la rama de trabajo; capacidades pendientes de diseño.
Fecha: 2026-11-02

## Criterio

La web y la app presentan los mismos conceptos y resultados del producto con nombres reconocibles. La web conserva sus patrones propios de escritorio y navegador. Los identificadores de modelos, API y rutas existentes permanecen estables.

| Área | Nombre visible en web | Entrada web |
| --- | --- | --- |
| Inicio | Inicio | `home_view` |
| Planificación por fecha | Mi calendario | `calendar_preview` |
| Gestión del programa | Programa en curso | `calendarization_dashboard`, desde Mi calendario |
| Comparaciones | Comparaciones | `comparator_index` |
| Intercambio | Compartidos | `inbox_list` |
| Librería de programas | Mis Programas | `program_list` |
| Librería de minutas diarias | Mis Minutas | `dailyplan_list` |
| Librerías restantes | Mis Comidas, Mis Alimentos | `meal_list`, `food_list` |
| Conversaciones y propuestas | Asistente Nutricional | `ai_nutrition_chat_list`, `proposal_list` |

`Minuta diaria` sigue siendo el nombre de la entidad singular. `Mis Minutas` es el título corto de su librería. El vocabulario de producto vive en `docs/00_current/PRODUCT_VOCABULARY.json`; el cliente móvil y la presentación Django tienen constantes de interfaz propias.

## Capacidades que necesitan una etapa funcional separada

1. **Digitalizar etiqueta nutricional en web.** El contrato de extracción, consentimiento, costo y revisión está descrito en `docs/00_current/features/nutrition_label_capture.md` y el servidor expone `/api/v1/foods/label-captures/*` para el cliente móvil. La web necesita adquisición por archivo o cámara del navegador, revisión editable y confirmación explícita antes de crear un alimento. No se ofrece un acceso web hasta completar el flujo.
2. **Revisión de progreso y ajustes.** La web muestra cumplimiento y registra peso, pero no presenta la revisión periódica ni la decisión sobre ajustes que usa la app móvil (`mobile_api/routes/calendarization.py`, `/program/reviews` y `/program/revisions`). Diseñar una vista web de progreso con tendencia de peso, historial y revisión de propuestas prospectivas, reutilizando los comandos de dominio y sus permisos.
3. **Recordatorios.** La web tiene suscripción push asociada al programa; la app combina recordatorios nativos y del servidor. Definir una configuración comprensible para navegador, su comportamiento cuando no hay permiso y la relación con los recordatorios del programa antes de ofrecer equivalencia de controles.
4. **Exploración de fechas.** La vista web actual muestra una ventana de cinco semanas. La app permite navegar por meses. Una mejora web posterior debe permitir consultar otras fechas sin modificar el historial ni la autoridad de `CalendarizedDay`.

Estas etapas requieren decisiones de interfaz y pruebas funcionales propias. Ninguna se resuelve cambiando únicamente títulos o enlaces.
