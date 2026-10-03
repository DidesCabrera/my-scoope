import { useEffect } from "react";
import { StyleProp, StyleSheet, View, ViewStyle } from "react-native";
import Animated, { cancelAnimation, Easing, useAnimatedStyle, useReducedMotion, useSharedValue, withRepeat, withSequence, withTiming } from "react-native-reanimated";

import { tokens } from "@/design/tokens";

type MacroLoadingIndicatorProps = { accessibilityLabel?: string; style?: StyleProp<ViewStyle> };

const MOTION = {
  protein: [36, 78, 54, 88, 42],
  carbs: [68, 40, 82, 52, 74],
  fat: [48, 84, 38, 70, 58],
} as const;
const DURATION = { protein: 520, carbs: 610, fat: 570 } as const;

function MacroBar({ color, duration, values }: { color: string; duration: number; values: readonly number[] }) {
  const reducedMotion = useReducedMotion();
  const width = useSharedValue(values[0]);
  const animatedStyle = useAnimatedStyle(() => ({ width: `${width.value}%` }));

  useEffect(() => {
    cancelAnimation(width);
    if (reducedMotion) {
      width.value = values[2];
      return;
    }
    width.value = withRepeat(
      withSequence(...values.slice(1).map((value) => withTiming(value, { duration, easing: Easing.inOut(Easing.quad) })), withTiming(values[0], { duration, easing: Easing.inOut(Easing.quad) })),
      -1,
      false,
    );
    return () => cancelAnimation(width);
  }, [duration, reducedMotion, values, width]);

  return <View style={styles.barSlot}><Animated.View style={[styles.fill, { backgroundColor: color }, animatedStyle]} /></View>;
}

export function MacroLoadingIndicator({ accessibilityLabel = "Cargando contenido", style }: MacroLoadingIndicatorProps) {
  return (
    <View accessibilityLabel={accessibilityLabel} accessibilityLiveRegion="polite" accessibilityRole="progressbar" style={[styles.container, style]}>
      <MacroBar color={tokens.color.protein} duration={DURATION.protein} values={MOTION.protein} />
      <MacroBar color={tokens.color.carbs} duration={DURATION.carbs} values={MOTION.carbs} />
      <MacroBar color={tokens.color.fat} duration={DURATION.fat} values={MOTION.fat} />
    </View>
  );
}

const styles = StyleSheet.create({
  barSlot: { height: tokens.component.nutritionKpi.regular.barHeight, width: "100%" },
  container: { gap: tokens.component.nutritionKpi.regular.contentGap, width: 180 },
  fill: { borderRadius: tokens.component.nutritionKpi.regular.barRadius, height: "100%" },
});
