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
  archive/
```

### `docs/current/`

Contiene documentación vigente. Es la fuente de verdad para implementar nuevas secciones, corregir arquitectura y mantener consistencia UI/UX.

### `docs/decisions/`

Contiene decisiones arquitectónicas e históricas importantes. Estos documentos explican por qué el sistema llegó a su forma actual.

### `docs/archive/`

Contiene documentación antigua, bitácoras, pruebas, contexto histórico y documentos superados. No debe guiar implementaciones nuevas.

## `manual_docs/`

Existe una carpeta `manual_docs/` en la raíz del proyecto para notas personales del desarrollador humano.

Esa carpeta **no forma parte de la documentación oficial del proyecto** y no debe ser considerada por una IA como fuente útil para implementar, refactorizar o auditar My Scoope.

Las exportaciones para IA deben excluir `manual_docs/`.

## Roadmaps

Los roadmaps fueron eliminados de `docs/` porque pertenecen a otro contexto de planificación. Esta documentación debe concentrarse en:

- axiomas actuales del sistema;
- contratos de arquitectura;
- patrones UI vigentes;
- decisiones ya tomadas;
- historia técnica relevante.

## Cómo usar esta documentación

Antes de agregar una sección nueva:

1. Leer `docs/current/architecture/layers.md`.
2. Leer `docs/current/architecture/rules.md`.
3. Leer `docs/current/architecture/section_creation_guide.md`.
4. Revisar `docs/current/architecture/ui_patterns.md`.
5. Revisar si existe una doc de feature similar en `docs/current/features/`.
6. Agregar o actualizar tests cuando la sección incorpore lógica reusable.
