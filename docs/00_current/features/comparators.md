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
