# Alineación web con la app móvil actual

Estado: ampliación local en `codex/web-mobile-parity`; pendiente de integración y QA de staging.
Actualizado: 2026-11-14.
Base comprobada al comenzar esta ampliación: `origin/staging` = `c75f9e5f53e2c73c37d4935b8d1024f23b9adcc1`.

## Referencia y criterio

La referencia visual y funcional es el cliente móvil actual en `main`: `mobile/src/components/navigation/app-navigation.tsx`, `mobile/src/components/navigation/sidebar-items.tsx`, `mobile/src/app/today.tsx`, `mobile/src/components/calendarization/calendar-overview-screen.tsx` y `mobile/src/app/account.tsx`. Los datos y comandos se comprobaron en `mobile_api/`, `notas/application/` y los modelos. La inspección en el iPhone 17 Pro del simulador confirmó el orden de la barra lateral, el calendario y el progreso.

La web usa navegación, formularios y paneles adecuados al navegador. Los nombres y resultados del producto se mantienen reconocibles entre clientes. Los identificadores de modelos y rutas existentes no cambian por una diferencia de texto visible.

## Cambios implementados

| Área | Alineación visible y funcional en web |
| --- | --- |
| Barra lateral | Mismo orden de entradas principales y bibliotecas que móvil, secciones en mayúsculas, iconos y colores de entidades, conteos de las cuatro bibliotecas, ficha con peso y panel fijo de créditos. Se quitaron accesos rápidos de creación, perfil duplicado y la sección administrativa del menú. La administración web sigue accesible para staff desde Mi cuenta. |
| Inicio | Semana navegable, saludo y plan del día, compromisos junto al plan, calendario mensual navegable, indicadores de planes y comidas, tendencia de peso y registro de peso. Se conservan las bibliotecas y el asistente accesibles desde la portada. |
| Mi calendario | Pestañas Planificación y Progreso, título fijo con la fecha local de hoy, mes navegable y acceso directo al detalle al tocar un día. Bajo el mes aparecen cinco indicadores y las acciones para añadir minuta o compromiso. La misma vista reúne Mis minutas programadas, Próximas minutas, Mis compromisos con filtros y lista mensual, y Semana actual. El progreso muestra los dos indicadores, tendencia de peso, registro de peso y edición de fecha de inicio. |
| Mi cuenta | Plan y créditos, información de acceso, edición de nombre de usuario mediante el mismo servicio de identidad que móvil, enlaces a fichas, suscripción, notificaciones, recordatorios del programa y soporte; salida y eliminación siguen disponibles. |
| Nombres transversales | Inicio, Mi calendario, Comparaciones, Compartidos, Fundamentos, Mis Programas, Mis Minutas, Mis Comidas, Mis Alimentos y Asistente Nutricional en navegación y recorridos principales. |

## Ampliación de Preparaciones y Suplementos en la web

La implementación se ordena por dependencias del dominio: primero lectura y permisos de biblioteca, luego edición de entidades reutilizables, después composición de Comidas y Minutas, y finalmente snapshots de días calendarizados. La web usa sesiones y formularios con CSRF; el móvil conserva su autenticación por token. Ambos clientes llaman los comandos del dominio que gobiernan versiones, totales y permisos.

| Área | Flujo web agregado |
| --- | --- |
| Preparaciones | Biblioteca de Preparaciones curadas y personales, fichas con ingredientes y nutrientes de receta completa, creación de borrador personal, agregar/ajustar/quitar ingredientes, rendimiento, porción habitual y retiro. El acceso personal respeta el interruptor y el permiso Pro. |
| Comidas | Agregar, ajustar porciones o gramos y quitar Preparaciones propias o curadas. La edición recalcula los totales de la Comida y sus Minutas derivadas. |
| Suplementos | Biblioteca privada Pro, copia independiente desde el catálogo publicado, edición de ficha, componentes y nutrición declarada, tomas guardadas con varios suplementos y edición de composición. La información declarada no participa en los macros. |
| Minutas | Agregar tomas directas o desde una toma guardada, asignar hora, ajustar cantidades y retirar la instancia. Una Minuta con solo suplementos conserva su criterio de completitud del dominio. |
| Calendario | Día calendarizado muestra tomas y su estado; permite agregar una toma guardada y registrar completada, omitida o restablecida en el día vigente. El detalle de Comida separa Preparaciones de Alimentos y permite agregar, ajustar y quitar una Preparación del snapshot de ese día. |

La revisión local cubrió las vistas de escritorio y teléfono, incluyó corrección de desbordes y de valores decimales en formularios, y ejecutó pruebas de propiedad de datos, permisos, composición y ausencia de macros de suplementos. La disponibilidad final sigue condicionada por `SUPPLEMENTS_FEATURE_ENABLED` y `PERSONAL_PREPARATIONS_FEATURE_ENABLED`, desactivados por defecto.

## Diferencias funcionales aún reales

Estas capacidades móviles todavía necesitan trabajo propio; esta ampliación no declara paridad total:

1. **Digitalizar etiqueta nutricional:** móvil combina cámara o galería, OCR local, análisis con créditos, revisión editable y confirmación. La web aún no tiene adquisición, revisión y confirmación por archivo o cámara del navegador. El contrato y el servicio están en `mobile_api/routes/label_capture.py` y `notas/application/services/nutrition_label_ai.py`.
2. **Revisión periódica y ajustes de programa:** el móvil presenta propuestas pendientes y decisiones prospectivas. La web conserva la gestión y el historial del programa, pero no esa revisión completa en Inicio. Fuente: `mobile/src/app/today.tsx`, `mobile_api/routes/calendarization.py` y los comandos de revisión.
3. **Recordatorios:** la web configura push del programa y muestra notificaciones; el móvil también ofrece ajustes de recordatorios nativos. La cuenta web enlaza a los controles que existen, sin representar una configuración inexistente como si fuera equivalente.
4. **Plan fijado y creación inmediata del plan de hoy:** el móvil puede trabajar con una minuta fijada o crear una para la fecha desde Inicio. La web ofrece asignación desde Mi calendario, pero no reproduce todos los controles de edición en la portada.

Las diferencias anteriores necesitan trabajo funcional propio. La revisión visual de esta rama debe valorar la alineación implementada y priorizar estas capacidades antes de afirmar paridad total.
