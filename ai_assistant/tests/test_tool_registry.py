from django.test import SimpleTestCase

from ai_assistant.application.tools import (
    AssistantToolCategory,
    AssistantToolRegistryError,
    AssistantToolRiskLevel,
    AssistantToolSpec,
    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
    TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL,
    TOOL_LIST_OPERATIONAL_FOODS,
    TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES,
    TOOL_READ_DAILYPLAN,
    TOOL_SEARCH_OPERATIONAL_FOODS,
    get_tool_spec,
    is_allowed_tool_name,
    is_forbidden_tool_name,
    list_allowed_tool_specs,
    list_provider_tool_specs,
    validate_tool_request,
)
from ai_assistant.domain.contracts import (
    AssistantToolRequest,
    AssistantToolStatus,
)


class AIAssistantToolRegistryTests(SimpleTestCase):
    def test_registry_exposes_controlled_allowed_tools(self):
        tool_names = [spec.name for spec in list_allowed_tool_specs()]

        self.assertIn(TOOL_READ_DAILYPLAN, tool_names)
        self.assertIn(TOOL_SEARCH_OPERATIONAL_FOODS, tool_names)
        self.assertIn(TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES, tool_names)
        self.assertIn(TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL, tool_names)
        self.assertIn(TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL, tool_names)
        self.assertNotIn("list_food_catalog", tool_names)
        self.assertNotIn("apply_proposal", tool_names)

    def test_can_filter_allowed_tools_by_category(self):
        read_specs = list_allowed_tool_specs(categories=[AssistantToolCategory.READ])
        proposal_specs = list_allowed_tool_specs(categories=["proposal"])

        self.assertTrue(read_specs)
        self.assertTrue(proposal_specs)
        self.assertTrue(all(spec.category == AssistantToolCategory.READ for spec in read_specs))
        self.assertTrue(all(spec.requires_human_review for spec in proposal_specs))

    def test_provider_tool_specs_do_not_expose_local_policy_flags(self):
        provider_specs = list_provider_tool_specs()
        first_spec = provider_specs[0]

        self.assertIn("name", first_spec)
        self.assertIn("description", first_spec)
        self.assertIn("parameters", first_spec)
        self.assertNotIn("requires_human_review", first_spec)
        self.assertNotIn("risk_level", first_spec)
        self.assertFalse(any("catalog" in spec["name"] for spec in provider_specs))

    def test_get_tool_spec_normalizes_names_and_rejects_forbidden_names(self):
        spec = get_tool_spec("  Read DailyPlan ")

        self.assertEqual(spec.name, TOOL_READ_DAILYPLAN)
        self.assertTrue(is_allowed_tool_name("read-dailyplan"))
        self.assertTrue(is_forbidden_tool_name("list_food_catalog"))

        with self.assertRaisesMessage(
            AssistantToolRegistryError,
            "forbidden_ai_assistant_tool:list_food_catalog",
        ):
            get_tool_spec("list_food_catalog")

    def test_tool_spec_contract_requires_review_for_proposal_tools(self):
        with self.assertRaisesMessage(
            AssistantToolRegistryError,
            "Proposal tools must require human review.",
        ):
            AssistantToolSpec(
                name="unsafe_proposal",
                description="Unsafe proposal tool.",
                category="proposal",
                risk_level="review_required",
                requires_human_review=False,
            )

    def test_validate_tool_request_marks_allowed_tool_as_pending(self):
        result = validate_tool_request(
            AssistantToolRequest(
                tool_name=TOOL_READ_DAILYPLAN,
                arguments={"dailyplan_id": 123},
                request_id="call_1",
            )
        )

        self.assertEqual(result.status, AssistantToolStatus.PENDING)
        self.assertEqual(result.tool_name, TOOL_READ_DAILYPLAN)
        self.assertEqual(result.request_id, "call_1")
        self.assertEqual(result.data["category"], "read")
        self.assertFalse(result.data["requires_human_review"])

    def test_validate_tool_request_blocks_unknown_and_forbidden_tools(self):
        unknown = validate_tool_request(
            AssistantToolRequest(tool_name="send_email", arguments={})
        )
        forbidden = validate_tool_request(
            AssistantToolRequest(tool_name="apply_proposal", arguments={"proposal_id": 1})
        )

        self.assertEqual(unknown.status, AssistantToolStatus.BLOCKED)
        self.assertEqual(unknown.error_code, "unsupported_ai_assistant_tool")
        self.assertEqual(forbidden.status, AssistantToolStatus.BLOCKED)
        self.assertEqual(forbidden.error_code, "forbidden_ai_assistant_tool")

    def test_validate_tool_request_blocks_missing_required_arguments(self):
        result = validate_tool_request(
            AssistantToolRequest(tool_name=TOOL_READ_DAILYPLAN, arguments={})
        )

        self.assertEqual(result.status, AssistantToolStatus.BLOCKED)
        self.assertEqual(result.error_code, "invalid_ai_assistant_tool_arguments")
        self.assertEqual(
            result.metadata["details"],
            {"missing_arguments": ["dailyplan_id"]},
        )

    def test_validate_tool_request_blocks_catalog_food_references(self):
        result = validate_tool_request(
            AssistantToolRequest(
                tool_name=TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
                arguments={
                    "dailyplan_id": 1,
                    "title": "Comida propuesta",
                    "proposed_payload": {
                        "meal": {
                            "foods": [
                                {"catalog_food_id": 999, "quantity": 100},
                            ],
                        },
                    },
                },
            )
        )

        self.assertEqual(result.status, AssistantToolStatus.BLOCKED)
        self.assertEqual(result.error_code, "forbidden_catalog_reference")
        self.assertEqual(result.metadata["details"], {"argument_key": "catalog_food_id"})

    def test_operational_food_tools_are_read_only_not_master_catalog_tools(self):
        list_spec = get_tool_spec(TOOL_LIST_OPERATIONAL_FOODS)
        search_spec = get_tool_spec(TOOL_SEARCH_OPERATIONAL_FOODS)
        preview_spec = get_tool_spec(TOOL_PREVIEW_NUTRITION_SOLVER_CANDIDATES)

        self.assertTrue(list_spec.is_read_only)
        self.assertTrue(search_spec.is_read_only)
        self.assertTrue(preview_spec.is_read_only)
        self.assertEqual(list_spec.risk_level, AssistantToolRiskLevel.MEDIUM)
        self.assertEqual(preview_spec.risk_level, AssistantToolRiskLevel.MEDIUM)
        self.assertIn("notas.Food", list_spec.description)
        self.assertIn("notas.Food", preview_spec.description)
        self.assertIn("nutrition solver", preview_spec.description)


    def test_nutrition_solver_meal_proposal_is_reviewable_tool(self):
        spec = get_tool_spec(TOOL_CREATE_NUTRITION_SOLVER_MEAL_PROPOSAL)

        self.assertEqual(spec.category, AssistantToolCategory.PROPOSAL)
        self.assertEqual(spec.risk_level, AssistantToolRiskLevel.REVIEW_REQUIRED)
        self.assertTrue(spec.requires_human_review)
        self.assertIn("target", spec.input_schema["required"])

    def test_tool_registry_does_not_import_provider_or_food_catalog_modules(self):
        import ai_assistant.application.tools.contracts as contracts
        import ai_assistant.application.tools.registry as registry

        self.assertNotIn("food_catalog", contracts.__dict__)
        self.assertNotIn("food_catalog", registry.__dict__)
        self.assertNotIn("OpenAIResponsesClient", registry.__dict__)
        self.assertNotIn("notas", registry.__dict__)
