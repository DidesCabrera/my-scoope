"""Curated starter content for the My Scoope meal catalog.

The manifest references operational ``notas.Food`` names on purpose: catalog
meals are ordinary Meals and therefore keep the same nutritional snapshot
boundary as every other composition in the product.
"""

STARTER_MEAL_CATALOG = (
    {
        "name": "Avena con yogur, plátano y arándanos",
        "occasion": "breakfast", "dietary_style": "vegetarian",
        "summary": "Desayuno cremoso con fruta y una base simple para días activos.",
        "foods": (("Avena tradicional", 50), ("Yogur griego natural sin azúcar", 180), ("Plátano", 100), ("Arándanos", 80)),
    },
    {
        "name": "Huevos con palta y tomate",
        "occasion": "breakfast", "dietary_style": "vegetarian",
        "summary": "Desayuno salado, rápido y con pocos ingredientes.",
        "foods": (("Huevo entero", 120), ("Palta", 70), ("Tomate", 120)),
    },
    {
        "name": "Bowl de quinoa, frutilla y almendras",
        "occasion": "breakfast", "dietary_style": "vegetarian",
        "summary": "Alternativa fresca de desayuno con quinoa, fruta y frutos secos.",
        "foods": (("Quinoa cocida", 180), ("Yogur natural descremado sin azúcar", 150), ("Frutilla cruda", 120), ("Almendras", 20)),
    },
    {
        "name": "Tofu revuelto con espinaca y tomate",
        "occasion": "breakfast", "dietary_style": "vegan",
        "summary": "Desayuno vegetal y salado para variar los formatos de la mañana.",
        "foods": (("Tofu firme", 180), ("Espinaca cruda", 80), ("Tomate", 120), ("Aceite de oliva", 8)),
    },
    {
        "name": "Yogur con manzana y nueces",
        "occasion": "breakfast", "dietary_style": "vegetarian",
        "summary": "Combinación sencilla de yogur, fruta y textura crocante.",
        "foods": (("Yogur griego natural sin azúcar", 200), ("Manzana con piel cruda", 140), ("Nueces", 20)),
    },
    {
        "name": "Avena con plátano y mantequilla de maní",
        "occasion": "breakfast", "dietary_style": "vegan",
        "summary": "Desayuno vegetal con ingredientes fáciles de mantener en despensa.",
        "foods": (("Avena tradicional", 60), ("Plátano", 120), ("Mantequilla de maní natural", 25)),
    },
    {
        "name": "Manzana con mantequilla de maní",
        "occasion": "snack", "dietary_style": "vegan",
        "summary": "Colación portátil con fruta fresca y mantequilla de maní.",
        "foods": (("Manzana con piel cruda", 160), ("Mantequilla de maní natural", 25)),
    },
    {
        "name": "Yogur con frutos rojos",
        "occasion": "snack", "dietary_style": "vegetarian",
        "summary": "Colación fresca con yogur, frutilla, frambuesa y arándanos.",
        "foods": (("Yogur griego natural sin azúcar", 180), ("Frutilla cruda", 80), ("Frambuesa cruda", 60), ("Arándanos", 50)),
    },
    {
        "name": "Garbanzos con bastones de verduras",
        "occasion": "snack", "dietary_style": "vegan",
        "summary": "Colación salada inspirada en hummus con verduras crujientes.",
        "foods": (("Garbanzos cocidos", 120), ("Zanahoria cruda", 100), ("Pepino con piel crudo", 100), ("Aceite de oliva", 8)),
    },
    {
        "name": "Huevo, mandarina y almendras",
        "occasion": "snack", "dietary_style": "vegetarian",
        "summary": "Colación mixta que combina un formato salado, fruta y frutos secos.",
        "foods": (("Huevo entero", 100), ("Mandarina cruda", 140), ("Almendras", 18)),
    },
    {
        "name": "Atún con palta y pepino",
        "occasion": "snack", "dietary_style": "pescatarian",
        "summary": "Colación salada con pescado, palta y verduras frescas.",
        "foods": (("Atún en agua drenado", 100), ("Palta", 60), ("Pepino con piel crudo", 120)),
    },
    {
        "name": "Dátiles con nueces y almendras",
        "occasion": "snack", "dietary_style": "vegan",
        "summary": "Colación de despensa para cuando se necesita una opción compacta.",
        "foods": (("Dátil seco", 45), ("Nueces", 20), ("Almendras", 20)),
    },
    {
        "name": "Pollo con arroz y brócoli",
        "occasion": "lunch", "dietary_style": "omnivore",
        "summary": "Almuerzo cotidiano de pollo, arroz y verduras.",
        "foods": (("Pechuga de pollo cocida", 170), ("Arroz blanco cocido", 220), ("Brócoli cocido", 150), ("Aceite de oliva", 8)),
    },
    {
        "name": "Carne magra con papa y ensalada",
        "occasion": "lunch", "dietary_style": "omnivore",
        "summary": "Plato de carne magra con papa y verduras frescas.",
        "foods": (("Carne magra cocida", 170), ("Papa cocida sin piel", 250), ("Lechuga costina cruda", 80), ("Tomate", 120), ("Aceite de oliva", 8)),
    },
    {
        "name": "Salmón con quinoa y espárragos",
        "occasion": "lunch", "dietary_style": "pescatarian",
        "summary": "Almuerzo de pescado con quinoa y verduras verdes.",
        "foods": (("Salmón cocido", 170), ("Quinoa cocida", 200), ("Espárrago cocido", 150)),
    },
    {
        "name": "Atún con arroz, tomate y palta",
        "occasion": "lunch", "dietary_style": "pescatarian",
        "summary": "Bowl práctico de atún con arroz y vegetales frescos.",
        "foods": (("Atún en agua drenado", 140), ("Arroz integral cocido", 220), ("Tomate", 120), ("Palta", 70)),
    },
    {
        "name": "Lentejas con quinoa y verduras",
        "occasion": "lunch", "dietary_style": "vegan",
        "summary": "Almuerzo vegetal de legumbres, cereal y verduras cocidas.",
        "foods": (("Lentejas cocidas", 220), ("Quinoa cocida", 160), ("Zanahoria cocida", 100), ("Zapallo italiano cocido", 120), ("Aceite de oliva", 8)),
    },
    {
        "name": "Garbanzos con camote y espinaca",
        "occasion": "lunch", "dietary_style": "vegan",
        "summary": "Bowl vegetal de garbanzos, camote y hojas verdes.",
        "foods": (("Garbanzos cocidos", 200), ("Camote cocido", 220), ("Espinaca cocida", 100), ("Aceite de oliva", 8)),
    },
    {
        "name": "Tofu con arroz y brócoli",
        "occasion": "lunch", "dietary_style": "vegan",
        "summary": "Almuerzo vegetal inspirado en un salteado simple.",
        "foods": (("Tofu firme", 200), ("Arroz integral cocido", 220), ("Brócoli cocido", 150), ("Aceite de oliva", 8)),
    },
    {
        "name": "Tempeh con quinoa y pimentón",
        "occasion": "lunch", "dietary_style": "vegan",
        "summary": "Bowl vegetal con tempeh, quinoa y pimentón.",
        "foods": (("Tempeh cocido", 180), ("Quinoa cocida", 200), ("Pimentón rojo crudo", 120), ("Espinaca cruda", 70), ("Aceite de oliva", 8)),
    },
    {
        "name": "Porotos negros con arroz y palta",
        "occasion": "lunch", "dietary_style": "vegan",
        "summary": "Almuerzo vegetal de legumbres con arroz y vegetales frescos.",
        "foods": (("Porotos negros cocidos", 210), ("Arroz blanco cocido", 200), ("Palta", 70), ("Tomate", 100)),
    },
    {
        "name": "Pavo con camote y zapallo italiano",
        "occasion": "dinner", "dietary_style": "omnivore",
        "summary": "Cena de pavo con tubérculo y verduras cocidas.",
        "foods": (("Pechuga de pavo cocida", 170), ("Camote cocido", 220), ("Zapallo italiano cocido", 160), ("Aceite de oliva", 8)),
    },
    {
        "name": "Pollo con quinoa y espinaca",
        "occasion": "dinner", "dietary_style": "omnivore",
        "summary": "Cena sencilla de pollo con quinoa y hojas verdes.",
        "foods": (("Pechuga de pollo cocida", 170), ("Quinoa cocida", 190), ("Espinaca cocida", 120), ("Aceite de oliva", 8)),
    },
    {
        "name": "Bacalao con papa y kale",
        "occasion": "dinner", "dietary_style": "pescatarian",
        "summary": "Cena de pescado blanco con papa y verduras verdes.",
        "foods": (("Bacalao crudo", 190), ("Papa cocida sin piel", 240), ("Kale cocido", 120), ("Aceite de oliva", 8)),
    },
    {
        "name": "Camarones con arroz y verduras",
        "occasion": "dinner", "dietary_style": "pescatarian",
        "summary": "Cena de camarones con arroz y verduras coloridas.",
        "foods": (("Camarón cocido", 180), ("Arroz blanco cocido", 210), ("Pimentón rojo crudo", 100), ("Zapallo italiano cocido", 120), ("Aceite de oliva", 8)),
    },
    {
        "name": "Trucha con papa y espárragos",
        "occasion": "dinner", "dietary_style": "pescatarian",
        "summary": "Cena de trucha acompañada de papa y espárragos.",
        "foods": (("Trucha arcoíris cruda", 190), ("Papa cocida sin piel", 230), ("Espárrago cocido", 150)),
    },
    {
        "name": "Lentejas con huevo y espinaca",
        "occasion": "dinner", "dietary_style": "vegetarian",
        "summary": "Cena vegetariana de legumbres, huevo y hojas verdes.",
        "foods": (("Lentejas cocidas", 220), ("Huevo entero", 100), ("Espinaca cocida", 100), ("Aceite de oliva", 8)),
    },
    {
        "name": "Omelette de champiñones y queso",
        "occasion": "dinner", "dietary_style": "vegetarian",
        "summary": "Cena vegetariana compacta con huevo, champiñones y queso.",
        "foods": (("Huevo entero", 150), ("Champiñón blanco cocido", 120), ("Espinaca cruda", 70), ("Mozzarella fresca", 50)),
    },
    {
        "name": "Plátano con avena pre-entreno",
        "occasion": "pre_workout", "dietary_style": "vegan",
        "summary": "Opción simple basada en carbohidratos para antes de entrenar.",
        "foods": (("Plátano", 140), ("Avena tradicional", 45), ("Dátil seco", 25)),
    },
    {
        "name": "Pollo con arroz post-entreno",
        "occasion": "post_workout", "dietary_style": "omnivore",
        "summary": "Comida práctica de recuperación con pollo, arroz y fruta.",
        "foods": (("Pechuga de pollo cocida", 170), ("Arroz blanco cocido", 240), ("Piña cruda", 120)),
    },
)

