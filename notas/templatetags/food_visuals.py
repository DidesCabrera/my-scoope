from django import template

from core.food_visual_identity import resolved_food_visual_identity

register = template.Library()


@register.filter
def food_visual_emoji(name):
    return resolved_food_visual_identity(str(name or "")).emoji
