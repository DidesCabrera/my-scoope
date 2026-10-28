# Calendario, planificación y progreso

Status: human_reference
Date: 2026-10-28
Audience: usuarios staff humanos de producto, operaciones, soporte y desarrollo
Role: human_reference
Authority: non_authoritative
Update-Policy: explicit_user_request_only

> Guía explicativa para personas. El comportamiento real debe verificarse en los contratos y pruebas
> vigentes de calendarización.

## Qué cambió

Calendario reemplaza conceptualmente a “Mi programa activo” como centro de planificación. Un programa
sigue siendo una plantilla útil, pero el usuario organiza su vida mediante fechas concretas, incluso
cuando mezcla días provenientes de un programa con planes agregados manualmente.

## Tres capas distintas

| Capa | Qué representa | Qué ocurre al editar el origen |
| --- | --- | --- |
| Programa | Plantilla relativa de semanas y días. | Cambia la plantilla; no reescribe lo ya vivido. |
| Plan fechado | Snapshot asignado a una fecha concreta. | Conserva su contenido e historial propio. |
| Ejecución | Evidencia de comidas completadas, omitidas o corregidas. | Es acumulativa y no debe borrarse al editar una plantilla. |

## Planificación

La vista mensual permite reconocer días con y sin plan, ver cuántos planes están programados desde
hoy y hasta qué fecha llega el horizonte. Un día futuro puede recibir un plan de la biblioteca,
moverse, reordenarse o reemplazarse con confirmación. Las fechas pasadas y las fechas presentes con evidencia protegen la historia.

El calendario también registra compromisos de compra, cocina, entrenamiento y citas nutricionistas. Una compra puede usar
un periodo de alimentación para agrupar los alimentos requeridos por los planes de esas fechas. La
lista guardada es evidencia del momento en que se creó; no cambia silenciosamente si luego se edita
un plan.

## Progreso

La pestaña de progreso resume únicamente días que realmente tienen un plan. Distingue comidas
planificadas, transcurridas, completadas y omitidas, y calcula adherencia dentro de un periodo
explícito. Reiniciar un periodo abre una nueva ventana de medición sin borrar la evidencia previa.

Peso, energía, hambre, rendimiento y notas pueden aportar contexto a una revisión. Una revisión puede
preparar cambios futuros, pero nunca debería reescribir días pasados ni aplicar una modificación sin
decisión explícita.

## Diagnóstico humano

| Síntoma | Pregunta inicial |
| --- | --- |
| “El programa cambió pero el calendario no” | ¿Se editó la plantilla después de crear los snapshots fechados? |
| “Aparecieron muchas comidas” | ¿Son entidades de biblioteca o copias contenidas en días calendarizados? |
| “La adherencia parece baja” | ¿Qué periodo está activo y cuántas comidas ya habían transcurrido? |
| “El día no muestra cambios” | ¿Se editó el origen o se reemplazó explícitamente el plan de esa fecha? |
| “La lista de compra quedó antigua” | ¿Fue guardada antes de modificar los planes del periodo? |
| “Recibí dos recordatorios” | Verificar canal nativo/local y reconciliación de eventos del dispositivo. |

## Regla operativa

Calendario responde “qué estaba planificado para esta fecha y qué ocurrió”. Biblioteca y Programa
responden “qué plantilla reutilizable tengo”. Confundir ambas preguntas suele producir la impresión
de duplicados, pérdida de cambios o métricas incorrectas.

## Referencias

- [Evolución del producto](project_evolution.md)
- [Recorrido móvil](mobile_journey.md)
