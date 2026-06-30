from dataclasses import dataclass


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
