# Comparators

Status: current
Date: 2026-10-28
Audience: developers and AI assistants

## Estado

Feature vigente.

## Tipos soportados

- Foods
- Meals
- DailyPlans

Programs queda fuera por decisión actual.

## Conceptos

### Comparación dinámica

La vista normal permite seleccionar múltiples entidades y comparar métricas.

Foods usan cantidad en su unidad operativa configurada, `g` o `ml`, con 100 unidades
como fallback de presentación cuando corresponde.

La selección es posicional: comienza con dos slots, permite agregar o quitar
posiciones y admite repetir una entidad. Esto permite, por ejemplo, comparar 100 g
contra 200 g del mismo alimento.

Meals y DailyPlans no usan cantidad, pero incluyen PPK cuando corresponde.

Los resultados se agrupan por métrica, no por entidad. Cada bloque muestra todas
las selecciones con valores y barras relativas al máximo del bloque, en el orden:
calorías, PPK cuando corresponde, proteínas, carbohidratos, grasas y P/C/F %.

### Comparación guardada

Las comparaciones guardadas usan dos estructuras:

- `payload`: IDs/cantidades editables.
- `snapshot_payload`: valores y nombres calculados al guardar.

El detail de una comparación guardada inicia en modo lectura. Al presionar editar, reaparecen selectores y acciones de edición.

La comparación guardada puede compartirse mediante el sistema normalizado de
`ShareResource`. El receptor previsualiza el snapshot, reclama el recurso de forma
explícita y al guardar obtiene una `SavedComparison` propia. Cambios posteriores en
la comparación original no reescriben la copia compartida.

Web, móvil y AI Assistant deben reutilizar las mismas proyecciones canónicas de
biblioteca y resultados. Paginación parcial no equivale al total de entidades.

## Ubicación de lógica

```text
notas/application/services/comparisons/
notas/application/services/commands/saved_comparison_commands.py
notas/presentation/viewmodels/comparators.py
notas/interface/views/comparators.py
```

## Reglas

- La view debe orquestar, no calcular todo inline.
- El parsing de payload vive en services.
- El snapshot vive en services.
- Las escrituras viven en commands.
- El template debe consumir viewmodels preparados.
- Sharing debe consumir `snapshot_payload`; nunca reconstruir un preview público
  leyendo objetos privados del emisor.
