# Architecture Overview

## Core Pattern

Each view follows a consistent structure:

view → use_case (page_data) → content_data → viewmodel → template

### Flow explanation

* **view (interface layer)**
  Thin Django view. Handles:

  * permissions
  * POST actions
  * rendering

* **use_case (application/use_cases)**
  Builds `page_data`:

  * loads aggregates (DB)
  * prepares picker payloads
  * resolves viewmode
  * prepares everything needed by the view

* **content_data (application layer)**
  Prepares data for UI:

  * KPIs
  * aggregations
  * table items
  * child card data
  * actions (via resolvers)

* **viewmodel (presentation layer)**
  Pure UI composition:

  * builds UI objects (MainCardUI, ChildCardUI, etc.)
  * NO business logic
  * NO DB queries

* **template / JS**

  * consumes VM
  * uses stable JSON contracts for pickers

---

## Layers

### domain

* Django models
* pure business logic
* no UI or HTTP knowledge

### application

#### use_cases

* orchestrate page logic
* entry point for views
* return structured `page_data`

#### services

* reusable logic
* examples:

  * kpis (get_ppk_meal, get_ppk_dailyplan)
  * access (get_meal_for_user)

#### resolvers

* define UI actions per entity
* examples:

  * resolve_meal_actions
  * resolve_meal_food_actions

---

### presentation

#### content_data builders

* transform domain → UI-ready data
* still no UI objects

#### viewmodels

* build UI objects only
* examples:

  * MainCardUI
  * ChildCardUI
  * MealDetailVM
  * ListVM

---

### interface (views)

* thin controllers
* never contain business logic
* never prepare complex data

---

## Key Rules

1. Views must be thin
2. No business logic in viewmodels
3. No DB queries in viewmodels
4. Heavy logic belongs to use_cases or services
5. UI contracts must remain stable (especially JS)
6. Do not mix responsibilities between layers

---

## Entity Design (Important)

Entities are NOT identical.

### Example

| Entity    | MainCardUI supports    |
| --------- | ---------------------- |
| dailyplan | foods_aggregation      |
| meal      | ❌ no foods_aggregation |

👉 Do NOT force uniform contracts between entities.

---

## Detail Views

### Meal Detail

* `main_card` → Meal
* `child_cards` → MealFood

### DailyPlan Detail

* `main_card` → DailyPlan
* `child_cards` → Meals

---

## Actions Pattern

Actions must align with entity level:

* Meal → `resolve_meal_actions`
* MealFood → `resolve_meal_food_actions`
* DailyPlan → `resolve_dailyplan_actions`

Never reuse actions across entity levels incorrectly.

---

## Picker Pattern (CRITICAL)

Pickers depend on strict contracts.

### Required inputs

1. data_json

   * list of items
   * example:
     window.FOOD_PICKER_FOODS

2. context_json

   * mode + editing state
   * example:
     window.FOOD_PICKER_CONTEXT

### Rule

❌ Never change keys without verifying JS
❌ Never mix picker contexts (meal vs dailyplan)

---

## Known Pitfalls

* Do NOT mix meal picker with dailyplan picker
* Do NOT assume MainCardUI is universal
* Always serialize dataclasses before sending to JS
* Always validate JS variables in browser (window.*)
* Never move logic into viewmodels
* Avoid duplicating logic between content_data and builders

---

## Where Things Live

| Responsibility | Location     |
| -------------- | ------------ |
| DB queries     | use_cases    |
| Business logic | services     |
| UI actions     | resolvers    |
| Data shaping   | content_data |
| UI composition | viewmodels   |
| HTTP handling  | views        |

---

## Refactor Checklist

When refactoring a module:

1. Extract use_case (page_data)
2. Move data preparation to content_data
3. Simplify viewmodel (UI only)
4. Keep JS contracts unchanged
5. Validate:

   * browser (window.*)
   * backend tests
   * E2E if available

---

## Design Philosophy

* Prefer clarity over abstraction
* Do not unify things that are conceptually different
* Keep contracts explicit
* Build systems that are easy to extend, not just to run

---

## Current State

The system has:

* clear layer separation
* stable picker contracts
* reusable services and resolvers
* scalable architecture for new modules (e.g. foods)

---

## Next Steps (Suggested)

* move POST mutations to application/services
* unify UI contracts only if needed (carefully)
* expand test coverage (especially pickers)
* replicate pattern for foods module
