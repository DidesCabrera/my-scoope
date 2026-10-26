import assert from "node:assert/strict";
import test from "node:test";

import { MobileApiError } from "../src/api/errors";
import type { EntitlementsData } from "../src/api/types";
import { commercialLimitState, isCommercialLimitError, isSharedImportLimitError, reachedCommercialLimit, sharedImportLimitState } from "../src/components/subscriptions/commercial-limit";

const entitlements = {
  plan_name: "Free",
  workspace_limits: { max_saved_comparisons: 0, max_dailyplans: 2, max_meals: 4, max_programs: 1, max_shared_imports_monthly: 1 },
  workspace_usage: { comparison: 0, dailyplan: 2, meal: 3, program: 1, shared_imports_monthly: 1 },
} as unknown as EntitlementsData;

test("commercial limits open the upgrade prompt only when usage reaches the current allowance", () => {
  assert.equal(reachedCommercialLimit(entitlements, "comparison")?.limit, 0);
  assert.equal(reachedCommercialLimit(entitlements, "dailyPlan")?.used, 2);
  assert.equal(reachedCommercialLimit(entitlements, "meal"), null);
  assert.equal(reachedCommercialLimit(entitlements, "program")?.planName, "Free");
});

test("missing limits do not block creation", () => {
  const withoutLimit = {
    ...entitlements,
    workspace_limits: { ...entitlements.workspace_limits, max_meals: null },
  } as EntitlementsData;
  assert.equal(commercialLimitState(withoutLimit, "meal"), null);
  assert.equal(reachedCommercialLimit(withoutLimit, "meal"), null);
});

test("only the matching server limit error triggers the commercial prompt", () => {
  const reached = new MobileApiError("Limit reached", "max_saved_comparisons_reached", 403);
  assert.equal(isCommercialLimitError(reached, "comparison"), true);
  assert.equal(isCommercialLimitError(reached, "meal"), false);
  assert.equal(isCommercialLimitError(new Error("Limit reached"), "comparison"), false);
});

test("received imports use the monthly entitlement and matching server error", () => {
  assert.deepEqual(sharedImportLimitState(entitlements), { limit: 1, planName: "Free", used: 1 });
  assert.deepEqual(sharedImportLimitState({ ...entitlements, workspace_usage: { shared_imports_monthly: 0 } }), { limit: 1, planName: "Free", used: 0 });
  assert.equal(sharedImportLimitState({ ...entitlements, workspace_limits: { max_shared_imports_monthly: null } }), null);
  assert.equal(isSharedImportLimitError(new MobileApiError("Limit reached", "max_shared_imports_monthly_reached", 422)), true);
  assert.equal(isSharedImportLimitError(new MobileApiError("Limit reached", "max_meals_reached", 422)), false);
});
