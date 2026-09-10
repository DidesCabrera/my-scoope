def meal_simulation(*, food_id: int, food_name: str) -> dict:
    return {
        "intent": "create_meal",
        "meal": {
            "name": "Desayuno AI",
            "foods": [
                {
                    "food_id": food_id,
                    "food_name": food_name,
                    "quantity": 100,
                    "unit": "g",
                    "protein": 13,
                    "carbs": 68,
                    "fat": 7,
                    "total_kcal": 387,
                }
            ],
            "kpis": {
                "protein": 13,
                "carbs": 68,
                "fat": 7,
                "total_kcal": 387,
                "alloc_protein": 13.4,
                "alloc_carbs": 70.3,
                "alloc_fat": 16.3,
            },
        },
        "dailyplan": None,
    }
