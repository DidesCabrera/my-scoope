"""Curated daily plans built from the published meal catalog."""

STARTER_DAILYPLAN_CATALOG = (
    {
        "name": "Día cotidiano con pollo",
        "dietary_style": "omnivore",
        "summary": "Desayuno, almuerzo y cena para un día cotidiano.",
        "meals": (("Huevos con palta y tomate", "08:00"), ("Pollo con arroz y brócoli", "13:00"), ("Pavo con camote y zapallo italiano", "20:00")),
    },
    {
        "name": "Día omnívoro con colación",
        "dietary_style": "omnivore",
        "summary": "Cuatro momentos con comidas sencillas y una colación.",
        "meals": (("Avena con yogur, plátano y arándanos", "08:00"), ("Carne magra con papa y ensalada", "13:00"), ("Yogur con frutos rojos", "17:00"), ("Pollo con quinoa y espinaca", "20:00")),
    },
    {
        "name": "Día con pescado y verduras",
        "dietary_style": "pescatarian",
        "summary": "Tres comidas con pescado, cereales y verduras.",
        "meals": (("Bowl de quinoa, frutilla y almendras", "08:00"), ("Salmón con quinoa y espárragos", "13:00"), ("Bacalao con papa y kale", "20:00")),
    },
    {
        "name": "Día pescetariano con colación",
        "dietary_style": "pescatarian",
        "summary": "Cuatro comidas con pescado y una colación salada.",
        "meals": (("Avena con yogur, plátano y arándanos", "08:00"), ("Atún con arroz, tomate y palta", "13:00"), ("Atún con palta y pepino", "17:00"), ("Trucha con papa y espárragos", "20:00")),
    },
    {
        "name": "Día vegetariano sencillo",
        "dietary_style": "vegetarian",
        "summary": "Tres comidas con legumbres, huevo y verduras.",
        "meals": (("Huevos con palta y tomate", "08:00"), ("Lentejas con quinoa y verduras", "13:00"), ("Omelette de champiñones y queso", "20:00")),
    },
    {
        "name": "Día vegetariano con colación",
        "dietary_style": "vegetarian",
        "summary": "Cuatro momentos con fruta, legumbres y huevo.",
        "meals": (("Yogur con manzana y nueces", "08:00"), ("Garbanzos con camote y espinaca", "13:00"), ("Huevo, mandarina y almendras", "17:00"), ("Lentejas con huevo y espinaca", "20:00")),
    },
    {
        "name": "Día vegetal de tres comidas",
        "dietary_style": "vegan",
        "summary": "Tres comidas vegetales con tofu y legumbres.",
        "meals": (("Tofu revuelto con espinaca y tomate", "08:00"), ("Lentejas con quinoa y verduras", "13:00"), ("Tofu con arroz y brócoli", "20:00")),
    },
    {
        "name": "Día vegetal con colación",
        "dietary_style": "vegan",
        "summary": "Cuatro momentos vegetales con una colación de fruta.",
        "meals": (("Avena con plátano y mantequilla de maní", "08:00"), ("Tempeh con quinoa y pimentón", "13:00"), ("Manzana con mantequilla de maní", "17:00"), ("Porotos negros con arroz y palta", "20:00")),
    },
)
