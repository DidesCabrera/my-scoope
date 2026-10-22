import { MobileApiError } from "@/api/errors";
import type { EntitlementsData } from "@/api/types";
import type { EntityKind } from "@/components/ui";

export type CommercialLimitEntity = Extract<EntityKind, "comparison" | "dailyPlan" | "meal" | "program">;

export type CommercialLimitState = {
  entity: CommercialLimitEntity;
  limit: number;
  planName: string;
  used: number;
};

const commercialLimitKeys = {
  comparison: { error: "max_saved_comparisons_reached", limit: "max_saved_comparisons", usage: "comparison" },
  dailyPlan: { error: "max_dailyplans_reached", limit: "max_dailyplans", usage: "dailyplan" },
  meal: { error: "max_meals_reached", limit: "max_meals", usage: "meal" },
  program: { error: "max_programs_reached", limit: "max_programs", usage: "program" },
} satisfies Record<CommercialLimitEntity, { error: string; limit: string; usage: string }>;

export function commercialLimitState(entitlements: EntitlementsData, entity: CommercialLimitEntity): CommercialLimitState | null {
  const keys = commercialLimitKeys[entity];
  const limit = entitlements.workspace_limits[keys.limit];
  if (typeof limit !== "number") return null;
  return {
    entity,
    limit,
    planName: entitlements.plan_name,
    used: entitlements.workspace_usage[keys.usage] ?? 0,
  };
}

export function reachedCommercialLimit(entitlements: EntitlementsData, entity: CommercialLimitEntity): CommercialLimitState | null {
  const state = commercialLimitState(entitlements, entity);
  return state && state.used >= state.limit ? state : null;
}

export function isCommercialLimitError(error: unknown, entity: CommercialLimitEntity): boolean {
  return error instanceof MobileApiError && error.code === commercialLimitKeys[entity].error;
}
