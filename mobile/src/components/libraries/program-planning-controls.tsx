import type { ReactNode } from "react";
import { Pressable, ScrollView, StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";
import { CalendarRange, ClipboardList, Plus } from "lucide-react-native";
import Svg, { Circle, Defs, LinearGradient, Stop } from "react-native-svg";

import { tokens } from "@/design/tokens";

export type ProgramPlanningDay = {
  filled: boolean;
  id: number | string;
  label: string;
};

export function ProgramWeekHeading({ detail, week }: { detail?: string; week: number }) {
  return (
    <View style={styles.weekHeading}>
      <View style={styles.weekHeadingIdentity}>
        <View style={styles.weekHeadingIcon}>
          <CalendarRange color={tokens.color.entityIconForeground} size={11} strokeWidth={2.4} />
        </View>
        <Text style={styles.weekHeadingTitle}>Semana {week}</Text>
      </View>
      {detail ? <Text style={styles.weekHeadingDetail}>{detail}</Text> : null}
    </View>
  );
}

function SelectedDayRing() {
  return (
    <View pointerEvents="none" style={styles.daySelectedRing}>
      <Svg height="100%" viewBox="0 0 100 100" width="100%">
        <Defs>
          <LinearGradient id="selected-day-gradient" x1="0" x2="1" y1="1" y2="0">
            <Stop offset="0" stopColor="#FEDA75" />
            <Stop offset="0.24" stopColor="#FA7E1E" />
            <Stop offset="0.52" stopColor="#D62976" />
            <Stop offset="0.76" stopColor="#962FBF" />
            <Stop offset="1" stopColor="#4F5BD5" />
          </LinearGradient>
        </Defs>
        <Circle cx="50" cy="50" fill="none" r="44" stroke="url(#selected-day-gradient)" strokeWidth="8" />
      </Svg>
    </View>
  );
}

export function ProgramWeekTabs({
  activeWeek,
  onChange,
  style,
  weeks,
}: {
  activeWeek: number;
  onChange(week: number): void;
  style?: StyleProp<ViewStyle>;
  weeks: number[];
}) {
  return (
    <View style={[styles.weekTabsViewport, style]}>
      <ScrollView
        accessibilityLabel="Semanas del programa"
        accessibilityRole="tablist"
        contentContainerStyle={styles.weekTabs}
        directionalLockEnabled
        horizontal
        nestedScrollEnabled
        style={styles.weekTabsScroll}
        showsHorizontalScrollIndicator={false}>
        {weeks.map((week) => {
          const selected = activeWeek === week;
          return (
            <Pressable
              accessibilityLabel={`Semana ${week}`}
              accessibilityRole="tab"
              accessibilityState={{ selected }}
              key={week}
              onPress={() => onChange(week)}
              style={({ pressed }) => [styles.weekTab, selected && styles.weekTabActive, pressed && styles.pressed]}>
              <Text style={[styles.weekTabText, selected && styles.weekTabTextActive]}>Semana {week}</Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

export function ProgramDaySelector({
  accessibilityLabel,
  children,
  days,
  onSelect,
  selectedId,
}: {
  accessibilityLabel: string;
  children?: ReactNode;
  days: ProgramPlanningDay[];
  onSelect(day: ProgramPlanningDay): void;
  selectedId: number | string | null;
}) {
  return (
    <View style={styles.daySelection}>
      <View accessibilityLabel={accessibilityLabel} style={styles.daysGrid}>
        {days.map((day) => {
          const selected = selectedId === day.id;
          return (
            <View key={day.id} style={styles.dayCell}>
              <Text style={styles.dayLabel}>{day.label}</Text>
              <Pressable
                accessibilityLabel={day.filled ? `${day.label}: ver plan diario` : `${day.label}: día sin plan`}
                accessibilityRole="button"
                accessibilityState={{ expanded: day.filled ? selected : undefined, selected }}
                disabled={!day.filled}
                onPress={() => onSelect(day)}
                style={({ pressed }) => [styles.dayCircle, !day.filled && styles.dayCircleEmpty, selected && styles.dayCircleSelected, pressed && styles.pressed]}>
                {selected ? <SelectedDayRing /> : null}
                {day.filled
                  ? <View style={styles.dayPlanIcon}><ClipboardList color={tokens.color.entityIconForeground} size={14} /></View>
                  : <Plus color={tokens.color.program} size={24} />}
              </Pressable>
            </View>
          );
        })}
      </View>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  dayCell: { alignItems: "center", flex: 1, gap: tokens.spacing.sm, minWidth: 0 },
  dayCircle: { alignItems: "center", aspectRatio: 1, backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 2, justifyContent: "center", maxWidth: 58, overflow: "visible", position: "relative", width: "100%" },
  dayCircleEmpty: { borderStyle: "dashed", opacity: 0.65 },
  dayCircleSelected: { borderColor: tokens.color.surfaceApp },
  dayLabel: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: "700" },
  dayPlanIcon: { alignItems: "center", backgroundColor: tokens.color.dailyPlan, borderRadius: tokens.spacing.compact, height: 24, justifyContent: "center", width: 24 },
  daySelectedRing: { bottom: -7, left: -7, position: "absolute", right: -7, top: -7 },
  daySelection: { gap: tokens.spacing.lg, minWidth: 0 },
  daysGrid: { flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "space-between" },
  pressed: { opacity: 0.68 },
  weekTab: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, justifyContent: "center", minHeight: 30, paddingHorizontal: tokens.spacing.md },
  weekTabActive: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  weekTabText: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "500" },
  weekTabTextActive: { color: tokens.color.surfaceApp },
  weekTabs: { flexDirection: "row", gap: tokens.spacing.compact },
  weekTabsScroll: { flexGrow: 0, width: "100%" },
  weekTabsViewport: { flexShrink: 1, minWidth: 0, width: "100%" },
  weekHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", minWidth: 0, width: "100%" },
  weekHeadingIdentity: { alignItems: "center", flexDirection: "row", flexShrink: 1, gap: tokens.spacing.compact, minWidth: 0 },
  weekHeadingIcon: { alignItems: "center", backgroundColor: tokens.color.program, borderRadius: 5, height: 18, justifyContent: "center", width: 18 },
  weekHeadingTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.semibold, letterSpacing: 0, lineHeight: 25 },
  weekHeadingDetail: { color: tokens.color.textSoft, fontSize: tokens.type.caption },
});
