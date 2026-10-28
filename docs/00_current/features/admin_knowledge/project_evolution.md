# Evolución de My Scoope: julio a octubre de 2026

Status: human_reference
Date: 2026-10-28
Audience: usuarios staff humanos de producto, operaciones, soporte y desarrollo
Role: human_reference
Authority: non_authoritative
Update-Policy: explicit_user_request_only

> Recapitulación humana contrastada con el historial de commits, el código, las pruebas y los
> documentos vigentes. No sustituye los contratos actuales ni implica que toda idea explorada
> haya sido implementada.

## Cambio principal

My Scoope pasó de ser principalmente una biblioteca web de entidades nutricionales a una experiencia
consumer-first que conecta creación, planificación, ejecución diaria y aprendizaje:

```text
biblioteca y ficha personal
  -> asistencia o construcción de una propuesta
  -> revisión explícita
  -> plan o programa propio
  -> calendario con fechas reales
  -> ejecución y registros
  -> progreso, revisión y ajustes futuros
```

## Línea de evolución

| Periodo | Evolución visible |
| --- | --- |
| Julio | Se consolidaron las fronteras de AI Assistant, Food Catalog y Nutrition Solver, con capacidades versionadas, propuestas revisables y operación staff. |
| Agosto | Nació el cliente móvil consumer-first, la calendarización ejecutable, captura de etiquetas, suscripciones móviles, recordatorios y una gramática visual compartida. |
| Septiembre | Sharing migró a snapshots portables; Chats y Propuestas se unificaron visualmente; el Assistant amplió memoria y acciones; el Solver avanzó hacia programas culinarios y alternativas. |
| Octubre | Se refinó onboarding, bibliotecas, nutrición extendida, unidades y comparaciones; se endureció billing Apple/Google; Calendario pasó a ser la columna de planificación; la beta ganó observabilidad y correcciones guiadas por evidencia. |

## Mapa mental actual

| Concepto | Significado humano |
| --- | --- |
| Biblioteca | Lugar de entidades reutilizables propias: alimentos, comidas, planes y programas. |
| Propuesta | Resultado pendiente que puede revisarse sin alterar todavía la biblioteca. |
| Programa | Plantilla semanal reutilizable, todavía sin fechas reales. |
| Calendario | Autoridad de lo planificado y vivido en fechas concretas. |
| Snapshot | Copia estable que protege historia, sharing y ejecución frente a cambios posteriores. |
| Food Catalog | Maestro curado; no es la misma capa que los alimentos operativos o privados. |
| Assistant | Operador conversacional acotado; propone y prepara, pero My Scoope valida y persiste. |
| Billing | Evidencia de proveedores externos proyectada a los beneficios comerciales de la cuenta. |

## Decisiones que explican muchas dudas

- Editar una plantilla no reescribe automáticamente días ya calendarizados.
- Una comida o plan incluido en otra entidad puede ser una copia independiente, no un duplicado
  accidental de biblioteca.
- Compartir expone un snapshot; guardar crea una copia propiedad del receptor.
- Capturar una etiqueta crea un alimento privado confirmado, no modifica el catálogo maestro.
- El Assistant puede mostrar o preparar una acción sin que eso signifique que ya fue aplicada.
- El proveedor de pago informa evidencia; la cuenta de My Scoope conserva la autoridad de acceso.
- Una conversación de Codex ayuda a descubrir intención y problemas, pero solo código, pruebas,
  decisiones aceptadas y documentación vigente confirman el comportamiento implementado.

## Cómo usar esta recapitulación

Usar esta página como puerta de entrada. Para operación diaria, continuar con las guías específicas
del Knowledge Center. Para implementar, diagnosticar un contrato o decidir permisos, salir de este
centro y consultar las fuentes normativas aplicables.

## Referencias internas

- [Calendario, planificación y progreso](calendar_and_progress.md)
- [Recorrido móvil](mobile_journey.md)
- [AI Assistant](ai_assistant.md)
- [Food Catalog](food_catalog.md)
- [Nutrition Solver](nutrition_solver.md)
- [Compartir y comparar](sharing_and_comparisons.md)
- [Pagos y salud de la beta](billing_and_beta.md)
