# Comparators

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

Foods usan cantidad en gramos.

Meals y DailyPlans no usan cantidad, pero incluyen PPK cuando corresponde.

### Comparación guardada

Las comparaciones guardadas usan dos estructuras:

- `payload`: IDs/cantidades editables.
- `snapshot_payload`: valores y nombres calculados al guardar.

El detail de una comparación guardada inicia en modo lectura. Al presionar editar, reaparecen selectores y acciones de edición.

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
