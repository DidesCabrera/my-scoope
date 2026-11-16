"""Serialize the result of a saved nutrition-label capture."""


def food_label_capture_payload(result) -> dict:
    food = result.food
    receipt = result.receipt
    return {
        "id": food.id,
        "name": food.name,
        "protein_g": food.protein,
        "carbs_g": food.carbs,
        "fat_g": food.fat,
        "saturated_fat_g": float(food.saturated_fat_g_per_100g) if food.saturated_fat_g_per_100g is not None else None,
        "sugar_g": float(food.sugar_g_per_100g) if food.sugar_g_per_100g is not None else None,
        "fiber_g": float(food.fiber_g_per_100g) if food.fiber_g_per_100g is not None else None,
        "sodium_mg": float(food.sodium_mg_per_100g) if food.sodium_mg_per_100g is not None else None,
        "total_kcal": food.total_kcal,
        "is_user_food": food.created_by_id is not None and not food.is_global,
        "is_verified": food.is_verified,
        "capture_receipt_id": receipt.id,
        "detected_basis": receipt.detected_basis,
        "serving_size_g": float(receipt.serving_size_g) if receipt.serving_size_g is not None else None,
        "portion_unit": food.portion_unit,
        "ocr_engine": receipt.ocr_engine,
        "label_image_retained": bool(receipt.retained_label_image),
        "shared_for_curation": receipt.shared_for_curation,
        "created_at": receipt.created_at,
    }
