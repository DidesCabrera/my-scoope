from copy import deepcopy
from dataclasses import dataclass

from django.urls import reverse


@dataclass
class ProposalEntityDetailContentVM:
    header: object
    proposal: dict
    proposal_review: dict
    entity_kind: str
    entity_name: str
    main_card: dict
    child_cards: list
    structural_indicators: dict
    foods_aggregation: list


class ProposalProgramNavigationError(ValueError):
    pass


def build_program_proposal_navigation_content(
    proposal_review: dict,
    *,
    proposal_id: int,
    week_number: int,
    day_number: int,
    meal_number: int | None = None,
    food_number: int | None = None,
) -> dict:
    payload = proposal_review.get("payload") or {}
    program = payload.get("program") or {}
    week = next((item for item in program.get("weeks") or [] if item.get("week_number") == week_number), None)
    day = next((item for item in (week or {}).get("days") or [] if item.get("day_number") == day_number), None)
    dailyplan = (day or {}).get("dailyplan_detail") or {}
    if not week or not day or not dailyplan:
        raise ProposalProgramNavigationError("program_proposal_dailyplan_not_found")

    context = {
        "proposal_id": proposal_id,
        "program_name": program.get("name") or "Programa propuesto",
        "week_number": week_number,
        "day_number": day_number,
        "day_label": day.get("day_label") or f"Día {day_number}",
        "dailyplan_name": dailyplan.get("name") or "Plan diario propuesto",
    }
    meals = dailyplan.get("meals") or []

    if meal_number is None:
        main_card = _card_without_actions(dailyplan.get("card"))
        child_cards = []
        for index, meal in enumerate(meals, start=1):
            card = _card_with_navigation_action(
                meal.get("meal", {}).get("card"),
                card_id=f"proposal-program-{proposal_id}-w{week_number}-d{day_number}-meal-{index}",
                label="Explorar comida",
                url=reverse("proposal_program_meal_detail", args=[proposal_id, week_number, day_number, index]),
                hour=meal.get("hour") or "",
            )
            if card:
                child_cards.append({"card": card})
        return {**context, "entity_kind": "dailyplan", "entity_name": context["dailyplan_name"],
                "main_card": main_card, "child_cards": child_cards, "foods_count": _dailyplan_food_count(meals)}

    if meal_number < 1 or meal_number > len(meals):
        raise ProposalProgramNavigationError("program_proposal_meal_not_found")
    meal_item = meals[meal_number - 1]
    meal = meal_item.get("meal") or {}
    context.update({"meal_number": meal_number, "meal_name": meal.get("name") or "Comida propuesta",
                    "meal_hour": meal_item.get("hour") or "", "meal_note": meal_item.get("note") or ""})
    foods = meal.get("foods") or []

    if food_number is None:
        main_card = _card_without_actions(meal.get("card"))
        _set_card_hour(main_card, context["meal_hour"])
        child_cards = [
            _build_proposed_food_card(
                food,
                card_id=f"proposal-program-{proposal_id}-w{week_number}-d{day_number}-m{meal_number}-food-{index}",
                detail_url=reverse("proposal_program_food_detail", args=[proposal_id, week_number, day_number, meal_number, index]),
            )
            for index, food in enumerate(foods, start=1)
        ]
        return {**context, "entity_kind": "meal", "entity_name": context["meal_name"],
                "main_card": main_card, "child_cards": child_cards, "foods_count": len(foods)}

    if food_number < 1 or food_number > len(foods):
        raise ProposalProgramNavigationError("program_proposal_food_not_found")
    food = foods[food_number - 1]
    context.update({"food_number": food_number, "food_name": food.get("food_name") or "Alimento propuesto"})
    return {**context, "entity_kind": "food", "entity_name": context["food_name"],
            "main_card": _build_proposed_food_card(food, card_id=f"proposal-program-{proposal_id}-food-detail", detail_url=""),
            "child_cards": [], "foods_count": 1}


def _card_without_actions(card: dict | None) -> dict:
    if not isinstance(card, dict):
        return {}
    result = deepcopy(card)
    result["actions"] = []
    return result


def _card_with_navigation_action(
    card: dict | None,
    *,
    card_id: str,
    label: str,
    url: str,
    hour: str = "",
) -> dict:
    result = _card_without_actions(card)
    if not result:
        return {}
    result.update({"id": card_id, "main_id": card_id, "actions": [{
        "key": "open_proposed_entity", "label": label, "icon": "arrow-right", "url": url,
        "method": "get", "desktop_position": "inline", "mobile_position": "inline",
    }]})
    _set_card_hour(result, hour)
    return result


def _set_card_hour(card: dict, hour: str) -> None:
    if not card or not hour:
        return
    card.setdefault("titulo", {}).setdefault("structural_indicators", {})["hour"] = hour


def _build_proposed_food_card(food: dict, *, card_id: str, detail_url: str) -> dict:
    protein = float(food.get("protein") or 0)
    carbs = float(food.get("carbs") or 0)
    fat = float(food.get("fat") or 0)
    total_kcal = float(food.get("total_kcal") or protein * 4 + carbs * 4 + fat * 9)
    actions = [{"key": "open_proposed_food", "label": "Explorar alimento", "icon": "arrow-right",
                "url": detail_url, "method": "get", "desktop_position": "inline", "mobile_position": "inline"}] if detail_url else []
    return {
        "id": card_id,
        "titulo": {"name": food.get("food_name") or "Alimento", "label": "Alimento", "icon": "carrot",
                   "category_badge": None, "classes": [], "structural_indicators": {}},
        "kpis": {"tot_kcal": total_kcal, "g_protein": protein, "g_carbs": carbs, "g_fat": fat,
                 "kcal_protein": protein * 4, "kcal_carbs": carbs * 4, "kcal_fat": fat * 9,
                 "alloc_protein": protein * 4 / total_kcal * 100 if total_kcal else 0,
                 "alloc_carbs": carbs * 4 / total_kcal * 100 if total_kcal else 0,
                 "alloc_fat": fat * 9 / total_kcal * 100 if total_kcal else 0, "ppk": 0},
        "related_data": {"quantity": food.get("quantity"), "unit": food.get("unit") or "g"},
        "metadata": {"owner": "AI", "author": "AI", "fork_from": None},
        "actions": actions,
    }


def _dailyplan_food_count(meals: list[dict]) -> int:
    return sum(len((item.get("meal") or {}).get("foods") or []) for item in meals)


def build_proposal_entity_content(proposal_review: dict) -> dict:
    payload = proposal_review.get("payload") or {}
    entity_kind = _proposal_entity_kind(proposal_review)
    entity_name = _proposal_entity_name(proposal_review)

    if entity_kind == "meal":
        meal = payload.get("meal") or {}
        main_card = _strip_proposal_entity_actions(meal.get("card"))
        return {
            "entity_kind": entity_kind,
            "entity_name": entity_name,
            "main_card": main_card,
            "child_cards": [],
            "structural_indicators": {},
            "foods_aggregation": [],
        }

    if entity_kind == "dailyplan":
        dailyplan = payload.get("dailyplan") or {}
        main_card = _strip_proposal_entity_actions(dailyplan.get("card"))
        child_cards = _build_dailyplan_child_cards_for_proposal_entity(
            proposal_review,
        )
        structural_indicators = {
            "meals_count": len(child_cards),
            "foods_count": (
                main_card.get("titulo", {})
                .get("structural_indicators", {})
                .get("foods_count", 0)
            ),
        }

        foods = []
        seen = set()
        for child in child_cards:
            for food in child.get("foods_aggregation") or []:
                name = food.get("display_name")
                if not name or name in seen:
                    continue
                seen.add(name)
                foods.append(food)

        return {
            "entity_kind": entity_kind,
            "entity_name": entity_name,
            "main_card": main_card,
            "child_cards": child_cards,
            "structural_indicators": structural_indicators,
            "foods_aggregation": foods,
        }

    return {
        "entity_kind": entity_kind,
        "entity_name": entity_name,
        "main_card": {},
        "child_cards": [],
        "structural_indicators": {},
        "foods_aggregation": [],
    }


def _proposal_entity_name(proposal_review: dict) -> str:
    payload = proposal_review.get("payload") or {}

    if payload.get("is_create_meal") and payload.get("meal"):
        return payload["meal"].get("name") or "Comida propuesta"

    if payload.get("is_create_dailyplan") and payload.get("dailyplan"):
        return payload["dailyplan"].get("name") or "DailyPlan propuesto"

    return "Entidad propuesta"


def _proposal_entity_kind(proposal_review: dict) -> str:
    payload = proposal_review.get("payload") or {}

    if payload.get("is_create_meal") and payload.get("meal"):
        return "meal"

    if payload.get("is_create_dailyplan") and payload.get("dailyplan"):
        return "dailyplan"

    return "unsupported"


def _strip_proposal_entity_actions(card: dict | None) -> dict:
    if not isinstance(card, dict):
        return {}

    clean_card = dict(card)
    clean_card["actions"] = []
    return clean_card


def _build_dailyplan_child_cards_for_proposal_entity(proposal_review: dict) -> list[dict]:
    payload = proposal_review.get("payload") or {}
    dailyplan = payload.get("dailyplan") or {}
    child_cards = []

    for index, item in enumerate(dailyplan.get("meals") or [], start=1):
        meal = item.get("meal") or {}
        card = _strip_proposal_entity_actions(meal.get("card"))

        if not card:
            continue

        card.setdefault("id", f"proposal-dailyplan-meal-{index}")
        card.setdefault("main_id", card["id"])
        child_cards.append(card)

    return child_cards
