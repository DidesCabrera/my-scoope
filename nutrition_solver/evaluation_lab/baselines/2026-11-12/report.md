# Nutrition Solver evaluation lab

Run `ebe2e7c682cb14e4` · fixture `2026-11-solver-v1`
Cases: 30 · feasible: 26 · p95: 4563.2 ms · automatic gate: **failed**

The automatic gate does not certify culinary quality, nutrition policy or a production release.

| ID | Feasible | Candidates | Alternatives | Nutrition | Hard violations | Culinary signals | Repetition | Time ms | Reason |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| S01 | True | 157 | 3 | 91.5 | 0 | affinity 1; raw/dry 1 | 1 | 4730.3 | — |
| S02 | True | 157 | 3 | 90.1 | 0 | affinity 3; raw/dry 5 | 3 | 4559.5 | — |
| S03 | True | 157 | 3 | 96.5 | 0 | affinity 3; raw/dry 2 | 2 | 4558.0 | — |
| S04 | True | 157 | 3 | 91.9 | 0 | affinity 4; raw/dry 3 | 2 | 4557.0 | — |
| S05 | True | 157 | 3 | 94.5 | 0 | affinity 4; raw/dry 0 | 2 | 4557.5 | — |
| S06 | True | 157 | 3 | 95.0 | 0 | affinity 1; raw/dry 2 | 2 | 4556.7 | — |
| S07 | True | 145 | 3 | 95.6 | 0 | affinity 1; raw/dry 3 | 2 | 4556.3 | — |
| S08 | True | 145 | 3 | 94.0 | 0 | affinity 2; raw/dry 0 | 2 | 4554.3 | — |
| S09 | True | 145 | 3 | 99.3 | 0 | affinity 1; raw/dry 0 | 4 | 4553.3 | — |
| S10 | True | 124 | 3 | 89.2 | 0 | affinity 5; raw/dry 4 | 3 | 4547.8 | — |
| S11 | True | 124 | 3 | 88.4 | 0 | affinity 4; raw/dry 2 | 1 | 4546.1 | — |
| S12 | True | 124 | 3 | 92.9 | 0 | affinity 3; raw/dry 6 | 4 | 4547.6 | — |
| S13 | True | 153 | 3 | 95.4 | 0 | affinity 2; raw/dry 2 | 2 | 4562.1 | — |
| S14 | True | 153 | 3 | 91.2 | 0 | affinity 1; raw/dry 1 | 2 | 4555.3 | — |
| S15 | True | 153 | 3 | 95.1 | 0 | affinity 1; raw/dry 0 | 2 | 4556.6 | — |
| S16 | False | 19 | 0 | — | — | — | — | 10.9 | cp_sat_infeasible |
| S17 | True | 36 | 3 | 93.2 | 0 | affinity 7; raw/dry 0 | 3 | 2011.4 | — |
| S18 | True | 35 | 3 | 93.5 | 0 | affinity 7; raw/dry 0 | 3 | 2812.8 | — |
| S19 | False | 34 | 0 | — | — | — | — | 0.6 | required_role_group_empty |
| S20 | True | 36 | 3 | 93.5 | 0 | affinity 7; raw/dry 0 | 3 | 2904.8 | — |
| S21 | False | 5 | 0 | — | — | — | — | 0.2 | required_role_group_empty |
| S22 | False | 11 | 0 | — | — | — | — | 7.0 | cp_sat_infeasible |
| S23 | True | 150 | 3 | 92.3 | 0 | affinity 3; raw/dry 1 | 3 | 4563.2 | — |
| S24 | True | 155 | 3 | 95.9 | 0 | affinity 2; raw/dry 2 | 2 | 4562.5 | — |
| S25 | True | 157 | 3 | 90.6 | 0 | affinity 2; raw/dry 0 | 4 | 4557.5 | — |
| S26 | True | 157 | 3 | 86.8 | 0 | affinity 3; raw/dry 0 | 4 | 4560.7 | — |
| S27 | True | 157 | 3 | 91.7 | 0 | affinity 2; raw/dry 0 | 2 | 4562.0 | — |
| S28 | True | 124 | 3 | 93.7 | 0 | affinity 4; raw/dry 3 | 2 | 4551.0 | — |
| S29 | True | 129 | 3 | 95.1 | 0 | affinity 4; raw/dry 4 | 2 | 4553.1 | — |
| S30 | True | 146 | 3 | 95.3 | 0 | affinity 1; raw/dry 1 | 2 | 4553.6 | — |

## Automatic gate findings

- feasibility_rate_below_90pct
- expected_feasible_failed:S16
- expected_feasible_failed:S19
- expected_feasible_failed:S21
- expected_feasible_failed:S22

## Human review queue

Review meal coherence, preparation, portion realism, local relevance and practical usefulness. A numerical score cannot substitute for this review.

- S01
- S02
- S03
- S04
- S05
- S06
- S07
- S08
- S09
- S10
- S11
- S12
- S13
- S14
- S15
- S17
- S18
- S20
- S23
- S24
- S25
- S26
- S27
- S28
- S29
- S30

## Selected alternatives for review

### S01 · Omnívoro, 1800 kcal, 3 comidas

Nutrition 91.5/100 · alternatives 3 · stability not probed.

- meal_0: Garbanzos cocidos (200 g), Huevo entero (95 g), Durazno crudo (80 g).
- meal_1: Arvejas de ojo negro cocidas (270 g), Soya cocida (190 g).
- meal_2: Lentejas cocidas (290 g), Mozzarella fresca (55 g), Taro cocido (70 g).

### S02 · Omnívoro, 2200 kcal, 4 comidas

Nutrition 90.1/100 · alternatives 3 · stability {'repeat_same_signature': True, 'plus_1pct_feasible': True, 'plus_1pct_food_jaccard': 0.176}.

- meal_0: Garbanzos cocidos (190 g), Huevo entero (100 g), Guayaba cruda (90 g).
- meal_1: Avena tradicional (45 g), Lentejas cocidas (360 g), Huevo entero (100 g).
- meal_2: Salmón cocido (100 g), Sandía cruda (430 g), Membrillo crudo (50 g).
- meal_3: Lentejas cocidas (250 g), Huevo entero (100 g), Hinojo bulbo crudo (75 g), Champiñón blanco cocido (310 g).

### S03 · Omnívoro, 2600 kcal, 4 comidas

Nutrition 96.5/100 · alternatives 3 · stability not probed.

- meal_0: Arroz blanco cocido (190 g), Requesón bajo en grasa (250 g), Ricotta entera (140 g).
- meal_1: Avena tradicional (40 g), Arvejas de ojo negro cocidas (250 g), Soya cocida (230 g).
- meal_2: Lentejas cocidas (250 g), Nueces (15 g).
- meal_3: Lentejas cocidas (360 g), Queso suizo (55 g).

### S04 · Omnívoro, 3000 kcal, 4 comidas

Nutrition 91.9/100 · alternatives 3 · stability not probed.

- meal_0: Arroz integral cocido (270 g), Palta (95 g), Requesón bajo en grasa (370 g).
- meal_1: Camote cocido (400 g), Pechuga de pollo cocida (200 g), Nueces (30 g), Papa horneada con piel (200 g).
- meal_2: Huevo entero (100 g), Carambola cruda (180 g), Guayaba cruda (330 g).
- meal_3: Lentejas cocidas (360 g), Palta (100 g), Porotos mung cocidos (160 g).

### S05 · Omnívoro, alto en proteína

Nutrition 94.5/100 · alternatives 3 · stability not probed.

- meal_0: Arroz integral cocido (240 g), Pechuga de pollo cocida (140 g), Queso suizo (15 g).
- meal_1: Porotos negros cocidos (330 g), Pechuga de pollo cocida (130 g), Queso suizo (35 g).
- meal_2: Quinoa cocida (140 g), Atún en agua drenado (100 g), Leche entera (150 g).
- meal_3: Lentejas cocidas (270 g), Huevo entero (100 g), Porotos pintos cocidos (90 g).

### S06 · Omnívoro, alto en carbohidratos

Nutrition 95.0/100 · alternatives 3 · stability not probed.

- meal_0: Porotos negros cocidos (210 g), Leche entera (430 g).
- meal_1: Huevo entero (50 g), Soya cocida (180 g), Taro cocido (260 g).
- meal_2: Leche descremada (400 g), Nueces (15 g), Melón calameño crudo (260 g).
- meal_3: Quinoa cocida (300 g), Queso suizo (35 g), Taro cocido (70 g).

### S07 · Vegetariano, 1800 kcal

Nutrition 95.6/100 · alternatives 3 · stability not probed.

- meal_0: Manzana (310 g), Queso suizo (30 g), Requesón bajo en grasa (190 g).
- meal_1: Lentejas cocidas (250 g), Queso suizo (50 g), Habas cocidas (180 g).
- meal_2: Avena tradicional (30 g), Leche descremada (360 g), Queso de cabra semiduro (25 g).
- meal_3: Lentejas cocidas (230 g), Clara de huevo (65 g), Almendras (25 g), Apio crudo (60 g).

### S08 · Vegetariano, 2300 kcal

Nutrition 94.0/100 · alternatives 3 · stability not probed.

- meal_0: Quinoa cocida (190 g), Queso cheddar (35 g), Yogur natural descremado sin azúcar (340 g).
- meal_1: Soya cocida (230 g), Arvejas verdes cocidas (320 g).
- meal_2: Lentejas cocidas (150 g), Yogur natural entero sin azúcar (340 g).
- meal_3: Lentejas cocidas (350 g), Queso suizo (50 g).

### S09 · Vegetariano, alto en proteína

Nutrition 99.3/100 · alternatives 3 · stability not probed.

- meal_0: Huevo entero (85 g), Manzana (330 g), Requesón bajo en grasa (350 g).
- meal_1: Mantequilla con sal (15 g), Requesón bajo en grasa (430 g), Porotos cranberry cocidos (270 g).
- meal_2: Huevo entero (55 g), Manzana (220 g), Requesón bajo en grasa (240 g).
- meal_3: Papa cocida sin piel (250 g), Huevo entero (100 g), Requesón bajo en grasa (340 g).

### S10 · Vegano, 1800 kcal

Nutrition 89.2/100 · alternatives 3 · stability {'repeat_same_signature': True, 'plus_1pct_feasible': True, 'plus_1pct_food_jaccard': 0.333}.

- meal_0: Soya cocida (120 g), Guayaba cruda (270 g).
- meal_1: Papa cocida sin piel (220 g), Soya cocida (210 g), Chirivía cocida (40 g).
- meal_2: Garbanzos cocidos (120 g), Berro crudo (65 g), Habas cocidas (120 g).
- meal_3: Avena tradicional (30 g), Soya cocida (160 g), Repollo blanco crudo (175 g).

### S11 · Vegano, 2300 kcal

Nutrition 88.4/100 · alternatives 3 · stability not probed.

- meal_0: Manzana (260 g), Lupino cocido (260 g).
- meal_1: Porotos pintos cocidos (310 g), Tofu blando (490 g).
- meal_2: Garbanzos cocidos (160 g), Espinaca cruda (100 g), Espárrago crudo (260 g).
- meal_3: Porotos blancos cocidos (210 g), Soya cocida (160 g).

### S12 · Vegano, alto en proteína

Nutrition 92.9/100 · alternatives 3 · stability not probed.

- meal_0: Lupino cocido (330 g), Carambola cruda (180 g).
- meal_1: Garbanzos cocidos (150 g), Espinaca cruda (100 g), Espárrago crudo (260 g), Berro crudo (65 g), Lupino cocido (330 g).
- meal_2: Lupino cocido (240 g), Carambola cruda (175 g).
- meal_3: Avena tradicional (40 g), Lupino cocido (330 g), Repollo blanco crudo (75 g).

### S13 · Pescetariano, 1800 kcal

Nutrition 95.4/100 · alternatives 3 · stability not probed.

- meal_0: Quinoa cocida (100 g), Mantequilla de maní natural (19 g), Yogur natural descremado sin azúcar (340 g).
- meal_1: Porotos negros cocidos (280 g), Huevo entero (100 g), Clara de huevo (65 g), Palta (40 g).
- meal_2: Avena tradicional (35 g), Yogur griego natural sin azúcar (170 g), Palta (30 g).
- meal_3: Quinoa cocida (200 g), Huevo entero (100 g), Repollo de Bruselas crudo (170 g).

### S14 · Pescetariano, 2300 kcal

Nutrition 91.2/100 · alternatives 3 · stability not probed.

- meal_0: Quinoa cocida (180 g), Queso cheddar (35 g), Yogur natural descremado sin azúcar (340 g).
- meal_1: Lentejas cocidas (250 g), Garbanzos cocidos (190 g), Huevo entero (100 g), Clara de huevo (60 g).
- meal_2: Almendras (30 g), Yogur natural descremado sin azúcar (340 g).
- meal_3: Garbanzos cocidos (230 g), Huevo entero (100 g), Clara de huevo (65 g), Zapallo italiano cocido (220 g).

### S15 · Pescetariano, alto en proteína

Nutrition 95.1/100 · alternatives 3 · stability not probed.

- meal_0: Arroz integral cocido (200 g), Huevo entero (75 g), Requesón bajo en grasa (330 g).
- meal_1: Atún en agua drenado (100 g), Porotos adzuki cocidos (250 g), Soya cocida (190 g).
- meal_2: Manzana (200 g), Requesón bajo en grasa (330 g).
- meal_3: Porotos negros cocidos (250 g), Huevo entero (100 g), Centolla cocida (130 g).

### S16 · Alergia a leche

No solution · candidates 19 · reason `cp_sat_infeasible`.

### S17 · Alergia a huevo

Nutrition 93.2/100 · alternatives 3 · stability not probed.

- meal_0: Leche descremada (400 g), Tomate (240 g), Leche semidescremada (250 g), Soya cocida (90 g).
- meal_1: Tomate (240 g), Yogur natural entero sin azúcar (340 g), Soya cocida (110 g), Yogur natural descremado sin azúcar (340 g).
- meal_2: Leche descremada (130 g), Palta (60 g), Yogur natural descremado sin azúcar (340 g).
- meal_3: Tomate (240 g), Yogur natural entero sin azúcar (170 g), Soya cocida (90 g), Yogur natural descremado sin azúcar (340 g).

### S18 · Alergia a frutos secos

Nutrition 93.5/100 · alternatives 3 · stability not probed.

- meal_0: Leche descremada (400 g), Tomate (240 g), Leche semidescremada (250 g), Soya cocida (90 g).
- meal_1: Clara de huevo (35 g), Tomate (240 g), Yogur natural entero sin azúcar (340 g), Soya cocida (90 g), Yogur natural descremado sin azúcar (340 g).
- meal_2: Leche descremada (130 g), Palta (60 g), Yogur natural descremado sin azúcar (340 g).
- meal_3: Tomate (240 g), Yogur natural entero sin azúcar (170 g), Soya cocida (90 g), Yogur natural descremado sin azúcar (340 g).

### S19 · Alergia a soya

No solution · candidates 34 · reason `required_role_group_empty`.

### S20 · Alergia a pescado

Nutrition 93.5/100 · alternatives 3 · stability not probed.

- meal_0: Leche descremada (400 g), Tomate (240 g), Leche semidescremada (250 g), Soya cocida (90 g).
- meal_1: Clara de huevo (35 g), Tomate (240 g), Yogur natural entero sin azúcar (340 g), Soya cocida (90 g), Yogur natural descremado sin azúcar (340 g).
- meal_2: Leche descremada (130 g), Palta (60 g), Yogur natural descremado sin azúcar (340 g).
- meal_3: Tomate (240 g), Yogur natural entero sin azúcar (170 g), Soya cocida (90 g), Yogur natural descremado sin azúcar (340 g).

### S21 · Vegano y alergia a soya

No solution · candidates 5 · reason `required_role_group_empty`.

### S22 · Vegetariano y alergia a leche

No solution · candidates 11 · reason `cp_sat_infeasible`.

### S23 · Sin pollo

Nutrition 92.3/100 · alternatives 3 · stability {'repeat_same_signature': True, 'plus_1pct_feasible': True, 'plus_1pct_food_jaccard': 0.273}.

- meal_0: Lentejas cocidas (320 g), Queso de cabra semiduro (45 g).
- meal_1: Lentejas cocidas (360 g), Mozzarella fresca (55 g).
- meal_2: Lentejas cocidas (190 g), Queso suizo (30 g).
- meal_3: Avena tradicional (80 g), Salmón cocido (120 g).

### S24 · Sin arroz

Nutrition 95.9/100 · alternatives 3 · stability not probed.

- meal_0: Quinoa cocida (250 g), Huevo entero (85 g), Requesón bajo en grasa (130 g).
- meal_1: Quinoa cocida (170 g), Arvejas partidas cocidas (180 g), Tofu blando (430 g).
- meal_2: Carne magra cocida (90 g), Membrillo crudo (170 g), Carambola cruda (175 g).
- meal_3: Lentejas cocidas (310 g), Huevo entero (100 g), Betarraga cocida (45 g).

### S25 · Prefiere legumbres

Nutrition 90.6/100 · alternatives 3 · stability not probed.

- meal_0: Lentejas cocidas (280 g), Queso suizo (45 g).
- meal_1: Lentejas cocidas (360 g), Huevo entero (100 g).
- meal_2: Lentejas cocidas (190 g), Queso suizo (30 g).
- meal_3: Lentejas cocidas (330 g), Huevo entero (100 g).

### S26 · Poco tiempo para cocinar

Nutrition 86.8/100 · alternatives 3 · stability not probed.

- meal_0: Lentejas cocidas (220 g), Leche entera (400 g).
- meal_1: Lentejas cocidas (360 g), Huevo entero (100 g).
- meal_2: Lentejas cocidas (170 g), Palta (60 g), Arándanos (45 g).
- meal_3: Lentejas cocidas (320 g), Huevo entero (100 g).

### S27 · Presupuesto bajo

Nutrition 91.7/100 · alternatives 3 · stability {'repeat_same_signature': True, 'plus_1pct_feasible': True, 'plus_1pct_food_jaccard': 0.357}.

- meal_0: Quinoa cocida (120 g), Ricotta entera (110 g), Yogur natural descremado sin azúcar (340 g).
- meal_1: Arvejas de ojo negro cocidas (280 g), Soya cocida (200 g).
- meal_2: Quinoa cocida (100 g), Yogur natural entero sin azúcar (340 g).
- meal_3: Lentejas cocidas (320 g), Huevo entero (100 g).

### S28 · Vegano, poco tiempo y bajo presupuesto

Nutrition 93.7/100 · alternatives 3 · stability not probed.

- meal_0: Quinoa cocida (210 g), Lupino cocido (180 g), Clementina cruda (40 g).
- meal_1: Avena tradicional (35 g), Soya cocida (230 g), Alcachofa cocida (240 g).
- meal_2: Soya cocida (110 g), Papaya cruda (270 g).
- meal_3: Garbanzos cocidos (200 g), Tofu firme (250 g).

### S29 · Vegetariano, sin huevos ni lácteos por exclusión

Nutrition 95.1/100 · alternatives 3 · stability not probed.

- meal_0: Porotos negros cocidos (180 g), Espinaca cruda (100 g), Espárrago crudo (260 g), Mozzarella fresca (55 g).
- meal_1: Porotos pintos cocidos (290 g), Tofu blando (430 g).
- meal_2: Piña cruda (210 g), Soya cocida (120 g).
- meal_3: Soya cocida (200 g), Repollo blanco crudo (175 g), Chirivía cocida (155 g).

### S30 · Omnívoro, sin carnes ni pescados por exclusión

Nutrition 95.3/100 · alternatives 3 · stability not probed.

- meal_0: Papa cocida sin piel (220 g), Yogur griego natural sin azúcar (340 g), Mantequilla sin sal (15 g).
- meal_1: Papa cocida sin piel (210 g), Soya cocida (210 g), Habas cocidas (200 g).
- meal_2: Avena tradicional (20 g), Yogur natural entero sin azúcar (170 g), Yogur natural descremado sin azúcar (340 g).
- meal_3: Quinoa cocida (280 g), Huevo entero (100 g), Camarón cocido (65 g).
