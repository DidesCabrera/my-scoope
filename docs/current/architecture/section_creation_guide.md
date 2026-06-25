# Section Creation Guide

Esta guía define cómo crear una nueva sección en My Scoope respetando la arquitectura actual.

## Objetivo

Toda sección nueva debe parecer escrita por el mismo sistema. Eso significa respetar capas, navegación, viewmodels, acciones, templates, CSS y tests.

## Pasos recomendados

### 1. Definir el tipo de sección

Identificar si la sección será:

- lista;
- detail;
- formulario;
- selector/picker;
- comparador;
- inbox/flujo de recepción;
- dashboard;
- feature interna sin UI.

### 2. Crear rutas en `interface/urls/`

Las rutas deben vivir en:

```text
notas/interface/urls/<feature>.py
```

El agregador principal debe mantenerse liviano.

### 3. Crear views delgadas

Las views viven en:

```text
notas/interface/views/<feature>.py
```

Las views deben:

- leer request;
- aplicar permisos/decorators;
- llamar commands para escrituras;
- llamar page builders/viewmodels para lectura;
- renderizar o redirigir.

Las views no deben concentrar cálculo nutricional, armado visual complejo ni reglas de negocio reutilizables.

### 4. Crear commands para escrituras

Si la sección crea, actualiza, elimina, guarda, renombra o comparte entidades, crear commands en:

```text
notas/application/services/commands/
```

Los commands no deben importar `presentation` ni `interface`.

### 5. Crear services para lógica reusable

Si hay parsing, cálculo, snapshots, normalización o validación reusable, crear services en:

```text
notas/application/services/<feature>/
```

### 6. Crear viewmodels para UI compleja

Si el template requiere datos compuestos, crear viewmodels en:

```text
notas/presentation/viewmodels/
```

Los viewmodels deben preparar datos listos para templates sin ejecutar writes.

### 7. Crear actions/header actions en `presentation/actions/`

Si una entidad necesita acciones globales o de card, resolverlas en:

```text
notas/presentation/actions/
```

No volver a ubicar action resolvers en `application`.

### 8. Registrar navegación

Si la sección aparece en sidebar/header, registrar en:

```text
notas/presentation/navigation/app_registry.py
```

### 9. Reutilizar patrones visuales existentes

Antes de crear CSS nuevo, revisar:

- `list-page-header`;
- `card-title-comp`;
- `structural-indicator`;
- `data-grid-edit-actions`;
- `child-card`;
- tabs existentes;
- botones existentes.

### 10. Agregar tests mínimos

Agregar tests cuando haya:

- payload parsing;
- commands;
- snapshots;
- rutas críticas;
- reglas de permisos;
- add/remove/reorder;
- regresiones ya detectadas.

## Regla final

Si una sección nueva necesita mucho CSS, muchas condiciones en templates o una view muy grande, probablemente falta extraer lógica a services/viewmodels/actions.
