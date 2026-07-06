# My Scoope Docs

La carpeta `docs/` es una parte crítica de la salud del proyecto. Su objetivo no es solo registrar información: debe funcionar como la **fuente de verdad operacional** para construir, refactorizar y extender My Scoope de forma consistente.

En el largo plazo, esta sección debe actuar como el motor documental de la autoprogramación del sistema: los documentos vigentes deben contener los **axiomas** del proyecto, y las decisiones deben registrar las **migraciones/historia** del proceso.

## Regla principal

Para crear o modificar código, una persona o una IA debe leer primero:

```text
docs/current/
docs/decisions/
```

Los documentos en `docs/archive/` son históricos. Pueden ayudar a entender contexto, pero **no deben usarse como patrón para código nuevo**.

## Estructura

```text
docs/
  README.md
  current/
    architecture/
    features/
    operations/
    design/
  decisions/
  planning/
  archive/
```

### `docs/current/`

Contiene documentación vigente. Es la fuente de verdad para implementar nuevas secciones, corregir arquitectura y mantener consistencia UI/UX.

### `docs/decisions/`

Contiene decisiones arquitectónicas e históricas importantes. Estos documentos explican por qué el sistema llegó a su forma actual.

### `docs/planning/`

Contiene planificación de ciclos futuros o próximos proyectos. Es documentación oficial, pero no representa por sí misma un contrato vigente de implementación. Sirve para conservar contexto estratégico, ordenar prioridades y preparar ciclos de patches antes de mover decisiones estables a `docs/decisions/`.

### `docs/archive/`

Contiene documentación antigua, bitácoras, pruebas, contexto histórico y documentos superados. No debe guiar implementaciones nuevas.

## `manual_docs/`

Existe una carpeta `manual_docs/` en la raíz del proyecto para notas personales del desarrollador humano.

Esa carpeta **no forma parte de la documentación oficial del proyecto** y no debe ser considerada por una IA como fuente útil para implementar, refactorizar o auditar My Scoope.

Las exportaciones para IA deben excluir `manual_docs/`.

## Planificación

Los planes futuros viven en `docs/planning/`. Deben entenderse como planificación oficial, pero no como contrato vigente de implementación hasta que se traduzcan en cambios de `docs/current/`, decisiones aceptadas o código.

La documentación vigente debe seguir concentrándose en:

- axiomas actuales del sistema;
- contratos de arquitectura;
- patrones UI vigentes;
- decisiones ya tomadas;
- historia técnica relevante;
- planes próximos cuando ayuden a orientar ciclos de patches.

## Cómo usar esta documentación

Antes de agregar una sección nueva:

1. Leer `docs/current/architecture/layers.md`.
2. Leer `docs/current/architecture/rules.md`.
3. Leer `docs/current/architecture/section_creation_guide.md`.
4. Revisar `docs/current/architecture/ui_patterns.md`.
5. Revisar si existe una doc de feature similar en `docs/current/features/`.
6. Para AI Assistant / LLM externo, leer `docs/current/features/ai_assistant/README.md` antes de tocar chat, prompts, tools u orquestación.
7. Para ciclos futuros o proyectos próximos, revisar `docs/planning/` y actualizar el plan correspondiente antes de generar patches.
8. Agregar o actualizar tests cuando la sección incorpore lógica reusable.
