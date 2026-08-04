from notas.application.services.food_imports.aliases import FoodAliasInput

USDA_SPANISH_ALIAS_CATALOG = {
    "oats raw": [
        FoodAliasInput(name="Avena", language="es", country="CL"),
        FoodAliasInput(name="Avena cruda", language="es", country="CL"),
        FoodAliasInput(name="Avena integral", language="es", country="CL"),
    ],
    "chicken breast cooked": [
        FoodAliasInput(name="Pechuga de pollo", language="es", country="CL"),
        FoodAliasInput(name="Pechuga de pollo cocida", language="es", country="CL"),
        FoodAliasInput(name="Pollo cocido", language="es", country="CL"),
    ],
    "eggs grade a large egg whole": [
        FoodAliasInput(name="Huevo", language="es", country="CL"),
        FoodAliasInput(name="Huevos", language="es", country="CL"),
        FoodAliasInput(name="Huevo entero", language="es", country="CL"),
        FoodAliasInput(name="Huevo grande", language="es", country="CL"),
    ],
    "rice white long grain unenriched raw": [
        FoodAliasInput(name="Arroz", language="es", country="CL"),
        FoodAliasInput(name="Arroz blanco", language="es", country="CL"),
        FoodAliasInput(name="Arroz blanco crudo", language="es", country="CL"),
        FoodAliasInput(name="Arroz crudo", language="es", country="CL"),
    ],
    "rice brown long grain unenriched raw": [
        FoodAliasInput(name="Arroz integral", language="es", country="CL"),
        FoodAliasInput(name="Arroz integral crudo", language="es", country="CL"),
        FoodAliasInput(name="Arroz café", language="es", country="CL"),
        FoodAliasInput(name="Arroz cafe", language="es", country="CL"),
    ],
    "nuts almonds whole raw": [
        FoodAliasInput(name="Almendra", language="es", country="CL"),
        FoodAliasInput(name="Almendras", language="es", country="CL"),
        FoodAliasInput(name="Almendras crudas", language="es", country="CL"),
    ],
    "kale raw": [
        FoodAliasInput(name="Kale", language="es", country="CL"),
        FoodAliasInput(name="Kale crudo", language="es", country="CL"),
        FoodAliasInput(name="Col rizada", language="es", country="CL"),
    ],
    "hummus commercial": [
        FoodAliasInput(name="Hummus", language="es", country="CL"),
        FoodAliasInput(name="Humus", language="es", country="CL"),
    ],
}