# USDA Foundation Foods import process

Este documento describe el proceso operativo para importar, validar, localizar y usar USDA Foundation Foods en My Scoope.

## Objetivo

Enriquecer la base global de alimentos usando USDA FoodData Central Foundation Foods como fuente pública inicial, manteniendo:

- trazabilidad por fuente;
- control de calidad;
- importación reproducible;
- aliases en español;
- `display_name` localizado;
- búsqueda server-side en el picker;
- validación operativa del catálogo.

## Fuente

- Fuente: USDA FoodData Central.
- Dataset: Foundation Foods.
- Formato usado: JSON descargable.
- Versión actual importada: `2026-04`.
- Archivo local usado:

~~~txt
data/food_sources/usda/foundation_foods_2026_04.json
~~~

El archivo local no necesita conservar el nombre original descargado desde USDA. Se renombra internamente para reflejar la versión del dataset.

## Resultado actual validado

Para Foundation Foods `2026-04`, el resultado operativo validado fue:

~~~txt
Global foods: 365
Core foods: 8
Extended foods: 357
Hidden foods: 0
USDA metadata: 365
Aliases: 26
Localized names: 365
~~~

Los alimentos USDA visibles tienen `FoodLocalizedName` primario en español `es-CL`.

## Flujo operativo completo

### 1. Descargar dataset

Descargar el archivo JSON de Foundation Foods desde USDA FoodData Central.

Crear carpeta local si no existe:

~~~bash
mkdir -p data/food_sources/usda
~~~

Guardar el archivo con un nombre versionado:

~~~txt
data/food_sources/usda/foundation_foods_2026_04.json
~~~

Para futuras versiones:

~~~txt
data/food_sources/usda/foundation_foods_YYYY_MM.json
~~~

---

### 2. Ejecutar dry-run

Antes de importar, siempre ejecutar dry-run:

~~~bash
python manage.py dry_run_usda_foods_json \
  data/food_sources/usda/foundation_foods_2026_04.json \
  --source-version 2026-04 \
  --source-dataset foundation_foods \
  --show-samples \
  --sample-size 10
~~~

El dry-run no escribe en base de datos.

Debe reportar:

- `total`
- `valid`
- `invalid`
- `duplicates`
- `failed`
- `would_import`
- `would_skip`
- `visibility_extended`
- `visibility_hidden`
- `reasons`
- `samples`, si se usa `--show-samples`

---

### 3. Ejecutar import real controlado

Si el dry-run es aceptable:

~~~bash
python manage.py import_usda_foods_json \
  data/food_sources/usda/foundation_foods_2026_04.json \
  --source-version 2026-04 \
  --source-dataset foundation_foods \
  --notes "USDA Foundation Foods 2026-04 controlled import"
~~~

El import crea:

- alimentos globales;
- metadata USDA;
- batch de importación;
- conteos de importación;
- fallos de mapping contabilizados sin abortar el proceso completo.

---

### 4. Validar idempotencia del import

Después del import, volver a correr dry-run:

~~~bash
python manage.py dry_run_usda_foods_json \
  data/food_sources/usda/foundation_foods_2026_04.json \
  --source-version 2026-04 \
  --source-dataset foundation_foods
~~~

Resultado esperado después de importar todo lo válido:

~~~txt
would_import=0
~~~

Los alimentos ya importados deben aparecer como:

~~~txt
already_imported
~~~

Para la versión `2026-04`, el dry-run final validado fue:

~~~txt
total=395
valid=363
invalid=0
duplicates=363
failed=32
would_import=0
would_skip=395
reasons:
- already_imported: 363
- mapping_failed: 32
~~~

Los `mapping_failed` observados corresponden a entradas `null` dentro del array `FoundationFoods`.

---

### 5. Aplicar core seed y aliases

Ejecutar:

~~~bash
python manage.py apply_core_food_seed
python manage.py apply_usda_spanish_aliases
~~~

Esto promueve alimentos globales conocidos a `core` y agrega aliases en español.

Para `2026-04`, los alimentos core iniciales fueron:

~~~txt
Oats, raw
Chicken breast, cooked
Eggs, Grade A, Large, egg whole
Rice, white, long grain, unenriched, raw
Rice, brown, long grain, unenriched, raw
Nuts, almonds, whole, raw
Kale, raw
Hummus, commercial
~~~

Ejemplos de aliases principales:

~~~txt
Avena
Avena cruda
Pechuga de pollo
Pollo
Huevo
Huevos
Arroz
Arroz blanco
Arroz integral
Almendra
Almendras
Kale
Col rizada
Hummus
Humus
~~~

---

### 6. Aplicar display names en español

Ejecutar:

~~~bash
python manage.py apply_usda_spanish_display_names
~~~

Esto crea `FoodLocalizedName` primario `es-CL` para alimentos USDA visibles que aún no lo tengan.

Si se mejora el algoritmo de traducción y se desea regenerar los nombres existentes:

~~~bash
python manage.py apply_usda_spanish_display_names --overwrite
~~~

Para la versión `2026-04`, después de aplicar el flujo completo:

~~~txt
Localized names: 365
~~~

Esto significa que todos los alimentos globales USDA visibles tienen nombre localizado en español.

---

### 7. Validar conteos

Ejecutar:

~~~bash
python manage.py shell -c '
from notas.domain.models import Food, FoodAlias, FoodLocalizedName, FoodSourceMetadata

print("Global foods:", Food.objects.filter(is_global=True).count())
print("Core foods:", Food.objects.filter(is_global=True, visibility=Food.VISIBILITY_CORE).count())
print("Extended foods:", Food.objects.filter(is_global=True, visibility=Food.VISIBILITY_EXTENDED).count())
print("Hidden foods:", Food.objects.filter(is_global=True, visibility=Food.VISIBILITY_HIDDEN).count())
print("USDA metadata:", FoodSourceMetadata.objects.filter(source=FoodSourceMetadata.SOURCE_USDA).count())
print("Aliases:", FoodAlias.objects.count())
print("Localized names:", FoodLocalizedName.objects.count())
'
~~~

Resultado validado para `2026-04`:

~~~txt
Global foods: 365
Core foods: 8
Extended foods: 357
Hidden foods: 0
USDA metadata: 365
Aliases: 26
Localized names: 365
~~~

---

### 8. Validar localized names específicos

Ejemplo para pescados:

~~~bash
python manage.py shell -c '
from notas.domain.models import FoodLocalizedName

for item in FoodLocalizedName.objects.filter(
    normalized_name__icontains="pescado"
).select_related("food").values(
    "food__id",
    "food__name",
    "name",
    "normalized_name",
)[:20]:
    print(item)
'
~~~

Ejemplo esperado:

~~~txt
Fish, tuna... -> Atún...
Fish, salmon... -> Salmón...
Fish, cod... -> Bacalao...
~~~

---

### 9. Validar endpoint server-side del picker

La app está montada bajo `/app/`, por lo que el endpoint local correcto es:

~~~txt
http://127.0.0.1:8000/app/api/foods/?search=fish&limit=20
~~~

y:

~~~txt
http://127.0.0.1:8000/app/api/foods/?search=pescado&limit=20
~~~

Este endpoint debe buscar contra la base completa, no solo contra el payload inicial del picker.

---

### 10. Validar picker en UI

Validar manualmente búsquedas en español e inglés:

~~~txt
pescado
fish
bacalao
atún
salmón
cerdo
pork
porotos
beans
harina
flour
avena
pollo
huevo
arroz
almendra
hummus
~~~

Resultado esperado:

- el alimento aparece aunque no estuviera en el payload inicial;
- el picker usa server-side search;
- el nombre mostrado usa `display_name`;
- alimentos con `FoodLocalizedName` aparecen en español;
- alimentos `hidden` no aparecen.

---

## Decisiones técnicas

### Uso de archivo descargable

Para carga inicial masiva se usa archivo JSON local descargado desde USDA, no API.

Razones:

- permite dry-run completo;
- evita rate limits;
- permite auditoría por versión;
- hace la carga reproducible;
- permite import controlado;
- desacopla el picker de servicios externos.

La API USDA queda como opción futura para enriquecimiento puntual o actualización selectiva por `fdcId`.

---

### Reader Foundation Foods

El reader se encarga solo de leer el archivo y extraer la lista de payloads.

No valida cada fila como objeto alimento.

Motivo:

- el archivo real puede contener entradas `null`;
- esas filas deben ser contabilizadas por dry-run/import como `mapping_failed`;
- el reader no debe abortar todo el proceso por filas no mapeables.

---

### Dry-run

El dry-run es obligatorio antes del import real.

Responsabilidades:

- mapear payloads USDA;
- normalizar DTOs;
- evaluar calidad;
- detectar duplicados en base;
- detectar duplicados dentro del archivo;
- estimar visibilidad;
- reportar razones y samples.

No escribe en base de datos.

---

### Negative carbs USDA

Algunos alimentos animales venían con carbohidratos negativos desde USDA.

Decisión:

- normalizar carbohidratos negativos USDA a `0`;
- mantener validación estricta para otros macros;
- corregir en el mapper USDA, no en la validación general.

---

### Visibilidad

Los alimentos importados desde USDA entran como globales.

La visibilidad inicial se resuelve según calidad:

- `core`: alimentos base conocidos promovidos por seed;
- `extended`: alimentos importados válidos, buscables y seleccionables;
- `hidden`: alimentos que no deberían aparecer en picker.

---

### Aliases

Los aliases sirven principalmente para búsqueda.

Ejemplo:

~~~txt
Pollo -> Chicken breast, cooked
Huevo -> Eggs, Grade A, Large, egg whole
Arroz -> Rice, white, long grain, unenriched, raw
~~~

---

### Display names

Los `FoodLocalizedName` sirven para visualización.

Fallback esperado:

1. `FoodLocalizedName` primario `es-CL`;
2. `food.name` original si no existe localized name.

Después de esta macrofase, todos los alimentos USDA visibles deberían tener `FoodLocalizedName` primario `es-CL`.

---

### Server-side picker search

El picker tenía una limitación inicial:

~~~txt
payload inicial limitado
+ búsqueda local JS
= alimentos fuera del payload no aparecían
~~~

La solución fue agregar búsqueda server-side usando el endpoint:

~~~txt
/app/api/foods/?search=<query>&limit=<n>
~~~

Así, el picker puede encontrar alimentos fuera de los primeros resultados precargados.

---

### Curación lingüística

La traducción automática por glosario y patrones es una primera capa operativa.

Limitación conocida:

- algunos nombres generados pueden seguir sonando poco naturales;
- ejemplo: combinaciones con semillas, variedades regionales o términos técnicos USDA.

Decisión:

- no bloquear la macrofase por curación lingüística fina;
- tratar la curación de nombres como una etapa futura propia.

Futura etapa sugerida:

~~~txt
Food naming curation layer
~~~

Objetivos futuros:

- reglas por categoría;
- override manual de nombres;
- tabla editable de nombres curados;
- alias regionales;
- soporte LATINFOODS/Open Food Facts;
- diferencia entre nombre visible simple y nombre técnico/source name.

---

## Tests recomendados de esta macrofase

Ejecutar:

~~~bash
python manage.py test \
  notas.tests.test_usda_foundation_foods_reader \
  notas.tests.test_dry_run_usda_foods_json_command \
  notas.tests.test_usda_food_payload_import_command \
  notas.tests.test_import_usda_foods_json_command \
  notas.tests.test_usda_food_mapper \
  notas.tests.test_core_food_seed_catalog \
  notas.tests.test_core_food_seed_service \
  notas.tests.test_apply_core_food_seed_command \
  notas.tests.test_usda_spanish_display_names \
  notas.tests.test_food_picker_queries \
  notas.tests.test_food_picker_display_name_static_assets \
  notas.tests.test_food_json_and_picker_contracts \
  notas.tests.test_dpm_food_picker_builder \
  notas.tests.test_picker_payloads \
  notas.tests.test_dpm_food_picker_payloads \
  notas.tests.test_builder_table_items
~~~

---

## Checklist para futuras versiones USDA

1. Descargar nuevo JSON Foundation Foods.
2. Guardarlo como `data/food_sources/usda/foundation_foods_YYYY_MM.json`.
3. Ejecutar dry-run con `--show-samples`.
4. Revisar `invalid`, `failed`, `would_import`.
5. Ejecutar import real si el dry-run es aceptable.
6. Repetir dry-run para confirmar `would_import=0`.
7. Ejecutar `apply_core_food_seed`.
8. Ejecutar `apply_usda_spanish_aliases`.
9. Ejecutar `apply_usda_spanish_display_names`.
10. Ejecutar `apply_usda_spanish_display_names --overwrite` solo si cambió el algoritmo de traducción y se desea regenerar nombres.
11. Validar conteos.
12. Validar endpoint `/app/api/foods/?search=...`.
13. Validar picker manualmente.
14. Ejecutar tests de la macrofase.
15. Hacer commit de cambios de código/docs.