import { tokens } from "@/design/tokens";

export function subscriptionPlanAccent(planName: string | null | undefined): string | undefined {
  switch (planName?.trim().toLowerCase()) {
    case "free":
      return tokens.color.fat;
    case "basic":
      return tokens.color.carbs;
    case "pro":
      return tokens.color.protein;
    default:
      return undefined;
  }
}
