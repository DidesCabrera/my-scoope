from django.test import SimpleTestCase

from ai_assistant.application.prepared_actions import PREPARED_ACTION_SPECS
from ai_assistant.application.tools.registry import is_allowed_tool_name
from ai_assistant.domain.capabilities import (
    CAPABILITIES,
    CAPABILITY_BY_CODE,
    AssistantCapabilityMode,
)


class AssistantCapabilityParityCatalogTests(SimpleTestCase):
    EXPECTED_DOMAINS = {
        "profile",
        "foods",
        "meals",
        "dailyplans",
        "nutrition",
        "programs",
        "calendar",
        "comparisons",
        "proposals",
        "inbox",
        "account_billing",
        "admin",
    }

    def test_all_human_product_domains_have_an_explicit_assistant_policy(self):
        self.assertEqual(
            {capability.domain for capability in CAPABILITIES},
            self.EXPECTED_DOMAINS,
        )
        self.assertEqual(len(CAPABILITIES), len(CAPABILITY_BY_CODE))

    def test_every_declared_tool_and_prepared_action_exists(self):
        for capability in CAPABILITIES:
            for tool_name in capability.tool_names:
                self.assertTrue(
                    is_allowed_tool_name(tool_name),
                    f"{capability.code} references missing tool {tool_name}",
                )
            for action_key in capability.prepared_action_keys:
                self.assertIn(
                    action_key,
                    PREPARED_ACTION_SPECS,
                    f"{capability.code} references missing action {action_key}",
                )

    def test_mutations_are_never_classified_as_autonomous_reads(self):
        for capability in CAPABILITIES:
            if capability.prepared_action_keys or capability.mode == AssistantCapabilityMode.REVIEWABLE_PROPOSAL:
                self.assertTrue(capability.requires_confirmation)

    def test_admin_capabilities_stay_staff_only_and_outside_user_tools(self):
        admin_capabilities = [
            capability
            for capability in CAPABILITIES
            if capability.domain == "admin"
        ]
        self.assertTrue(admin_capabilities)
        self.assertTrue(
            all(
                capability.mode == AssistantCapabilityMode.STAFF_ONLY
                and not capability.tool_names
                and not capability.prepared_action_keys
                for capability in admin_capabilities
            )
        )
