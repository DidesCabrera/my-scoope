# AI Assistant: paridad, seguridad y operación

Status: human_reference
Date: 2026-07-23
Audience: usuarios staff humanos de producto, operaciones, soporte y desarrollo
Role: human_reference
Authority: non_authoritative
Update-Policy: explicit_user_request_only

> Orientación exclusiva para personas. No define contratos del AI Assistant, no forma parte del
> contexto normativo de Codex y no se sincroniza automáticamente con ciclos o features.

## Objetivo operativo

El AI Assistant puede asistir todas las áreas actuales del producto sin convertirse en una vía de
escritura libre. El lenguaje natural interpreta la intención; My Scoope conserva la autoridad sobre
identidad, permisos, cálculos, validación, preview, persistencia, auditoría y resultado final.

```text
solicitud del usuario
  -> resolución segura de la entidad
  -> catálogo canónico de capacidades
  -> lectura, propuesta o acción preparada
  -> revisión explícita del usuario
  -> comando acotado
  -> verificación del resultado
```

## Fuente única de capacidades

El catálogo ejecutable vive en `ai_assistant.application.tools.registry`. El chat y MCP proyectan
sus contratos desde esa fuente; no mantienen definiciones paralelas. El mapa
`ai_assistant.domain.capabilities` clasifica cada funcionalidad humana como lectura autónoma,
propuesta revisable, acción preparada, handoff a UI confiable o staff-only.

Analytics, Operations y Knowledge permanecen en superficies staff separadas. No se incorporan a la
identidad ni a las tools del usuario final.

## Qué puede hacer por área

| Área | Lectura | Cambios |
| --- | --- | --- |
| Ficha | Consultar contexto nutricional autorizado. | Preparar y confirmar cambios de ficha. |
| Alimentos y comidas | Listar, buscar y leer objetos visibles. | Acciones básicas preparadas; composición/import/share continúan en UI especializada. |
| Planes diarios | Resolver por nombre y leer estructura completa. | Crear propuestas nutricionales o acciones preparadas según el cambio. |
| Programas | Listar y consultar semanas y días. | Acciones básicas preparadas; composición y sharing siguen en UI confiable. |
| Calendario | Consultar estado e historial. | Pausar, reanudar o cancelar mediante preview; activación y preferencias siguen en UI. |
| Propuestas | Listar y leer estado y validación. | Aprobar, rechazar, cancelar, eliminar o aplicar con confirmación. |
| Comparaciones e Inbox | Consultar objetos visibles. | Las composiciones y workflows especializados conservan sus pantallas. |
| Cuenta y billing | Consultar plan, créditos, suscripción, pagos y documentos. | Checkout y cancelación permanecen en la superficie de billing. |

## Ajustar calorías manteniendo alimentos

La solicitud “aumenta este plan en 200 calorías manteniendo los mismos alimentos y variando las
cantidades” está cubierta por una propuesta revisable:

1. resolver un DailyPlan propio, sin adivinar el ID;
2. leer su total y sus comidas snapshot;
3. calcular un factor proporcional para el nuevo objetivo;
4. proponer una actualización por cada `MealFood` del snapshot;
5. conservar alimentos y estructura de comidas;
6. mostrar el antes/después;
7. cambiar el plan únicamente después de aprobar y aplicar la propuesta.

Las Meals dentro de un DailyPlan son snapshots independientes. Cambiar sus cantidades no modifica
la Meal reutilizable de la biblioteca. Si el plan no es propio, no tiene calorías escalables o el
objetivo no es válido, no se crea una propuesta engañosa.

## Acciones preparadas

`AIPreparedAction` cubre mutaciones generales compatibles con preview. Preparar una acción guarda
únicamente intención, antes/después, expiración y huella del objetivo. El proveedor no puede llamar
el commit. La confirmación ocurre en una acción UI autenticada y protegida; el commit vuelve a
validar ownership y versión, rechaza acciones vencidas, repetidas o stale y verifica el resultado.

## Handoffs intencionales

No todo debe ejecutarse dentro del chat. Composición especializada, imports, sharing, activación de
calendario, checkout, cancelación de suscripción y operaciones staff conservan controles dedicados.
El Assistant puede explicar el siguiente paso y llevar al usuario a la superficie confiable, pero no
simula una mutación que no ocurrió.

## Activación y diagnóstico

La paridad implementada no elimina los gates de rollout. Un ambiente que use LLM y propuestas
revisables debe habilitarlos explícitamente:

```text
AI_ASSISTANT_CHAT_ENGINE_MODE=llm_preview
AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS=true
```

Si una solicitud falla, revisar en orden: resolución de entidad, ownership/visibilidad, selección de
capacidad, executor, validación del servicio de aplicación, estado de propuesta/acción preparada y
gate del ambiente. Nunca corregir un problema de permisos abriendo una tool más amplia.

## Dónde verificar el comportamiento real

Ante dudas o diferencias, consultar directamente el código, sus tests y la documentación normativa
aplicable. Esta guía es explicativa y no debe utilizarse para implementar o modificar features.
