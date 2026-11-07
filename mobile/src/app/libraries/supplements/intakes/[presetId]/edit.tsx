import { useLocalSearchParams } from "expo-router";

import { SupplementIntakePresetFormScreen } from "@/components/supplements/supplement-intake-preset-form-screen";

export default function EditSupplementIntakePresetScreen() {
  const { presetId } = useLocalSearchParams<{ presetId: string }>();
  return <SupplementIntakePresetFormScreen presetId={presetId} />;
}
