import { useFocusEffect } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { AppState, StyleProp, StyleSheet, View, ViewStyle } from "react-native";
import Animated, { cancelAnimation, Easing, useAnimatedStyle, useReducedMotion, useSharedValue, withDelay, withRepeat, withSequence, withTiming } from "react-native-reanimated";

import { tokens } from "@/design/tokens";

type MacroLoadingIndicatorProps = { accessibilityLabel?: string; style?: StyleProp<ViewStyle> };

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

function MacroBar({ active, color, delay, values }: { active: boolean; color: string; delay: number; values: readonly number[] }) {
  const reducedMotion = useReducedMotion();
  const width = useSharedValue(values[0] / 100);
  const animatedStyle = useAnimatedStyle(() => ({ transform: [{ scaleX: width.get() }] }));

  useEffect(() => {
    cancelAnimation(width);
    width.set(values[0] / 100);
    if (!active || reducedMotion) return;
    width.set(withDelay(
      delay,
      withRepeat(
        withSequence(...values.slice(1).map((value, index) => withTiming(value / 100, {
          duration: transitionDuration(values[index], value),
          easing: Easing.linear,
        }))),
        -1,
        false,
      ),
    ));
    return () => cancelAnimation(width);
  }, [active, delay, reducedMotion, values, width]);

  return <View style={styles.barSlot}><Animated.View style={[styles.fill, { backgroundColor: color }, animatedStyle]} /></View>;
}

export function MacroLoadingIndicator({ accessibilityLabel = "Cargando contenido", style }: MacroLoadingIndicatorProps) {
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

  return (
    <View accessibilityLabel={accessibilityLabel} accessibilityLiveRegion="polite" accessibilityRole="progressbar" style={[styles.container, style]}>
      <MacroBar active={active} color={tokens.color.protein} delay={START_DELAY.protein} values={MOTION.protein} />
      <MacroBar active={active} color={tokens.color.carbs} delay={START_DELAY.carbs} values={MOTION.carbs} />
      <MacroBar active={active} color={tokens.color.fat} delay={START_DELAY.fat} values={MOTION.fat} />
    </View>
  );
}

const styles = StyleSheet.create({
  barSlot: { height: tokens.component.nutritionKpi.regular.barHeight * 0.72, width: "100%" },
  container: { gap: tokens.component.nutritionKpi.regular.contentGap * 0.72, transform: [{ translateX: 18 }], width: 79.2 },
  fill: { borderRadius: tokens.component.nutritionKpi.regular.barRadius, height: "100%", transformOrigin: "left", width: "100%" },
});
