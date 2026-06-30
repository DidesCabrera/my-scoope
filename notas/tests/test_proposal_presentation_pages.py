from django.test import SimpleTestCase
from django.urls import reverse

from notas.presentation.proposals.entity_page import build_proposal_entity_content
from notas.presentation.proposals.list_page import (
    build_proposal_list_actions,
    normalize_proposal_list_mode,
    proposal_list_url,
    resolve_proposal_list_status_filter,
)


class ProposalListPageViewModelTests(SimpleTestCase):
    def test_status_filter_accepts_only_supported_statuses(self):
        self.assertEqual(
            resolve_proposal_list_status_filter(
                get_status="pending_review",
                post_status=None,
            ),
            "pending_review",
        )
        self.assertEqual(
            resolve_proposal_list_status_filter(
                get_status=None,
                post_status="applied",
            ),
            "applied",
        )
        self.assertIsNone(
            resolve_proposal_list_status_filter(
                get_status="approved",
                post_status=None,
            )
        )

    def test_list_mode_accepts_only_supported_modes(self):
        self.assertEqual(normalize_proposal_list_mode("reorder"), "reorder")
        self.assertEqual(normalize_proposal_list_mode("delete"), "delete")
        self.assertEqual(normalize_proposal_list_mode("unexpected"), "list")

    def test_proposal_list_url_keeps_status_and_mode_contract(self):
        self.assertEqual(proposal_list_url(), reverse("proposal_list"))
        self.assertEqual(
            proposal_list_url(mode="reorder", status_filter="pending_review"),
            f'{reverse("proposal_list")}?mode=reorder&status=pending_review',
        )

    def test_default_actions_include_modes_and_filters(self):
        actions = build_proposal_list_actions("pending_review", "list")
        keys = {action["key"] for action in actions}

        self.assertIn("enter_reorder_mode", keys)
        self.assertIn("enter_delete_mode", keys)
        self.assertIn("filter_applied", keys)
        self.assertIn("filter_rejected", keys)

        pending_filter = next(
            action for action in actions if action["key"] == "filter_pending_review"
        )
        self.assertEqual(pending_filter["extra_class"], "is-active")

    def test_delete_mode_actions_keep_bulk_delete_disabled_until_selection(self):
        actions = build_proposal_list_actions("applied", "delete")
        bulk_delete = next(action for action in actions if action["key"] == "bulk_delete")

        self.assertTrue(bulk_delete["disabled"])
        self.assertIn("status=applied", bulk_delete["url"])


class ProposalEntityPageViewModelTests(SimpleTestCase):
    def test_meal_entity_strips_actions_from_main_card(self):
        content = build_proposal_entity_content(
            {
                "payload": {
                    "is_create_meal": True,
                    "meal": {
                        "name": "Almuerzo propuesto",
                        "card": {
                            "id": "meal-card",
                            "actions": [{"key": "edit"}],
                        },
                    },
                }
            }
        )

        self.assertEqual(content["entity_kind"], "meal")
        self.assertEqual(content["entity_name"], "Almuerzo propuesto")
        self.assertEqual(content["main_card"]["actions"], [])

    def test_dailyplan_entity_collects_child_cards_and_foods(self):
        content = build_proposal_entity_content(
            {
                "payload": {
                    "is_create_dailyplan": True,
                    "dailyplan": {
                        "name": "Plan propuesto",
                        "card": {
                            "id": "dailyplan-card",
                            "actions": [{"key": "edit"}],
                            "titulo": {
                                "structural_indicators": {
                                    "foods_count": 2,
                                },
                            },
                        },
                        "meals": [
                            {
                                "meal": {
                                    "card": {
                                        "actions": [{"key": "edit"}],
                                        "foods_aggregation": [
                                            {"display_name": "Pollo"},
                                            {"display_name": "Arroz"},
                                        ],
                                    },
                                },
                            },
                            {
                                "meal": {
                                    "card": {
                                        "foods_aggregation": [
                                            {"display_name": "Pollo"},
                                        ],
                                    },
                                },
                            },
                        ],
                    },
                }
            }
        )

        self.assertEqual(content["entity_kind"], "dailyplan")
        self.assertEqual(content["entity_name"], "Plan propuesto")
        self.assertEqual(content["main_card"]["actions"], [])
        self.assertEqual(content["structural_indicators"]["meals_count"], 2)
        self.assertEqual(content["structural_indicators"]["foods_count"], 2)
        self.assertEqual(
            [food["display_name"] for food in content["foods_aggregation"]],
            ["Pollo", "Arroz"],
        )
        self.assertEqual(content["child_cards"][0]["actions"], [])
