from myscoope_mcp.contracts import MCPToolSpec


TOOL_READ_DAILYPLAN = "read_dailyplan"
TOOL_READ_PROPOSAL = "read_proposal"
TOOL_LIST_USER_PROPOSALS = "list_user_proposals"
TOOL_COMPARE_DAILYPLAN_TO_TARGETS = "compare_dailyplan_to_targets"
TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL = "create_validated_dailyplan_proposal"
TOOL_LIST_FOOD_CATALOG = "list_food_catalog"
TOOL_CREATE_VALIDATED_MEAL_PROPOSAL = "create_validated_meal_proposal"
TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL = "create_validated_dailyplan_build_proposal"
TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL = "create_nutrition_engine_dailyplan_proposal"
TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL = "iterate_nutrition_engine_dailyplan_proposal"


FORBIDDEN_TOOL_NAMES = {
    "apply_approved_proposal",
    "apply_proposal",
    "apply_validated_proposal",
    "delete_food",
    "delete_meal",
    "delete_dailyplan",
    "update_food",
    "update_meal",
    "update_dailyplan",
    "create_food",
    "create_meal",
    "create_dailyplan",
    "raw_sql",
    "raw_command_execution",
    "raw_model_mutation",
}


ALLOWED_TOOL_SPECS = {
    TOOL_READ_DAILYPLAN: MCPToolSpec(
        name=TOOL_READ_DAILYPLAN,
        description="Read a DailyPlan available to the authenticated user.",
        api_path="/ai-tools/read-dailyplan/",
        input_schema={
            "type": "object",
            "required": ["dailyplan_id"],
            "properties": {
                "dailyplan_id": {
                    "type": "integer",
                    "description": "DailyPlan ID to read.",
                },
            },
        },
    ),
    TOOL_READ_PROPOSAL: MCPToolSpec(
        name=TOOL_READ_PROPOSAL,
        description="Read a NutritionProposal available to the authenticated user.",
        api_path="/ai-tools/read-proposal/",
        input_schema={
            "type": "object",
            "required": ["proposal_id"],
            "properties": {
                "proposal_id": {
                    "type": "integer",
                    "description": "NutritionProposal ID to read.",
                },
            },
        },
    ),
    TOOL_LIST_USER_PROPOSALS: MCPToolSpec(
        name=TOOL_LIST_USER_PROPOSALS,
        description="List proposals visible to the authenticated user.",
        api_path="/ai-tools/list-user-proposals/",
        input_schema={
            "type": "object",
            "required": [],
            "properties": {},
        },
    ),
    TOOL_COMPARE_DAILYPLAN_TO_TARGETS: MCPToolSpec(
        name=TOOL_COMPARE_DAILYPLAN_TO_TARGETS,
        description="Compare a DailyPlan against nutritional targets.",
        api_path="/ai-tools/compare-dailyplan-to-targets/",
        input_schema={
            "type": "object",
            "required": ["dailyplan_id", "targets"],
            "properties": {
                "dailyplan_id": {
                    "type": "integer",
                    "description": "DailyPlan ID to validate.",
                },
                "targets": {
                    "type": "object",
                    "description": "Target nutrition metrics.",
                },
                "tolerances": {
                    "type": "object",
                    "description": "Optional tolerance values.",
                },
            },
        },
    ),
    TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL: MCPToolSpec(
        name=TOOL_CREATE_VALIDATED_DAILYPLAN_PROPOSAL,
        description="Create a validated NutritionProposal for human review.",
        api_path="/ai-tools/create-validated-dailyplan-proposal/",
        input_schema={
            "type": "object",
            "required": ["dailyplan_id", "title", "targets"],
            "properties": {
                "dailyplan_id": {
                    "type": "integer",
                    "description": "DailyPlan ID for the proposal.",
                },
                "title": {
                    "type": "string",
                    "description": "Proposal title.",
                },
                "summary": {
                    "type": "string",
                    "description": "Optional proposal summary.",
                },
                "targets": {
                    "type": "object",
                    "description": "Target nutrition metrics.",
                },
                "tolerances": {
                    "type": "object",
                    "description": "Optional tolerance values.",
                },
                "proposed_payload": {
                    "type": "object",
                    "description": "Optional structured proposal payload.",
                },
            },
        },
    ),
    TOOL_LIST_FOOD_CATALOG: MCPToolSpec(
        name=TOOL_LIST_FOOD_CATALOG,
        description="List readable foods available for AI/MCP nutrition planning.",
        api_path="/ai-tools/list-food-catalog/",
        input_schema={
            "type": "object",
            "required": [],
            "properties": {
                "search": {
                    "type": "string",
                    "description": "Optional case-insensitive food name search.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Optional maximum number of foods to return.",
                },
            },
        },
    ),
    TOOL_CREATE_VALIDATED_MEAL_PROPOSAL: MCPToolSpec(
        name=TOOL_CREATE_VALIDATED_MEAL_PROPOSAL,
        description=(
            "Create a reviewable meal proposal using real food IDs and quantities. "
            "This tool does not create a final Meal."
        ),
        api_path="/ai-tools/create-validated-meal-proposal/",
        input_schema={
            "type": "object",
            "required": [
                "dailyplan_id",
                "title",
                "proposed_payload",
            ],
            "properties": {
                "dailyplan_id": {
                    "type": "integer",
                    "description": "DailyPlan context where the meal proposal will be reviewed.",
                },
                "title": {
                    "type": "string",
                    "description": "Proposal title.",
                },
                "summary": {
                    "type": "string",
                    "description": "Optional proposal summary.",
                },
                "targets": {
                    "type": "object",
                    "description": "Optional meal-level target metrics.",
                },
                "proposed_payload": {
                    "type": "object",
                    "description": "Rich proposal payload with intent create_meal.",
                    "required": [
                        "intent",
                        "meal",
                    ],
                    "properties": {
                        "intent": {
                            "type": "string",
                            "const": "create_meal",
                        },
                        "meal": {
                            "type": "object",
                            "required": [
                                "name",
                                "foods",
                            ],
                            "properties": {
                                "name": {
                                    "type": "string",
                                },
                                "foods": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": [
                                            "food_id",
                                            "quantity",
                                        ],
                                        "properties": {
                                            "food_id": {
                                                "type": "integer",
                                            },
                                            "quantity": {
                                                "type": "number",
                                            },
                                            "unit": {
                                                "type": "string",
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    ),
    TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL: MCPToolSpec(
        name=TOOL_CREATE_VALIDATED_DAILYPLAN_BUILD_PROPOSAL,
        description=(
            "Create a reviewable DailyPlan build proposal using proposed meals, "
            "real food IDs and quantities. This tool does not create a final DailyPlan."
        ),
        api_path="/ai-tools/create-validated-dailyplan-build-proposal/",
        input_schema={
            "type": "object",
            "required": [
                "dailyplan_id",
                "title",
                "proposed_payload",
            ],
            "properties": {
                "dailyplan_id": {
                    "type": "integer",
                    "description": (
                        "DailyPlan context where the proposed DailyPlan will be reviewed."
                    ),
                },
                "title": {
                    "type": "string",
                    "description": "Proposal title.",
                },
                "summary": {
                    "type": "string",
                    "description": "Optional proposal summary.",
                },
                "targets": {
                    "type": "object",
                    "description": "Optional dailyplan-level target metrics.",
                },
                "proposed_payload": {
                    "type": "object",
                    "description": "Rich proposal payload with intent create_dailyplan.",
                    "required": [
                        "intent",
                        "dailyplan",
                    ],
                    "properties": {
                        "intent": {
                            "type": "string",
                            "const": "create_dailyplan",
                        },
                        "dailyplan": {
                            "type": "object",
                            "required": [
                                "name",
                                "meals",
                            ],
                            "properties": {
                                "name": {
                                    "type": "string",
                                },
                                "meals": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": [
                                            "meal",
                                        ],
                                        "properties": {
                                            "hour": {
                                                "type": [
                                                    "string",
                                                    "null",
                                                ],
                                            },
                                            "note": {
                                                "type": "string",
                                            },
                                            "meal": {
                                                "type": "object",
                                                "required": [
                                                    "name",
                                                    "foods",
                                                ],
                                                "properties": {
                                                    "name": {
                                                        "type": "string",
                                                    },
                                                    "foods": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "required": [
                                                                "food_id",
                                                                "quantity",
                                                            ],
                                                            "properties": {
                                                                "food_id": {
                                                                    "type": "integer",
                                                                },
                                                                "quantity": {
                                                                    "type": "number",
                                                                },
                                                                "unit": {
                                                                    "type": "string",
                                                                },
                                                            },
                                                        },
                                                    },
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    ),

    TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: MCPToolSpec(
        name=TOOL_CREATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
        description=(
            "Create a reviewable DailyPlan proposal by running the internal "
            "My Scoope nutrition engine from a structured NutritionBrief. "
            "This tool does not create or apply the final DailyPlan."
        ),
        api_path="/ai-tools/create-nutrition-engine-dailyplan-proposal/",
        input_schema={
            "type": "object",
            "required": ["nutrition_brief"],
            "properties": {
                "nutrition_brief": {
                    "type": "object",
                    "description": "Structured NutritionBrief consumed by the nutrition engine.",
                    "required": [
                        "raw_prompt",
                        "goal",
                        "requested_entity",
                        "meals_per_day",
                    ],
                    "properties": {
                        "raw_prompt": {"type": "string"},
                        "goal": {
                            "type": "string",
                            "description": "fat_loss, muscle_gain, maintenance, performance or healthy_eating.",
                        },
                        "requested_entity": {
                            "type": "string",
                            "const": "daily_plan",
                        },
                        "meals_per_day": {"type": "integer"},
                        "training_frequency": {"type": "integer"},
                        "calorie_target": {"type": "integer"},
                        "protein_target": {"type": "integer"},
                        "carb_target": {"type": "integer"},
                        "fat_target": {"type": "integer"},
                        "weight_kg": {"type": "number"},
                        "height_cm": {"type": "integer"},
                        "age_years": {"type": "integer"},
                        "sex": {"type": "string"},
                        "activity_level": {"type": "string"},
                        "energy_adjustment": {"type": "string"},
                        "style_preferences": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "excluded_foods": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "preferred_foods": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "complexity_level": {"type": "string"},
                        "budget_level": {"type": "string"},
                        "notes": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        },
    ),
    TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL: MCPToolSpec(
        name=TOOL_ITERATE_NUTRITION_ENGINE_DAILYPLAN_PROPOSAL,
        description=(
            "Create a new reviewable DailyPlan proposal revision by applying "
            "structured chat feedback commands over a NutritionBrief. This tool "
            "does not mutate or apply the previous proposal."
        ),
        api_path="/ai-tools/iterate-nutrition-engine-dailyplan-proposal/",
        input_schema={
            "type": "object",
            "required": [
                "previous_proposal_id",
                "nutrition_brief",
                "user_message",
            ],
            "properties": {
                "previous_proposal_id": {
                    "type": "integer",
                    "description": "Previous generated DailyPlan proposal to keep as immutable revision history.",
                },
                "nutrition_brief": {
                    "type": "object",
                    "description": "Structured NutritionBrief after applying/accumulating the user's requested adjustments.",
                },
                "user_message": {
                    "type": "string",
                    "description": "Original chat feedback, such as 'más proteína' or 'sin arroz'.",
                },
            },
        },
    ),
}


def list_allowed_tool_specs() -> list[MCPToolSpec]:
    return list(ALLOWED_TOOL_SPECS.values())


def get_tool_spec(tool_name: str) -> MCPToolSpec:
    try:
        return ALLOWED_TOOL_SPECS[tool_name]
    except KeyError:
        raise ValueError(f"unsupported_mcp_tool:{tool_name}")


def is_forbidden_tool_name(tool_name: str) -> bool:
    return tool_name in FORBIDDEN_TOOL_NAMES