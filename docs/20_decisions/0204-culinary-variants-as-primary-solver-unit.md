# 0204 — Variantes culinarias como unidad primaria del Solver

Status: accepted
Date: 2026-10-07

## Contexto

El optimizador de planes diarios podía seleccionar alimentos individuales por rol y
ajustar sus porciones. Esa estrategia satisface gramática nutricional y objetivos de
macros, pero no demuestra que los alimentos formen una comida reconocible, preparable
y culturalmente coherente.

El generador de programas con especificación semanal ya dispone de una frontera más
segura: `CulinaryTemplate` y `CulinaryVariant` representan combinaciones persistidas,
preparación, sustituciones acotadas, rangos de porción, proporciones y evidencia de
validación. Mantener una estrategia distinta para comidas y planes diarios duplicaba
criterios y dejaba la coherencia culinaria fuera del contrato principal.

Una comida tampoco es una bolsa plana de alimentos. Puede contener fondo, ensalada y
postre. Por ejemplo, pollo, arroz y naranja es una composición válida cuando la naranja
ocupa el curso `dessert`; no necesita una afinidad directa con el pollo.

## Decisión

La unidad primaria de generación será una variante culinaria validada:

```text
catálogo culinario validado
    -> selección por tipo de comida y familia
    -> conservación de componentes/cursos/preparación/proporciones
    -> ajuste de porciones dentro de límites autorizados
    -> validación nutricional diaria
    -> propuesta revisable
```

- Comidas, planes diarios y programas comparten `CulinaryVariant` como catálogo de
  candidatos preferente.
- El Solver puede elegir una variante y ajustar las cantidades de sus ingredientes;
  no puede añadir libremente alimentos fuera de la variante durante ese camino.
- Los componentes distinguen `main`, `side`, `salad`, `dessert` y `beverage`. La
  afinidad se interpreta dentro de la estructura de la comida, no entre todos los
  alimentos como si pertenecieran a un único plato.
- Las restricciones alimentarias se aplican antes de habilitar una variante. La falta
  de evidencia sobre alérgenos continúa fallando de forma segura.
- La propuesta conserva identificador de variante, digest de evidencia, nivel de
  validación, componentes y porciones. Esa evidencia se recalcula antes de aplicar.
- `NutritionProposal` continúa siendo la frontera de revisión humana; generar nunca
  crea directamente una entidad final.
- La composición desde alimentos individuales queda como fallback explícito y
  observable mientras madura el catálogo. No puede presentarse como resultado
  culinario ni ocultar la razón del fallback.

## Cursos y afinidad

La afinidad se evalúa en tres niveles:

1. ingrediente dentro de un componente;
2. componente dentro de una variante culinaria;
3. variante respecto del tipo de comida y del resto del día o semana.

Una fruta puede formar parte del postre de una comida principal aunque no combine
directamente con su proteína. Las reglas de proporción sólo vinculan componentes que
realmente deben mantener una relación culinaria.

## Catálogo y activación

La disponibilidad técnica mínima es tener al menos una variante válida para cada tipo
de comida solicitado. Eso permite usar el camino culinario, pero no basta para retirar
el fallback.

Antes de configurar `NUTRITION_CULINARY_RAW_FALLBACK_ENABLED=false` en producción se
requiere, como gate operativo:

- cobertura de `breakfast`, `main`, `snack` y `dinner`;
- al menos tres familias para desayuno/snack y cuatro para fondo/cena;
- al menos doce variantes vigentes por tipo de comida;
- al menos una variante revisada por una persona en cada familia activa;
- cobertura de patrones alimentarios y alérgenos soportados;
- smoke de comida, plan diario, onboarding y programa sin fallback;
- métricas de inviabilidad y fallback revisadas en staging.

El starter v2 amplía las familias base y representa explícitamente ensalada y postre,
incluida naranja cuando está disponible en el catálogo operacional. Sigue siendo un
bootstrap validado por reglas, no reemplaza la curación humana requerida por el gate.

## Consecuencias

- Los resultados son explicables como comidas conocidas, no sólo como soluciones de
  macros.
- Las porciones pueden cambiar sin destruir la identidad culinaria.
- Comida, plan diario y programa comparten una autoridad y evidencia común.
- El catálogo culinario pasa a ser una dependencia operacional de primera clase.
- Un catálogo insuficiente reduce variedad o provoca fallback explícito; nunca debe
  provocar que una composición libre se etiquete como variante validada.
- Cambiar alimentos, preparación, límites o reglas invalida el digest y bloquea la
  aplicación de propuestas ya revisadas.

## Alternativas descartadas

| Alternativa | Motivo de descarte |
|---|---|
| Optimizar siempre desde alimentos individuales | Cubre roles y macros, pero no garantiza preparación ni coherencia culinaria. |
| Mantener el enfoque culinario sólo para programas | Produce diferencias de calidad entre una comida, un día y una semana. |
| Exigir afinidad entre todos los alimentos | Rechaza falsamente cursos legítimos, como una fruta de postre. |
| Guardar todas las combinaciones posibles | Explosión combinatoria; se prefieren plantillas, variantes canónicas y sustituciones acotadas. |
| Desactivar inmediatamente todo fallback | El catálogo actual aún debe demostrar cobertura robusta en staging y revisión humana por familia. |

## Referencias

- `docs/10_active_cycles/culinary_first_solver_cycle.md`
- `notas/application/culinary_library.py`
- `notas/application/culinary_starter.py`
- `nutrition_solver/application/culinary_day_planner.py`
- `notas/application/ai_intake/culinary_dailyplan.py`
