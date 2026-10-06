"""Canonical persisted planning values shared by onboarding and nutrition intake."""

NUTRITION_GOAL_CHOICES = (
    ("fat_loss", "Bajar grasa"),
    ("muscle_gain", "Ganar masa muscular"),
    ("maintenance", "Mantención"),
    ("performance", "Rendimiento deportivo"),
    ("healthy_eating", "Comer mejor"),
)

ACTIVITY_LEVEL_CHOICES = (
    ("sedentary", "Sedentaria"),
    ("light", "Ligera"),
    ("moderate", "Moderada"),
    ("high", "Alta"),
    ("very_high", "Muy alta"),
)

NUTRITION_GOAL_VALUES = frozenset(value for value, _label in NUTRITION_GOAL_CHOICES)
ACTIVITY_LEVEL_VALUES = frozenset(value for value, _label in ACTIVITY_LEVEL_CHOICES)
