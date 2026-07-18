# My Scoope Docs

La carpeta `docs/` es una parte crítica de la salud del proyecto. Su objetivo no es solo registrar información: debe funcionar como una **arquitectura de conocimiento** para construir, refactorizar y extender My Scoope de forma consistente.

La documentación oficial no debe crecer como un archivo plano. Debe ordenar la atención de humanos e IA: primero lo vigente, luego los ciclos, después las decisiones, manuales, notas técnicas y finalmente el archivo histórico.

## Regla principal

Para crear o modificar código, una persona o una IA debe leer primero:

```text
docs/00_current/AI_README.md
docs/00_current/PROJECT_STATE.md
docs/00_current/
docs/20_decisions/
```

Si `PROJECT_STATE.md` aún no existe en un export, usar `docs/00_current/README.md` como entrada secundaria.

Los documentos en `docs/90_archive/` son históricos. Pueden ayudar a entender contexto, pero **no deben usarse como patrón para código nuevo**.

## Estructura oficial

```text
docs/
  README.md
  00_current/
    AI_README.md
    PROJECT_STATE.md
    architecture/
    design/
    features/
  10_active_cycles/
  20_decisions/
  30_manuals/
  40_technical/
    operations/
    qa/
  90_archive/
```

## Jerarquía de atención

| Carpeta | Rol | Autoridad |
| --- | --- | --- |
| `00_current/` | Fuente vigente de arquitectura, producto, features y diseño | Alta |
| `10_active_cycles/` | Ciclos planificados, activos, pausados o completados | Media hasta implementación |
| `20_decisions/` | Decisiones aceptadas y memoria técnica | Alta para racionalidad histórica |
| `30_manuals/` | Manuales oficiales de uso u operación humana | Media/alta según alcance |
| `40_technical/` | Políticas operacionales, QA, CI, testing y exportaciones | Alta para operación técnica |
| `90_archive/` | Contexto histórico o superado | Baja |

## `docs/00_current/`

Contiene documentación vigente. Es la fuente de verdad para implementar nuevas secciones, corregir arquitectura y mantener consistencia UI/UX.

`docs/00_current/AI_README.md` es el punto de entrada recomendado para trabajo asistido por IA. Comienza con la bienvenida de Felipe Dides y establece que una AI es también clienta y usuaria actual de My Scoope: las herramientas y la documentación deben darle contexto y capacidades para ejercer buen juicio, no imponerle un camino rígido.

## `docs/10_active_cycles/`

Contiene planificación de ciclos futuros, activos, pausados, completados o superados. Es documentación oficial, pero no representa por sí misma un contrato vigente de implementación.

Un plan se vuelve contrato cuando sus resultados quedan reflejados en código, en `docs/00_current/` o en `docs/20_decisions/`.

## `docs/20_decisions/`

Contiene decisiones arquitectónicas e históricas importantes. Estos documentos explican por qué el sistema llegó a su forma actual.

## `docs/30_manuals/`

Contiene manuales oficiales para uso humano u operación estable del sistema. No debe confundirse con `manual_docs/`, que son notas personales fuera de la documentación oficial.

## `docs/40_technical/`

Contiene documentación técnica operacional, como exportaciones para IA, testing, CI, QA y políticas que no son necesariamente arquitectura de producto, pero sí afectan cómo se trabaja el sistema.

`docs/40_technical/operations/docs_information_architecture.md` define la jerarquía de atención documental y cómo evitar que la documentación crezca como ruido.

`docs/40_technical/operations/export_for_chatgpt.md` define qué modo de export usar según el tipo de trabajo, cómo evitar exports demasiado grandes y cómo mantener los ZIP alineados con la arquitectura vigente.

## `docs/90_archive/`

Contiene documentación antigua, bitácoras, pruebas, contexto histórico y documentos superados. No debe guiar implementaciones nuevas.

## `manual_docs/`

Existe una carpeta `manual_docs/` en la raíz del proyecto para notas personales del desarrollador humano.

Esa carpeta **no forma parte de la documentación oficial del proyecto** y no debe ser considerada por una IA como fuente útil para implementar, refactorizar o auditar My Scoope.

Las exportaciones para IA deben excluir `manual_docs/`.

## Cómo usar esta documentación

Antes de agregar una sección nueva:

1. Leer `docs/00_current/AI_README.md`.
2. Leer `docs/00_current/PROJECT_STATE.md` si está presente.
3. Leer `docs/00_current/architecture/layers.md`.
4. Leer `docs/00_current/architecture/rules.md`.
5. Leer `docs/00_current/architecture/section_creation_guide.md`.
6. Revisar `docs/00_current/architecture/ui_patterns.md`.
7. Revisar si existe una doc de feature similar en `docs/00_current/features/`.
8. Para AI Assistant / LLM externo, leer `docs/00_current/features/ai_assistant/README.md` antes de tocar chat, prompts, tools u orquestación.
9. Para ciclos futuros o proyectos próximos, revisar `docs/10_active_cycles/` y actualizar el plan correspondiente antes de generar patches.
10. Revisar `docs/40_technical/operations/testing_and_ci_policy.md` cuando el cambio toque CI, testing o staging.
11. Agregar o actualizar tests cuando la sección incorpore lógica reusable.

## Regla editorial

La documentación debe aportar valor por jerarquía, no por volumen.

Agregar o actualizar un documento solo cuando ayude a responder una de estas preguntas:

- ¿Qué es verdad hoy?
- ¿Qué ciclo está planificado o activo?
- ¿Qué decisión se aceptó y por qué?
- ¿Cómo se usa u opera el sistema?
- ¿Qué regla técnica evita errores futuros?
- ¿Qué contexto histórico explica una restricción actual?
