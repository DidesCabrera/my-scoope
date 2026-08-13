import { StyleProp, StyleSheet, View, ViewStyle } from "react-native";

import type { LibraryCalorieDistribution } from "@/api/types";
import { tokens } from "@/design/tokens";

function normalized(value: number): number {
  return Number.isFinite(value) ? Math.max(0, Math.min(value, 100)) : 0;
}

export function CalorieDistributionBar({ distribution, style }: {
  distribution?: LibraryCalorieDistribution;
  style?: StyleProp<ViewStyle>;
}) {
  const protein = normalized(distribution?.protein ?? 0);
  const carbs = normalized(distribution?.carbs ?? 0);
  const fat = normalized(distribution?.fat ?? 0);
  return (
    <View
      accessibilityLabel={`Distribución calórica: proteínas ${Math.round(protein)}%, carbohidratos ${Math.round(carbs)}%, grasas ${Math.round(fat)}%`}
      accessibilityRole="image"
      style={[styles.track, style]}>
      <View style={{ backgroundColor: tokens.color.protein, flexBasis: `${protein}%` }} />
      <View style={{ backgroundColor: tokens.color.carbs, flexBasis: `${carbs}%` }} />
      <View style={{ backgroundColor: tokens.color.fat, flexBasis: `${fat}%` }} />
    </View>
  );
}

const styles = StyleSheet.create({
  track: { backgroundColor: tokens.color.allocationPanelTrack, borderRadius: 4, flexDirection: "row", height: 24, minWidth: 0, overflow: "hidden", width: "100%" },
});
