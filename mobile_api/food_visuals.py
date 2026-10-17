from core.food_visual_identity import resolved_food_visual_identity
from notas.application.services.food_imports.localized_names import resolve_food_display_name


def food_visual_payload(food=None, *, name: str = "") -> dict[str, str]:
    display_name = name or resolve_food_display_name(food)
    visual = resolved_food_visual_identity(
        display_name,
        emoji=getattr(food, "emoji", ""),
        visual_key=getattr(food, "visual_key", ""),
        food_group=getattr(food, "food_group", ""),
        food_subgroup=getattr(food, "food_subgroup", ""),
    )
    return {
        "name": display_name,
        "emoji": visual.emoji,
        "visual_key": visual.visual_key,
    }


__all__ = ["food_visual_payload"]
