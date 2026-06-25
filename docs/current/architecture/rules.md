# Architecture Rules

## Purpose

These rules define the architectural boundaries of the project.
Their purpose is to keep responsibilities clear, reduce coupling, and make future refactors safer.

They are not theoretical guidelines.  
They must be used to evaluate new code, refactors, and pull requests.

---

## Layer Overview

The project is organized around these layers:

- `domain`
- `application`
- `presentation`
- `interface`

Each layer has a specific responsibility and must respect dependency direction.

---

## Dependency Direction

Allowed direction:

`interface -> presentation/application -> domain`

`presentation -> application/domain`

Forbidden direction:

- `domain -> application`
- `application -> presentation`
- `application -> interface`
- `domain -> interface`
- `domain -> presentation`

---

## Rules

### 1. `domain` does not import `application`

The domain layer defines core entities, relationships, and business invariants.

It must not depend on application services, orchestration logic, routing, views, or presentation logic.

#### Allowed in `domain`
- models
- entity rules
- domain-specific helpers close to the model
- constants related to the business concept

#### Forbidden in `domain`
- imports from `application`
- imports from `interface`
- imports from `presentation`
- request handling
- messages framework
- redirects
- URL building

---

### 2. `application` does not import `presentation`

The application layer executes use cases and business workflows.

It may return plain Python structures, entities, or result objects.
It must not know how data will be rendered.

#### Allowed in `application`
- use cases
- orchestration
- business workflows
- reusable services
- capability checks
- plain result dictionaries or objects

#### Forbidden in `application`
- viewmodels
- template-specific formatting
- UI labels
- icon selection
- render concerns

---

### 3. `application` does not import `interface`

The application layer must not depend on HTTP, Django views, routing helpers, request objects, or redirect logic.

#### Forbidden in `application`
- `request`
- `messages`
- `redirect`
- `render`
- URL helpers from interface routing
- view-specific logic

#### Expected pattern
The interface layer calls the application layer, not the opposite.

---

### 4. `interface` orchestrates, it does not compute

The interface layer receives HTTP input and returns HTTP responses.

Views should stay thin and predictable.

#### Responsibilities of `interface`
- read request data
- load the authenticated user
- call application services / use cases
- call presentation builders when needed
- render templates or redirect
- return messages to the user

#### Interface should not
- implement business rules directly
- duplicate business computations
- build complex domain state inline
- contain large amounts of branching business logic

#### Target rule
If logic is reusable or business-relevant, move it out of the view.

---

### 5. `presentation` transforms data for rendering

The presentation layer prepares data for templates and UI components.

It is responsible for shaping data, labels, sections, cards, headers, and viewmodels.

#### Responsibilities of `presentation`
- build viewmodels
- adapt data for template rendering
- compose headers, cards, tables, actions, and sections
- prepare display-oriented structures

#### Presentation should not
- write to the database
- own business workflows
- decide permissions independently
- mutate core business entities as part of rendering

---

### 6. `resolvers` resolve UI actions, not business logic

Resolvers exist to decide which actions are visible and how they are presented in the UI.

They are part of UI action resolution, not core domain behavior.

#### Responsibilities of `resolvers`
- determine available actions for a context
- define labels
- define icons
- define action groups
- define ordering
- connect actions to URLs
- check capabilities already exposed by the system

#### Resolvers should not
- perform writes
- execute business workflows
- mutate entities
- contain domain rules that belong in services or models
- replace use cases

---

## Practical Heuristics

Use these questions during development:

### If the code needs `request`, where should it live?
Usually in `interface`.

### If the code changes business state, where should it live?
Usually in `application`, or in `domain` if it is a true domain rule close to the entity.

### If the code only prepares data for templates, where should it live?
In `presentation`.

### If the code decides whether to show a button or action, where should it live?
In `resolvers`.

### If the code is reusable across multiple views and affects business behavior, where should it live?
In `application`.

---

## PR Review Rules

A pull request should be questioned when:

- a model imports from `application`
- an application service imports from `presentation`
- an application service imports from `interface`
- a view grows because it contains business logic
- a resolver starts executing workflows instead of resolving actions
- presentation code starts writing or mutating business state

---

## Current Refactor Direction

The current architectural direction of the project is:

- thinner views
- page builders in `presentation/pages`
- action resolvers in `presentation/actions`
- application focused on commands and services
- stricter isolation of `domain`
- presentation focused on viewmodels and composition
- resolvers limited to UI action definition
- progressive reduction of cross-layer coupling

This document should guide future refactors.




---

## Known Current Gaps

The project is currently moving toward these rules, but some legacy areas still violate them.

Known areas under refactor:

- some views still contain too much orchestration and conditional logic
- some domain code still depends on application services
- some resolvers currently mix UI concerns with behavior that should move elsewhere

These cases should be reduced progressively, not through uncontrolled rewrites.