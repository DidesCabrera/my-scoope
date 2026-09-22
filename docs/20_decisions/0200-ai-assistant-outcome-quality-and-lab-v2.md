# 0200 — AI Assistant outcome quality and Lab v2

Status: accepted repository contract
Date: 2026-09-21

## Decision

My Scoope evaluará el asistente como un sistema que alcanza outcomes mediante
capabilities controladas, no como un chatbot evaluado sólo por estilo o por un pase
técnico global.

La arquitectura conserva native function calling, schemas estrictos, ownership,
propuestas/patches revisables y confirmación confiable. Sobre esa base se incorporan:

- un núcleo compacto con capacidades adicionales seleccionadas por outcome o referencia
  explícita (memoria, lectura, cards y patch);
- `active_work.v1` como continuidad informativa, sin autoridad implícita;
- `ai_assistant_prompt.v4` con reglas de consulta/cambio y condición de parada;
- `ai_assistant.evaluation_lab.v2` con dataset, outcomes, repeticiones y dimensiones;
- revisión humana explícita: la ausencia de anotación es pendiente, no aprobada;
- feedback de producto agregado, sin copiar contenido a reportes;
- selección de modelo posterior al gate funcional y cualitativo.

El runtime permite hasta seis continuaciones de tools por turno. Este valor no
obliga a ejecutar seis operaciones: es un techo para solicitudes compuestas que
deben leer memoria, capturar distintos drafts y cerrar con una respuesta. Cada
continuación reduce el contexto y expone sólo la capability pendiente, manteniendo
el límite de input y la condición de parada.

La decisión sigue las prácticas oficiales de evaluación task-specific, calibración
humana, evaluación de selección/argumentos de tools y grading de trayectorias:

- <https://developers.openai.com/api/docs/guides/evaluation-best-practices>
- <https://developers.openai.com/api/docs/guides/function-calling>
- <https://developers.openai.com/api/docs/guides/trace-grading>

## Consequences

- Un escenario sólo pasa cuando completa su outcome y respeta sus límites.
- Una corrida automatizada sana queda `awaiting_quality_review` hasta ser anotada.
- Un candidato sólo se acepta si pasan todas sus repeticiones y revisión humana.
- Luna permanece baseline; Terra es escalamiento; Sol es benchmark opcional.
- Astra no es dependencia ni candidato de este ciclo.
- Las consultas no usan Workspace Patch. Las mutaciones usan patch revisable y el
  commit continúa reservado a una acción explícita en UI confiable.
- Una referencia ambigua no hereda `blocking_fields` de nutrición: exige una
  aclaración breve y no puede inventar un plan activo.
- La captura de hechos pendientes ocurre antes de compartir cards, para que una
  presentación opcional no consuma el presupuesto de una operación necesaria.
- Si el proveedor falla al redactar la respuesta final después de completar el
  outcome, el runtime intenta una sola redacción compacta, sin tools ni nuevos
  efectos. Si también falla, conserva el acuse local seguro y registra la
  degradación.

## Rejected alternatives

- Aprobar calidad por ausencia de fallos técnicos.
- Usar un único score promedio que oculte una regresión grave.
- Ampliar indiscriminadamente el tool set en cada turno.
- Corregir repetición mediante plantillas rígidas de respuesta.
- Escalar de modelo antes de medir el sistema y el baseline.
