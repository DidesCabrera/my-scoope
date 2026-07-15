# 0004 - AI Export Modes

Status: accepted

## Context

El proyecto se comparte frecuentemente con IA mediante ZIPs. Incluir todos los archivos genera ruido, consume contexto y puede afectar la calidad de análisis.

## Decision

Se mantienen modos de exportación especializados:

```bash
./scripts/export_for_chatgpt.sh ai
./scripts/export_for_chatgpt.sh full
./scripts/export_for_chatgpt.sh usda
./scripts/export_for_chatgpt.sh foodcatalog
./scripts/export_for_chatgpt.sh planning
```

- `ai`: uso normal, excluye tests, USDA e imágenes.
- `full`: mantiene tests, excluye USDA e imágenes.
- `usda`: incluye USDA y tests, excluye imágenes.
- `foodcatalog`: export focalizado para Food Catalog App, documentación y tests relacionados.
- `planning`: export focalizado para documentación oficial, decisiones y planificación futura.

`manual_docs/` debe excluirse de exports porque no es documentación oficial del proyecto.

## Consequences

- Para cambios de arquitectura o tests, usar `full`.
- Para UI/refactors normales, usar `ai`.
- Para importadores USDA, usar `usda`.
- Para Food Catalog App, usar `foodcatalog`.
- Para planificar próximos ciclos con IA, usar `planning`.
