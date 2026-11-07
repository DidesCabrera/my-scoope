def _snapshot_food_relation_id(food: dict) -> int | None:
    food_key = food.get("key")
    if not isinstance(food_key, str):
        return None
    for prefix in ("meal_food:", "source_meal_food:"):
        if food_key.startswith(prefix):
            try:
                return int(food_key.removeprefix(prefix))
            except ValueError:
                return None
    return None


def index_snapshot_food(
    food: object,
    *,
    foods_by_source_id: dict[int, list[dict]],
    foods_by_relation_id: dict[int, list[dict]],
) -> None:
    if not isinstance(food, dict):
        return
    food.pop("detail_id", None)
    source_food_id = food.get("source_food_id")
    if isinstance(source_food_id, int):
        foods_by_source_id.setdefault(source_food_id, []).append(food)
        return
    relation_id = _snapshot_food_relation_id(food)
    if relation_id is not None:
        foods_by_relation_id.setdefault(relation_id, []).append(food)
