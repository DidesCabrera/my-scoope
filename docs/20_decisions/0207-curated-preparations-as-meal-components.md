# 0207 — Preparaciones curadas como componentes de Comida

Status: accepted
Date: 2026-11-08

## Decisión

Una Preparación tiene identidad propia y no es un Alimento con macros precalculados. En la primera etapa, solo My Scoope crea y publica revisiones. Una revisión registra alimentos ingredientes, gramos y estado de preparación, condimentos visibles, rendimiento comestible estimado, porción doméstica, nutrientes calculados y evidencia del rendimiento. No admite Preparaciones anidadas.

El Food Catalog central conserva la autoridad editorial. Una revisión pasa a publicada solo si todos sus ingredientes son alimentos publicados, con valores de proteína, carbohidratos, grasa y sodio, y una evaluación explícita de alérgenos (`none` es una evaluación válida). La compilación congela nutrientes, alérgenos, cantidades, nombres y referencias de los alimentos. Un release aprobado entrega esa copia con suma de control; el importador la materializa en `notas.Preparation` después de materializar `notas.Food`. Las Comidas nunca calculan desde el catálogo central.

Una Comida contiene `MealFood` y `MealPreparation` por relaciones distintas. La porción de Preparación conserva la revisión, los gramos equivalentes y la selección original en unidades o gramos. El selector ofrece 0,5 a 10 unidades en pasos de 0,5; gramos permite una cantidad positiva de hasta diez porciones domésticas. El cálculo de la Comida suma una vez la porción de Preparación. Sus ingredientes explican el cálculo y se muestran proporcionalmente, con acceso al detalle de cada Alimento.

Las copias de Comida, minutas y programas conservan la relación de Preparación. Cuando una revisión nueva se materializa, las Comidas todavía vivas en bibliotecas y sus cachés de minutas/programas se actualizan: la elección en unidades conserva el número de unidades y recalcula gramos; la elección en gramos conserva los gramos. Los snapshots ya asignados al calendario retienen nombre, revisión, porción, ingredientes y nutrientes anteriores. Compartir guarda una copia autónoma de la composición; al guardarla de nuevo en una biblioteca se exige que la misma revisión global siga disponible, sin convertir la Preparación en un Alimento privado.

El modelo operacional admite propietario para una futura Preparación personal, pero esta etapa no expone creación ni edición de Preparaciones por personas. La publicación y el selector solo ofrecen las versiones globales curadas. La evolución personal usará el mismo cálculo y una autoridad separada; requerirá un flujo específico de revisión y permisos.

## Límites de esta entrega

- No se cargan Preparaciones reales ni se estiman pesos o rendimientos chilenos. El curador debe aportar la evidencia.
- Los ingredientes en mililitros se bloquean hasta tener una conversión verificada a gramos.
- Una Preparación puede leerse en un snapshot de calendario. La edición de su porción dentro de un día ya asignado requiere un editor específico; los comandos heredados de Alimento la rechazan para evitar cambiar solo macros sin ajustar ingredientes y sodio.
- La interfaz inicial de selección y edición de porción está en la biblioteca móvil de Comidas. El flujo web y el agregado directo a un día calendarizado quedan para una etapa de interfaz posterior.
