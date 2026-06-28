# Food Catalog

## Estado

Feature vigente con historia extensa archivada.

## Concepto

El catálogo de alimentos combina alimentos de usuario, alimentos globales, aliases, trazabilidad y datos nutricionales normalizados.

## Regla actual

La documentación histórica del catálogo está en:

```text
docs/archive/food_catalog_history/
```

Esa carpeta puede usarse para entender contexto, pero cualquier implementación nueva debe revisar primero el código actual y las reglas vigentes en `docs/current/`.

## Food Catalog App

Decisión vigente: Food Catalog debe evolucionar como una aplicación/sistema independiente dentro de MyScoope.

Su responsabilidad no es solo guardar registros `Food`, sino adquirir, investigar, normalizar, validar, deduplicar, versionar y publicar alimentos confiables para el resto del producto.

El core de Meals, DailyPlans, Programs, Comparators y Proposals no debe depender directamente de fuentes externas como USDA, FatSecret, Open Food Facts, tablas públicas, agentes de IA o planillas de marcas. Todas las fuentes deben entrar primero como candidatos y adaptarse a un contrato canónico interno antes de crear o actualizar alimentos publicados.

La relación correcta es:

```text
Food Catalog App
    produce alimentos canónicos, trazables y versionados

Nutrition Management App
    consume alimentos publicados para construir comidas, planes y programas
```

## Documentación vigente

- [Food Catalog App](food_catalog/food_catalog_app.md): decisión principal sobre Food Catalog como sistema propio separado del entorno de gestión nutricional.
- [Research FatSecret API](food_catalog/fatsecret_research.md): evaluación inicial de FatSecret como proveedor externo temporal/no canónico mientras no exista permiso explícito de persistencia y atribución aceptable.
