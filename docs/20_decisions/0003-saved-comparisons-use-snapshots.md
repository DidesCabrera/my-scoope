# 0003 - Saved Comparisons Use Snapshots

Status: accepted

## Context

Las comparaciones guardadas deben poder revisarse posteriormente, incluso si los alimentos, comidas o planes originales cambian.

## Decision

`SavedComparison` usa dos estructuras:

- `payload`: IDs y cantidades editables.
- `snapshot_payload`: nombres y valores nutricionales calculados al momento de guardar.

## Consequences

- Una comparación guardada conserva su lectura histórica.
- Al editar y guardar cambios, se regenera el snapshot.
- Si una entidad original cambia o desaparece, el snapshot sigue permitiendo entender la comparación guardada.
