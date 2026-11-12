import { Redirect, useLocalSearchParams } from "expo-router";

import { CompositionPickerScreen } from "@/components/pickers/composition-picker-screen";
import { internalHref } from "@/navigation/internal-href";

export default function FoodToPreparationRoute() {
  const { preparationId, returnTo } = useLocalSearchParams<{ preparationId?: string; returnTo?: string }>();
  const targetId = Number(preparationId);
  if (!Number.isInteger(targetId) || targetId <= 0) return <Redirect href="/libraries/preparations" />;
  return <CompositionPickerScreen kind="food-to-preparation" returnTo={internalHref(returnTo)} targetId={targetId} />;
}
