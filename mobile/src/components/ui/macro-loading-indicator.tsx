import { useFocusEffect } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { AppState, StyleProp, StyleSheet, View, ViewStyle } from "react-native";
import Animated, { cancelAnimation, Easing, useAnimatedStyle, useReducedMotion, useSharedValue, withDelay, withRepeat, withSequence, withTiming } from "react-native-reanimated";

import { tokens } from "@/design/tokens";

type MacroLoadingIndicatorProps = { accessibilityLabel?: string; size?: "regular" | "small"; style?: StyleProp<ViewStyle> };

const MOTION = {
  protein: [45, 70, 35, 45],
  carbs: [60, 30, 75, 60],
  fat: [30, 50, 20, 30],
} as const;
const SPEED_PERCENT_PER_SECOND = 88;
const START_DELAY = { protein: 0, carbs: 140, fat: 280 } as const;

function transitionDuration(from: number, to: number): number {
  return Math.abs(to - from) / SPEED_PERCENT_PER_SECOND * 1000;
}

function MacroBar({ active, color, compact, delay, values }: { active: boolean; color: string; compact: boolean; delay: number; values: readonly number[] }) {
  const reducedMotion = useReducedMotion();
  const availableWidth = compact ? 32 : 79.2;
  const width = useSharedValue(availableWidth * values[0] / 100);
  const animatedStyle = useAnimatedStyle(() => ({ width: width.get() }));

  useEffect(() => {
    cancelAnimation(width);
    width.set(availableWidth * values[0] / 100);
    if (!active || reducedMotion) return;
    width.set(withDelay(
      delay,
      withRepeat(
        withSequence(...values.slice(1).map((value, index) => withTiming(availableWidth * value / 100, {
          duration: transitionDuration(values[index], value),
          easing: Easing.linear,
        }))),
        -1,
        false,
      ),
    ));
    return () => cancelAnimation(width);
  }, [active, availableWidth, delay, reducedMotion, values, width]);

  return <View style={[styles.barSlot, compact && styles.barSlotSmall]}><Animated.View style={[styles.fill, { backgroundColor: color }, animatedStyle]} /></View>;
}

export function MacroLoadingIndicator({ accessibilityLabel = "Cargando contenido", size = "regular", style }: MacroLoadingIndicatorProps) {
  const [focused, setFocused] = useState(false);
  const [appActive, setAppActive] = useState(AppState.currentState === "active");

  useFocusEffect(useCallback(() => {
    setFocused(true);
    return () => setFocused(false);
  }, []));

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (state) => setAppActive(state === "active"));
    return () => subscription.remove();
  }, []);

  const active = focused && appActive;
  const compact = size === "small";

  return (
    <View accessibilityLabel={accessibilityLabel} accessibilityLiveRegion="polite" accessibilityRole="progressbar" style={[styles.container, compact && styles.containerSmall, style]}>
      <MacroBar active={active} color={tokens.color.protein} compact={compact} delay={START_DELAY.protein} values={MOTION.protein} />
      <MacroBar active={active} color={tokens.color.carbs} compact={compact} delay={START_DELAY.carbs} values={MOTION.carbs} />
      <MacroBar active={active} color={tokens.color.fat} compact={compact} delay={START_DELAY.fat} values={MOTION.fat} />
    </View>
  );
}

const styles = StyleSheet.create({
  barSlot: { height: tokens.component.nutritionKpi.regular.barHeight * 0.72, width: "100%" },
  barSlotSmall: { height: 5 },
  container: { gap: tokens.component.nutritionKpi.regular.contentGap * 0.72, transform: [{ translateX: 18 }], width: 79.2 },
  containerSmall: { gap: 2, transform: [{ translateX: 0 }], width: 32 },
  fill: { borderRadius: tokens.component.nutritionKpi.regular.barRadius, height: "100%" },
});
