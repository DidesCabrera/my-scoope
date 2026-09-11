import { createContext, type ReactNode, useContext, useId, useState } from "react";
import { type LayoutChangeEvent, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Defs, LinearGradient, Stop } from "react-native-svg";

import { tokens } from "@/design/tokens";

const compactWeekDayWidth = 350;
const WeekDayLayoutContext = createContext({ compact: false });

export function useWeekDayLayout() {
  return useContext(WeekDayLayoutContext);
}

export function WeekDayGrid({ accessibilityLabel, children }: { accessibilityLabel?: string; children: ReactNode }) {
  const [availableWidth, setAvailableWidth] = useState<number | null>(null);
  const compact = availableWidth != null && availableWidth < compactWeekDayWidth;

  function measure(event: LayoutChangeEvent) {
    const nextWidth = Math.round(event.nativeEvent.layout.width);
    setAvailableWidth((current) => current === nextWidth ? current : nextWidth);
  }

  return (
    <WeekDayLayoutContext.Provider value={{ compact }}>
      <View
        accessibilityLabel={accessibilityLabel}
        onLayout={measure}
        style={[styles.grid, compact && styles.gridCompact]}>
        {children}
      </View>
    </WeekDayLayoutContext.Provider>
  );
}

export function WeekDayCell({ accessibilityLabel, children, label }: { accessibilityLabel?: string; children: ReactNode; label: string }) {
  return (
    <View accessibilityLabel={accessibilityLabel} accessible={Boolean(accessibilityLabel)} style={styles.cell}>
      <Text style={styles.label}>{label}</Text>
      {children}
    </View>
  );
}

export function WeekDaySelectionRing() {
  const gradientId = useId().replace(/:/g, "");
  return (
    <View pointerEvents="none" style={styles.selectionRing}>
      <Svg height="100%" viewBox="0 0 100 100" width="100%">
        <Defs>
          <LinearGradient id={gradientId} x1="0" x2="1" y1="1" y2="0">
            <Stop offset="0" stopColor="#FEDA75" />
            <Stop offset="0.24" stopColor="#FA7E1E" />
            <Stop offset="0.52" stopColor="#D62976" />
            <Stop offset="0.76" stopColor="#962FBF" />
            <Stop offset="1" stopColor="#4F5BD5" />
          </LinearGradient>
        </Defs>
        <Circle cx="50" cy="50" fill="none" r="44" stroke={`url(#${gradientId})`} strokeWidth="6" />
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  cell: { alignItems: "center", flex: 1, gap: tokens.spacing.sm, minWidth: 0 },
  grid: { alignSelf: "stretch", flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "space-between", marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minWidth: 0 },
  gridCompact: { gap: tokens.spacing.xs },
  label: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.bold },
  selectionRing: { bottom: -7, left: -7, position: "absolute", right: -7, top: -7 },
});
