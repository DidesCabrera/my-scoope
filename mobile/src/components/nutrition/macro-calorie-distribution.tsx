import { StyleProp, StyleSheet, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";
import { macroCalorieShares } from "./macro-calorie-shares";

type MacroCalorieDistributionProps = {
  carbsGrams: number;
  fatGrams: number;
  proteinGrams: number;
  style?: StyleProp<ViewStyle>;
};

export function MacroCalorieDistribution(props: MacroCalorieDistributionProps) {
  const shares = macroCalorieShares(props);
  const accessibilityLabel = `Distribución calórica: proteínas ${shares.protein}%, carbohidratos ${shares.carbs}%, grasas ${shares.fat}%`;

  return (
    <View accessibilityLabel={accessibilityLabel} style={[styles.track, props.style]}>
      <View style={[styles.segment, styles.protein, { flex: shares.protein }]} />
      <View style={[styles.segment, styles.carbs, { flex: shares.carbs }]} />
      <View style={[styles.segment, styles.fat, { flex: shares.fat }]} />
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    backgroundColor: tokens.color.allocationPanelTrack,
    borderRadius: 4,
    flexDirection: "row",
    gap: 1,
    height: 24,
    minWidth: 0,
    overflow: "hidden",
    width: "100%",
  },
  segment: { height: "100%", minWidth: 0 },
  protein: { backgroundColor: tokens.color.protein },
  carbs: { backgroundColor: tokens.color.carbs },
  fat: { backgroundColor: tokens.color.fat },
});
