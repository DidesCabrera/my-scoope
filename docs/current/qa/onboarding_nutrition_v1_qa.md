# Onboarding Nutrition v1 — QA Closure

Status: completed
Date: 2026-07-03
Cycle: ONB00–ONB09

## Scope validated

This QA closure validates the first end-to-end implementation of the nutrition onboarding cycle:

```text
accounts onboarding
  -> notas Profile + WeightLog / Body Metrics
  -> AI Intake NutritionBrief
  -> NutritionSubjectContext
  -> Nutrition Solver target estimation
  -> Proposal Review external-subject warning
```

The objective of ONB09 is not to introduce new product behavior. It closes the cycle by documenting the stable contracts and adding a smoke/regression test that verifies the main ONB v1 paths remain connected.

## Stable product contracts

### 1. Personal ficha is captured during onboarding

The authenticated onboarding flow captures only the minimum stable body basics:

```text
birth_date
sex
height_cm
weight
onboarding_completed_at
onboarding_version
```

`accounts` conducts the experience, but `notas` owns the persisted operational data.

### 2. Weight is a Body Metric

The onboarding weight is not stored as a static profile field. It is recorded as a `WeightLog` entry with `source=onboarding`.

The current weight for calculations is obtained through the Body Metrics service/read boundary, which uses the latest `WeightLog`.

### 3. First chat completes operational context

The first nutrition chat captures contextual data that v1 does not persist as personal defaults:

```text
activity_level
training_frequency
```

The following remain session/proposal context in v1:

```text
default_goal
default_meals_per_day
default_complexity_level
default_budget_level
```

### 4. Solver calculates for an explicit subject

The solver must not assume the authenticated user is always the nutrition subject.

The calculation subject must be explicit:

```text
self_profile
external_chat_data
manual_chat_data
```

`self_profile` uses the user's ficha and latest `WeightLog`. External/manual subjects use chat-provided values and must not silently fall back to the account owner's body data.

### 5. PPK follows the calculation subject during proposal generation

During proposal generation, PPK and protein-per-kg calculations use the weight of the selected nutrition subject.

Example:

```text
Owner profile weight: 90 kg
External subject weight: 70 kg
Proposal PPK calculation weight: 70 kg
```

### 6. Library save/apply warns for external subjects

When a proposal was calculated with `external_chat_data` or `manual_chat_data`, applying it into the personal library requires an explicit acknowledgement.

The warning explains that kcal and macro grams remain unchanged, while profile-dependent indicators such as PPK will be displayed using the owner's current ficha weight.

## ONB09 regression coverage

ONB09 adds:

```text
accounts/tests/test_onboarding_nutrition_cycle_closure.py
```

The test covers two smoke paths:

1. `self_profile` path:
   - user completes onboarding through the UI;
   - `Profile` receives birth date, sex, height and onboarding metadata;
   - `WeightLog` receives the initial weight with `source=onboarding`;
   - AI Intake uses the ficha when requested;
   - target estimation keeps `subject_context.source=self_profile` and no library PPK warning.

2. `external_chat_data` path:
   - user has a personal ficha;
   - AI Intake receives data for another person;
   - target estimation uses the external weight, not the owner's weight;
   - the generated subject context requires library acknowledgement.

## Recommended validation command

```bash
python manage.py test \
  accounts.tests.test_onboarding \
  accounts.tests.test_onboarding_gate \
  accounts.tests.test_onboarding_nutrition_cycle_closure \
  notas.tests.test_body_metrics \
  notas.tests.test_user_nutrition_profile \
  notas.tests.test_ai_intake_subject_context \
  notas.tests.test_ai_intake_dailyplan_generator \
  notas.tests.test_proposal_review_viewmodels
```

For the ONB08 apply guard specifically:

```bash
python manage.py test \
  notas.tests.test_proposal_views.ProposalViewTests.test_proposal_apply_external_subject_requires_ppk_warning_ack \
  notas.tests.test_proposal_views.ProposalViewTests.test_proposal_apply_external_subject_with_ack_creates_real_dailyplan
```

## Closure statement

ONB v1 is complete when the codebase can truthfully state:

```text
A new user is guided through a nutrition onboarding.
The personal ficha captures stable body basics.
Weight is stored as a Body Metric history entry.
Profile exposes the ficha in clear sections.
AI Assistant asks whether to use the ficha or new data.
Nutrition Solver estimates targets from an explicit subject context.
External/manual proposals preserve their calculation subject during review.
Applying external/manual proposals requires a PPK warning acknowledgement.
```

## Deferred to future cycles

The following remain intentionally out of scope:

- persistent client/third-party profiles;
- generic `UserMetricLog` migration;
- persistent default goals/meals/complexity/budget;
- allergies, intolerances and medical restrictions as profile data;
- weekly Program generation from onboarding;
- professional multi-client workflows.
