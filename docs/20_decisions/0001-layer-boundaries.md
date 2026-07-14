# 0001 - Layer Boundaries

Status: accepted

## Context

My Scoope creció con varias secciones complejas. Para mantener el código comprensible, se definieron límites entre `domain`, `application`, `presentation` e `interface`.

## Decision

La dirección de dependencias vigente es:

```text
interface -> presentation/application -> domain
presentation -> application/domain
application -> domain
```

`application` no debe importar `presentation` ni `interface`.

Los page builders y action resolvers de UI pertenecen a `presentation`, no a `application`.

## Consequences

- Las views deben quedar delgadas.
- Las escrituras deben vivir en commands.
- Los datos UI-ready deben vivir en presentation.
- Los tests de arquitectura deben proteger estas fronteras.
