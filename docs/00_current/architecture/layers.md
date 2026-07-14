# Architecture Layers

My Scoope is currently structured as a modular Django monolith.

The goal is to keep Django as the main product shell while separating business logic, presentation composition, and interface concerns.

## Layers

### Interface

Path examples:

- `notas/interface/views/`
- `notas/interface/urls/`
- `notas/urls.py` as route aggregator

Responsibilities:

- Receive HTTP requests.
- Apply Django decorators.
- Read form/request data.
- Call presentation page builders for read/page data and application commands for writes.
- Manage web-only concerns such as `messages`, `redirect`, `render`, and uploaded files.
- Build the final page response.

Interface code should not contain core business writes such as creating meals, updating DailyPlanMeal relations, replacing snapshots, or creating shares.

### Presentation Page Builders

Path examples:

- `notas/presentation/pages/`
- `notas/presentation/actions/`

Responsibilities:

- Orchestrate page-level read flows for web pages.
- Build page data and action contracts for templates.
- Coordinate read services, picker payloads, viewmodels, icons, labels, navigation, breadcrumbs, and header actions.
- Keep views thin without making the application layer depend on presentation or interface code.

Presentation page builders can prepare UI-ready data for the web interface, but should not execute write operations. Writes belong in application commands.

### Application Commands

Path examples:

- `notas/application/services/commands/`

Responsibilities:

- Execute write operations.
- Create, update, delete, copy, fork, save, share, configure, and attach domain objects.
- Encapsulate changes that may later be reused from API, MCP, internal AI, or mobile clients.
- Return explicit result objects.

Commands should not depend on:

- `request`
- `messages`
- `redirect`
- templates
- HTML
- JavaScript
- browser state

### Application Services

Path examples:

- `notas/application/services/`

Responsibilities:

- Shared application rules.
- Access resolution.
- Nutrition calculations.
- Food aggregation.
- User-specific nutrition context.

### Presentation

Path examples:

- `notas/presentation/`

Responsibilities:

- Build viewmodels.
- Build content contracts for templates.
- Resolve icons, titles, labels, navigation, breadcrumbs, header actions, and UI metadata.
- Convert application data into UI-ready structures.

Presentation should not execute writes to the database.

### Domain

Path examples:

- `notas/domain/`

Responsibilities:

- Django models.
- Domain properties.
- Nutrition fields.
- Core invariants.
- Model-level calculations where appropriate.

### Templates and Static Assets

Path examples:

- `notas/templates/`
- `notas/static/notas/`

Responsibilities:

- Render UI.
- Handle client-side interaction.
- Consume already-prepared contracts.

Templates and JavaScript should not duplicate business rules when those rules belong to commands or services.

### AI Assistant App

Path examples:

- `ai_assistant/application/`
- `ai_assistant/domain/`
- `ai_assistant/infrastructure/`

Responsibilities:

- Define chat engine contracts.
- Host future LLM provider gateways.
- Version prompts and structured AI contracts.
- Register controlled tools for AI orchestration.
- Keep AI safety/audit concerns outside operational domain models.

`ai_assistant` does not own `Food`, `Meal`, `DailyPlan`, `Program`, `NutritionProposal` or the current `AiNutritionChat` persistence. It orchestrates through explicit application services and must not access `food_catalog` directly.
