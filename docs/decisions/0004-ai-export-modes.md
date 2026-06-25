# 0004 - AI Export Modes

Status: accepted

## Context

El proyecto se comparte frecuentemente con IA mediante ZIPs. Incluir todos los archivos genera ruido, consume contexto y puede afectar la calidad de análisis.

## Decision

Se mantienen tres modos de exportación:

```bash
./scripts/export_for_chatgpt.sh ai
./scripts/export_for_chatgpt.sh full
./scripts/export_for_chatgpt.sh usda
```

- `ai`: uso normal, excluye tests, USDA e imágenes.
- `full`: mantiene tests, excluye USDA e imágenes.
- `usda`: incluye USDA y tests, excluye imágenes.

`manual_docs/` debe excluirse de exports porque no es documentación oficial del proyecto.

## Consequences

- Para cambios de arquitectura o tests, usar `full`.
- Para UI/refactors normales, usar `ai`.
- Para importadores USDA, usar `usda`.
