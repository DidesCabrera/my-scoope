# Evaluación inicial del solver: 30 solicitudes sintéticas

Fecha: 11 de noviembre de 2026. Código: `origin/staging@5cf0880169c485fa6eb4a6aeee92cf66f9e84a29`. Datos: copia de solo lectura de 157 `notas.Food` elegibles en staging, snapshot `2026-11-solver-v1`.

## Alcance y método

- Se ejecutó el motor puro `cp_sat_v1` con los filtros de patrón alimentario y alérgenos del adaptador operativo, 3 alternativas por caso y límite de 1,5 s por búsqueda. Se seleccionó la alternativa con mejor puntuación nutricional, como hace el adaptador.
- Las metas son entradas sintéticas para probar comportamiento del producto, no recomendaciones nutricionales. Se usaron tolerancias por comida y día del adaptador actual.
- Esta prueba cubre minutas de 3 o 4 comidas. No ejecuta la ruta de variantes culinarias, la API, la persistencia de propuestas ni programas semanales. Los resultados no autorizan afirmar calidad clínica o culinaria.

## Resultado cuantitativo

- 26/30 solicitudes tuvieron 3 alternativas; 4/30 quedaron inviables.
- Puntuación nutricional media de las 26 soluciones seleccionadas: 93.2/100 (rango 86.8–99.3).
- La puntuación funcional fue 100/100 en todas las soluciones obtenidas, pero sólo mide cobertura de roles y número de componentes; no verifica si forman una comida apetecible o preparable.
- 16/26 soluciones incluyen al menos un alimento catalogado crudo o seco. Esto no prueba un error en cada caso, pero exige revisar preparación y cantidades.
- 10/26 repiten un alimento tres o más veces en el día; 8/26 asignan más de 170 g de algún yogur en una comida.

## Tabla de casos

| Caso | Solicitud | Candidatos | Alternativas | Estado | Nutrición |
|---|---|---:|---:|---|---:|
| S01 | Omnívoro, 1800 kcal, 3 comidas | 157 | 3 | acceptable | 91.5 |
| S02 | Omnívoro, 2200 kcal, 4 comidas | 157 | 3 | acceptable | 90.1 |
| S03 | Omnívoro, 2600 kcal, 4 comidas | 157 | 3 | acceptable | 96.5 |
| S04 | Omnívoro, 3000 kcal, 4 comidas | 157 | 3 | acceptable | 91.9 |
| S05 | Omnívoro, alto en proteína | 157 | 3 | acceptable | 94.5 |
| S06 | Omnívoro, alto en carbohidratos | 157 | 3 | acceptable | 95.0 |
| S07 | Vegetariano, 1800 kcal | 145 | 3 | acceptable | 95.6 |
| S08 | Vegetariano, 2300 kcal | 145 | 3 | acceptable | 94.0 |
| S09 | Vegetariano, alto en proteína | 145 | 3 | acceptable | 99.3 |
| S10 | Vegano, 1800 kcal | 124 | 3 | acceptable | 89.2 |
| S11 | Vegano, 2300 kcal | 124 | 3 | acceptable | 88.4 |
| S12 | Vegano, alto en proteína | 124 | 3 | acceptable | 93.0 |
| S13 | Pescetariano, 1800 kcal | 153 | 3 | acceptable | 95.4 |
| S14 | Pescetariano, 2300 kcal | 153 | 3 | acceptable | 91.2 |
| S15 | Pescetariano, alto en proteína | 153 | 3 | acceptable | 95.1 |
| S16 | Alergia a leche | 19 | 0 | impossible | — |
| S17 | Alergia a huevo | 36 | 3 | optimal | 93.2 |
| S18 | Alergia a frutos secos | 35 | 3 | optimal | 93.5 |
| S19 | Alergia a soya | 34 | 0 | impossible | — |
| S20 | Alergia a pescado | 36 | 3 | optimal | 93.5 |
| S21 | Vegano y alergia a soya | 5 | 0 | impossible | — |
| S22 | Vegetariano y alergia a leche | 11 | 0 | impossible | — |
| S23 | Sin pollo | 150 | 3 | acceptable | 92.3 |
| S24 | Sin arroz | 155 | 3 | acceptable | 95.8 |
| S25 | Prefiere legumbres | 157 | 3 | acceptable | 90.6 |
| S26 | Poco tiempo para cocinar | 157 | 3 | acceptable | 86.8 |
| S27 | Presupuesto bajo | 157 | 3 | acceptable | 91.7 |
| S28 | Vegano, poco tiempo y bajo presupuesto | 124 | 3 | acceptable | 93.7 |
| S29 | Vegetariano, sin huevos ni lácteos por exclusión | 129 | 3 | acceptable | 95.1 |
| S30 | Omnívoro, sin carnes ni pescados por exclusión | 146 | 3 | acceptable | 95.3 |

## Hallazgos que requieren acción

1. **Alergias:** S16, S19, S21 y S22 no produjeron alternativa. En el snapshot, 119/157 alimentos tienen una lista explícita vacía de alérgenos, pero el adaptador omite listas vacías al construir el perfil; luego el filtro de alergia interpreta la ausencia como desconocida y los excluye. La biblioteca culinaria sí distingue explícitamente una lista vacía de un dato ausente. Es una discrepancia de contrato/implementación que debe corregirse y verificarse con fuentes curadas antes de prometer seguridad.
2. **Coherencia culinaria:** S02 propone salmón con sandía y membrillo como snack, y avena con lentejas y huevo como plato principal. S10 propone garbanzos, berro y habas como snack. Son señales claras de que cumplir macros y roles no garantiza una minuta aceptable.
3. **Preferencias operativas:** el snapshot de los 157 candidatos informa `cost_band=unknown` y `preparation_effort=unknown` en todos. Por eso S26–S28 no pueden demostrar respeto efectivo al tiempo de cocina ni al presupuesto.
4. **Porciones y repetición:** la prueba muestra yogures de 340 g y hasta cuatro apariciones de un mismo alimento en un día. Hace falta el contrato de porción indivisible y una métrica de variedad percibida.
5. **Programas y staging culinario:** la comprobación de Render encontró 35 variantes culinarias validadas por reglas en producción y 0 en staging. Una prueba del camino culinario o de programas en staging no representaría producción hasta homologar esa biblioteca.

## Lectura del resultado

El solver demuestra capacidad numérica en solicitudes comunes y por patrón alimentario: 26/30 casos obtuvieron alternativas bajo estas condiciones. **No está demostrada la calidad de entrega de minutas ni programas.** El puntaje funcional actual sobreestima la calidad porque no evalúa recetas, preparación, sabor, conveniencia, envases ni repetición.

## Prioridades recomendadas

1. Corregir y versionar la semántica de alérgenos: diferenciar `desconocido` de `revisado sin alérgenos declarados`; repetir los 7 casos con alergias, con validación de Curación.
2. Incorporar reglas de porción por unidad/envase y revisar yogures, huevos, latas y frutas enteras; volver a ejecutar los 30 casos.
3. Homologar las variantes culinarias de staging con producción y evaluar las mismas solicitudes por la ruta culinaria, más casos semanales de programa.
4. Añadir revisión humana ciega de coherencia, practicidad y variedad sobre las tres alternativas de cada caso. Definir umbral de aceptación antes de activar cambios del solver.

## Detalle para revisión de Felipe

Cada sección muestra la alternativa seleccionada. Las otras dos composiciones no se guardan en este primer informe; la ejecución conserva el resultado seleccionado y el número de alternativas.

### S01 · Omnívoro, 1800 kcal, 3 comidas

**acceptable** · 3 alternativas · 91.5/100 nutrición · kcal 1791 frente a 1800 objetivo.

- meal_0: Garbanzos cocidos (200 g), Huevo entero (95 g), Durazno crudo (80 g).
- meal_1: Arvejas de ojo negro cocidas (270 g), Soya cocida (190 g).
- meal_2: Lentejas cocidas (290 g), Mozzarella fresca (55 g), Taro cocido (70 g).

### S02 · Omnívoro, 2200 kcal, 4 comidas

**acceptable** · 3 alternativas · 90.1/100 nutrición · kcal 2194 frente a 2200 objetivo.

- meal_0: Garbanzos cocidos (190 g), Huevo entero (100 g), Guayaba cruda (90 g).
- meal_1: Avena tradicional (45 g), Lentejas cocidas (360 g), Huevo entero (100 g).
- meal_2: Salmón cocido (100 g), Sandía cruda (430 g), Membrillo crudo (50 g).
- meal_3: Lentejas cocidas (250 g), Huevo entero (100 g), Hinojo bulbo crudo (75 g), Champiñón blanco cocido (310 g).

### S03 · Omnívoro, 2600 kcal, 4 comidas

**acceptable** · 3 alternativas · 96.5/100 nutrición · kcal 2559 frente a 2600 objetivo.

- meal_0: Arroz blanco cocido (190 g), Requesón bajo en grasa (250 g), Ricotta entera (140 g).
- meal_1: Avena tradicional (40 g), Arvejas de ojo negro cocidas (250 g), Soya cocida (230 g).
- meal_2: Lentejas cocidas (250 g), Nueces (15 g).
- meal_3: Lentejas cocidas (360 g), Queso suizo (55 g).

### S04 · Omnívoro, 3000 kcal, 4 comidas

**acceptable** · 3 alternativas · 91.9/100 nutrición · kcal 2963 frente a 3000 objetivo.

- meal_0: Arroz integral cocido (270 g), Palta (95 g), Requesón bajo en grasa (370 g).
- meal_1: Camote cocido (400 g), Pechuga de pollo cocida (200 g), Nueces (30 g), Papa horneada con piel (200 g).
- meal_2: Huevo entero (100 g), Carambola cruda (180 g), Guayaba cruda (330 g).
- meal_3: Lentejas cocidas (360 g), Palta (100 g), Porotos mung cocidos (160 g).

### S05 · Omnívoro, alto en proteína

**acceptable** · 3 alternativas · 94.5/100 nutrición · kcal 2293 frente a 2300 objetivo.

- meal_0: Arroz integral cocido (240 g), Pechuga de pollo cocida (140 g), Queso suizo (15 g).
- meal_1: Porotos negros cocidos (330 g), Pechuga de pollo cocida (130 g), Queso suizo (35 g).
- meal_2: Quinoa cocida (140 g), Atún en agua drenado (100 g), Leche entera (150 g).
- meal_3: Lentejas cocidas (270 g), Huevo entero (100 g), Porotos pintos cocidos (90 g).

### S06 · Omnívoro, alto en carbohidratos

**acceptable** · 3 alternativas · 95.0/100 nutrición · kcal 2259 frente a 2300 objetivo.

- meal_0: Porotos negros cocidos (210 g), Leche entera (430 g).
- meal_1: Huevo entero (50 g), Soya cocida (180 g), Taro cocido (260 g).
- meal_2: Leche descremada (400 g), Nueces (15 g), Melón calameño crudo (260 g).
- meal_3: Quinoa cocida (300 g), Queso suizo (35 g), Taro cocido (70 g).

### S07 · Vegetariano, 1800 kcal

**acceptable** · 3 alternativas · 95.6/100 nutrición · kcal 1841 frente a 1800 objetivo.

- meal_0: Manzana (310 g), Queso suizo (30 g), Requesón bajo en grasa (190 g).
- meal_1: Lentejas cocidas (250 g), Queso suizo (50 g), Habas cocidas (180 g).
- meal_2: Avena tradicional (30 g), Leche descremada (360 g), Queso de cabra semiduro (25 g).
- meal_3: Lentejas cocidas (230 g), Clara de huevo (65 g), Almendras (25 g), Apio crudo (60 g).

### S08 · Vegetariano, 2300 kcal

**acceptable** · 3 alternativas · 94.0/100 nutrición · kcal 2269 frente a 2300 objetivo.

- meal_0: Quinoa cocida (190 g), Queso cheddar (35 g), Yogur natural descremado sin azúcar (340 g).
- meal_1: Soya cocida (230 g), Arvejas verdes cocidas (320 g).
- meal_2: Lentejas cocidas (150 g), Yogur natural entero sin azúcar (340 g).
- meal_3: Lentejas cocidas (350 g), Queso suizo (50 g).

### S09 · Vegetariano, alto en proteína

**acceptable** · 3 alternativas · 99.3/100 nutrición · kcal 2307 frente a 2300 objetivo.

- meal_0: Huevo entero (85 g), Manzana (330 g), Requesón bajo en grasa (350 g).
- meal_1: Mantequilla con sal (15 g), Requesón bajo en grasa (430 g), Porotos cranberry cocidos (270 g).
- meal_2: Huevo entero (55 g), Manzana (220 g), Requesón bajo en grasa (240 g).
- meal_3: Papa cocida sin piel (250 g), Huevo entero (100 g), Requesón bajo en grasa (340 g).

### S10 · Vegano, 1800 kcal

**acceptable** · 3 alternativas · 89.2/100 nutrición · kcal 1802 frente a 1800 objetivo.

- meal_0: Soya cocida (120 g), Guayaba cruda (270 g).
- meal_1: Papa cocida sin piel (220 g), Soya cocida (210 g), Chirivía cocida (40 g).
- meal_2: Garbanzos cocidos (120 g), Berro crudo (65 g), Habas cocidas (120 g).
- meal_3: Avena tradicional (30 g), Soya cocida (160 g), Repollo blanco crudo (175 g).

### S11 · Vegano, 2300 kcal

**acceptable** · 3 alternativas · 88.4/100 nutrición · kcal 2228 frente a 2300 objetivo.

- meal_0: Manzana (260 g), Lupino cocido (260 g).
- meal_1: Porotos pintos cocidos (310 g), Tofu blando (490 g).
- meal_2: Garbanzos cocidos (160 g), Espinaca cruda (100 g), Espárrago crudo (260 g).
- meal_3: Porotos blancos cocidos (210 g), Soya cocida (160 g).

### S12 · Vegano, alto en proteína

**acceptable** · 3 alternativas · 93.0/100 nutrición · kcal 2231 frente a 2300 objetivo.

- meal_0: Lupino cocido (330 g), Carambola cruda (180 g).
- meal_1: Garbanzos cocidos (150 g), Espinaca cruda (100 g), Espárrago crudo (260 g), Berro crudo (65 g), Lupino cocido (330 g).
- meal_2: Lupino cocido (240 g), Carambola cruda (175 g).
- meal_3: Avena tradicional (40 g), Lupino cocido (330 g), Repollo blanco crudo (75 g).

### S13 · Pescetariano, 1800 kcal

**acceptable** · 3 alternativas · 95.4/100 nutrición · kcal 1800 frente a 1800 objetivo.

- meal_0: Quinoa cocida (100 g), Mantequilla de maní natural (19 g), Yogur natural descremado sin azúcar (340 g).
- meal_1: Porotos negros cocidos (280 g), Huevo entero (100 g), Clara de huevo (65 g), Palta (40 g).
- meal_2: Avena tradicional (35 g), Yogur griego natural sin azúcar (170 g), Palta (30 g).
- meal_3: Quinoa cocida (200 g), Huevo entero (100 g), Repollo de Bruselas crudo (170 g).

### S14 · Pescetariano, 2300 kcal

**acceptable** · 3 alternativas · 91.2/100 nutrición · kcal 2305 frente a 2300 objetivo.

- meal_0: Quinoa cocida (180 g), Queso cheddar (35 g), Yogur natural descremado sin azúcar (340 g).
- meal_1: Lentejas cocidas (250 g), Garbanzos cocidos (190 g), Huevo entero (100 g), Clara de huevo (60 g).
- meal_2: Almendras (30 g), Yogur natural descremado sin azúcar (340 g).
- meal_3: Garbanzos cocidos (230 g), Huevo entero (100 g), Clara de huevo (65 g), Zapallo italiano cocido (220 g).

### S15 · Pescetariano, alto en proteína

**acceptable** · 3 alternativas · 95.1/100 nutrición · kcal 2286 frente a 2300 objetivo.

- meal_0: Arroz integral cocido (200 g), Huevo entero (75 g), Requesón bajo en grasa (330 g).
- meal_1: Atún en agua drenado (100 g), Porotos adzuki cocidos (250 g), Soya cocida (190 g).
- meal_2: Manzana (200 g), Requesón bajo en grasa (330 g).
- meal_3: Porotos negros cocidos (250 g), Huevo entero (100 g), Centolla cocida (130 g).

### S16 · Alergia a leche

**Sin solución.** Candidatos después de filtros: 19. La primera ejecución diagnóstica registró inviabilidad del modelo; revisar junto con el caso de alérgenos.

### S17 · Alergia a huevo

**optimal** · 3 alternativas · 93.2/100 nutrición · kcal 1984 frente a 2100 objetivo.

- meal_0: Leche descremada (400 g), Tomate (240 g), Leche semidescremada (250 g), Soya cocida (90 g).
- meal_1: Tomate (240 g), Yogur natural entero sin azúcar (340 g), Soya cocida (110 g), Yogur natural descremado sin azúcar (340 g).
- meal_2: Leche descremada (130 g), Palta (60 g), Yogur natural descremado sin azúcar (340 g).
- meal_3: Tomate (240 g), Yogur natural entero sin azúcar (170 g), Soya cocida (90 g), Yogur natural descremado sin azúcar (340 g).

### S18 · Alergia a frutos secos

**optimal** · 3 alternativas · 93.5/100 nutrición · kcal 1963 frente a 2100 objetivo.

- meal_0: Leche descremada (400 g), Tomate (240 g), Leche semidescremada (250 g), Soya cocida (90 g).
- meal_1: Clara de huevo (35 g), Tomate (240 g), Yogur natural entero sin azúcar (340 g), Soya cocida (90 g), Yogur natural descremado sin azúcar (340 g).
- meal_2: Leche descremada (130 g), Palta (60 g), Yogur natural descremado sin azúcar (340 g).
- meal_3: Tomate (240 g), Yogur natural entero sin azúcar (170 g), Soya cocida (90 g), Yogur natural descremado sin azúcar (340 g).

### S19 · Alergia a soya

**Sin solución.** Candidatos después de filtros: 34. La primera ejecución diagnóstica registró inviabilidad del modelo; revisar junto con el caso de alérgenos.

### S20 · Alergia a pescado

**optimal** · 3 alternativas · 93.5/100 nutrición · kcal 1963 frente a 2100 objetivo.

- meal_0: Leche descremada (400 g), Tomate (240 g), Leche semidescremada (250 g), Soya cocida (90 g).
- meal_1: Clara de huevo (35 g), Tomate (240 g), Yogur natural entero sin azúcar (340 g), Soya cocida (90 g), Yogur natural descremado sin azúcar (340 g).
- meal_2: Leche descremada (130 g), Palta (60 g), Yogur natural descremado sin azúcar (340 g).
- meal_3: Tomate (240 g), Yogur natural entero sin azúcar (170 g), Soya cocida (90 g), Yogur natural descremado sin azúcar (340 g).

### S21 · Vegano y alergia a soya

**Sin solución.** Candidatos después de filtros: 5. La primera ejecución diagnóstica registró inviabilidad del modelo; revisar junto con el caso de alérgenos.

### S22 · Vegetariano y alergia a leche

**Sin solución.** Candidatos después de filtros: 11. La primera ejecución diagnóstica registró inviabilidad del modelo; revisar junto con el caso de alérgenos.

### S23 · Sin pollo

**acceptable** · 3 alternativas · 92.3/100 nutrición · kcal 2001 frente a 2100 objetivo.

- meal_0: Lentejas cocidas (320 g), Queso de cabra semiduro (45 g).
- meal_1: Lentejas cocidas (360 g), Mozzarella fresca (55 g).
- meal_2: Lentejas cocidas (190 g), Queso suizo (30 g).
- meal_3: Avena tradicional (80 g), Salmón cocido (120 g).

### S24 · Sin arroz

**acceptable** · 3 alternativas · 95.8/100 nutrición · kcal 2077 frente a 2100 objetivo.

- meal_0: Quinoa cocida (250 g), Huevo entero (85 g), Requesón bajo en grasa (130 g).
- meal_1: Quinoa cocida (170 g), Arvejas partidas cocidas (180 g), Tofu blando (430 g).
- meal_2: Carne magra cocida (90 g), Membrillo crudo (170 g), Carambola cruda (175 g).
- meal_3: Lentejas cocidas (310 g), Huevo entero (100 g), Betarraga cocida (45 g).

### S25 · Prefiere legumbres

**acceptable** · 3 alternativas · 90.6/100 nutrición · kcal 1964 frente a 2100 objetivo.

- meal_0: Lentejas cocidas (280 g), Queso suizo (45 g).
- meal_1: Lentejas cocidas (360 g), Huevo entero (100 g).
- meal_2: Lentejas cocidas (190 g), Queso suizo (30 g).
- meal_3: Lentejas cocidas (330 g), Huevo entero (100 g).

### S26 · Poco tiempo para cocinar

**acceptable** · 3 alternativas · 86.8/100 nutrición · kcal 1939 frente a 2100 objetivo.

- meal_0: Lentejas cocidas (220 g), Leche entera (400 g).
- meal_1: Lentejas cocidas (360 g), Huevo entero (100 g).
- meal_2: Lentejas cocidas (170 g), Palta (60 g), Arándanos (45 g).
- meal_3: Lentejas cocidas (320 g), Huevo entero (100 g).

### S27 · Presupuesto bajo

**acceptable** · 3 alternativas · 91.7/100 nutrición · kcal 2058 frente a 2100 objetivo.

- meal_0: Quinoa cocida (120 g), Ricotta entera (110 g), Yogur natural descremado sin azúcar (340 g).
- meal_1: Arvejas de ojo negro cocidas (280 g), Soya cocida (200 g).
- meal_2: Quinoa cocida (100 g), Yogur natural entero sin azúcar (340 g).
- meal_3: Lentejas cocidas (320 g), Huevo entero (100 g).

### S28 · Vegano, poco tiempo y bajo presupuesto

**acceptable** · 3 alternativas · 93.7/100 nutrición · kcal 2101 frente a 2100 objetivo.

- meal_0: Quinoa cocida (210 g), Lupino cocido (180 g), Clementina cruda (40 g).
- meal_1: Avena tradicional (35 g), Soya cocida (230 g), Alcachofa cocida (240 g).
- meal_2: Soya cocida (110 g), Papaya cruda (270 g).
- meal_3: Garbanzos cocidos (200 g), Tofu firme (250 g).

### S29 · Vegetariano, sin huevos ni lácteos por exclusión

**acceptable** · 3 alternativas · 95.1/100 nutrición · kcal 2098 frente a 2100 objetivo.

- meal_0: Porotos negros cocidos (180 g), Espinaca cruda (100 g), Espárrago crudo (260 g), Mozzarella fresca (55 g).
- meal_1: Porotos pintos cocidos (290 g), Tofu blando (430 g).
- meal_2: Piña cruda (210 g), Soya cocida (120 g).
- meal_3: Soya cocida (200 g), Repollo blanco crudo (175 g), Chirivía cocida (155 g).

### S30 · Omnívoro, sin carnes ni pescados por exclusión

**acceptable** · 3 alternativas · 95.3/100 nutrición · kcal 2123 frente a 2100 objetivo.

- meal_0: Papa cocida sin piel (220 g), Yogur griego natural sin azúcar (340 g), Mantequilla sin sal (15 g).
- meal_1: Papa cocida sin piel (210 g), Soya cocida (210 g), Habas cocidas (200 g).
- meal_2: Avena tradicional (20 g), Yogur natural entero sin azúcar (170 g), Yogur natural descremado sin azúcar (340 g).
- meal_3: Quinoa cocida (280 g), Huevo entero (100 g), Camarón cocido (65 g).
