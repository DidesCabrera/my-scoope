# PPK00–PPK06 · PPK and macro coherence cycle

Status: implemented in repository
Date: 2026-09-17

## Objective

Convertir PPK, calorías y distribución de macros en un solo objetivo coherente y
auditable, evitando que el asistente o el solver completen contradicciones de forma
silenciosa.

## Stages

### PPK00 — Baseline audit — completed

- Confirmó que pérdida de grasa y aumento muscular ya compartían 1,8 g/kg por defecto.
- Identificó que la captura no representaba PPK ni porcentajes como datos tipados.
- Separó objetivo diario, objetivo de una comida y futura periodización deportiva.

### PPK01 — Canonical policy — completed

- Centralizó la conversión kcal↔gramos y el cálculo de distribuciones.
- Definió 1,6–2,2 g/kg como preferente y 1,0–2,5 g/kg como ampliado.
- Acotó grasa diaria y asignó a carbohidratos la energía restante.

### PPK02 — Typed assistant capture — completed

- Añadió `protein_per_kg_target` y `macro_distribution` al brief, memoria y schemas.
- Preservó esos campos desde las tools hasta la propuesta revisable.

### PPK03 — Daily target integration — completed

- Reemplazó cálculos dispersos del estimador por la política común.
- Conservó proteína cuando cambian calorías y desplazó principalmente carbohidratos.
- Guardó fuente y distribución resuelta en el resultado.

### PPK04 — Meal solver integration — completed

- Aceptó porcentajes completos solicitados para una comida.
- Cambió el fallback kcal-only a 30/50/20.
- Rechazó mezclas parciales o conflictivas de gramos y porcentajes.

### PPK05 — Catalog and documentation — completed

- Añadió DP-13 para PPK/distribución coherente.
- Registró DP-14 como brecha honesta hasta disponer de agenda de entrenamiento.
- Adoptó la decisión 0198 y actualizó los contratos vigentes.

### PPK06 — Executable validation — completed

- Cubrió rangos, distribuciones aceptadas, contradicciones, límites de grasa y PPK.
- Cubrió estabilidad de proteína ante cambios calóricos y el solver de comidas.
- Incluyó las nuevas filas en el gate del catálogo vivo.

## Deferred scope

No se infiere hora de entrenamiento, día de descanso ni sensibilidad metabólica desde
el nivel general de actividad. Esa capacidad requiere primero una agenda diaria y una
política propia de periodización. Tampoco se modelan todavía tiempos de absorción por
alimento.

## Validation

```bash
python manage.py test notas.tests.test_macro_target_policy \
  notas.tests.test_nutrition_engine_target_estimator \
  notas.tests.test_nutrition_solver_meal_proposal --keepdb
scripts/ci_ai_assistant_capability_catalog.sh
```
