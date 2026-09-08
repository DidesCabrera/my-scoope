import type { ReactNode } from "react";
import { Pressable, ScrollView, StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";
import { CalendarRange, ClipboardList, Plus } from "lucide-react-native";

import { tokens } from "@/design/tokens";
import { StructuralIndicators, useWeekDayLayout, WeekDayCell, WeekDayGrid, WeekDaySelectionRing } from "@/components/ui";

export type ProgramPlanningDay = {
  dayOfMonth?: number;
  disabled?: boolean;
  filled: boolean;
  id: number | string;
  isToday?: boolean;
  label: string;
  monthLabel?: string;
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
      {detail ? <StructuralIndicators indicators={[{ icon: "week", iconPosition: "leading", label: "periodo", tone: "surfaceMuted", value: detail }]} /> : null}
    </View>
  );
}

function ProgramDayCell({ allowEmptySelection, day, onSelect, selected }: { allowEmptySelection: boolean; day: ProgramPlanningDay; onSelect(day: ProgramPlanningDay): void; selected: boolean }) {
  const { compact } = useWeekDayLayout();
  return (
    <WeekDayCell label={day.label}>
      <Pressable
        accessibilityLabel={day.filled ? `${day.label}: ver plan diario` : day.disabled ? `${day.label}: día sin plan, no editable` : `${day.label}: agregar plan diario`}
        accessibilityRole="button"
        accessibilityState={{ expanded: day.filled ? selected : undefined, selected }}
        disabled={day.disabled || (!day.filled && !allowEmptySelection)}
        hitSlop={compact ? 2 : undefined}
        onPress={() => onSelect(day)}
        style={({ pressed }) => [styles.dayCircle, compact && styles.dayCircleCompact, !day.filled && styles.dayCircleEmpty, day.isToday && styles.dayCircleToday, selected && styles.dayCircleSelected, pressed && styles.pressed]}>
        {selected ? <WeekDaySelectionRing /> : null}
        {day.dayOfMonth != null && day.monthLabel ? (
          <>
            <Text style={[styles.dayDateNumber, day.isToday && styles.dayDateTextToday]}>{day.dayOfMonth}</Text>
            <Text style={[styles.dayDateMonth, day.isToday && styles.dayDateTextToday]}>{day.monthLabel}</Text>
            {!day.filled && !day.disabled ? (
              <View style={styles.dayAddBadge}><Plus color={tokens.color.textMain} size={10} strokeWidth={2.5} /></View>
            ) : null}
          </>
        ) : day.filled ? (
          <View style={styles.dayPlanIcon}><ClipboardList color={tokens.color.entityIconForeground} size={14} /></View>
        ) : (
          <Plus color={tokens.color.textMain} size={24} />
        )}
      </Pressable>
    </WeekDayCell>
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
  allowEmptySelection = false,
  children,
  days,
  onSelect,
  selectedId,
}: {
  accessibilityLabel: string;
  allowEmptySelection?: boolean;
  children?: ReactNode;
  days: ProgramPlanningDay[];
  onSelect(day: ProgramPlanningDay): void;
  selectedId: number | string | null;
}) {
  return (
    <View style={styles.daySelection}>
      <WeekDayGrid accessibilityLabel={accessibilityLabel}>
        {days.map((day) => {
          const selected = selectedId === day.id;
          return (
            <ProgramDayCell allowEmptySelection={allowEmptySelection} day={day} key={day.id} onSelect={onSelect} selected={selected} />
          );
        })}
      </WeekDayGrid>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  dayCircle: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, height: 44, justifyContent: "center", overflow: "visible", position: "relative", width: 44 },
  dayCircleCompact: { height: 40, width: 40 },
  dayCircleEmpty: { borderStyle: "dashed", opacity: 0.65 },
  dayCircleSelected: { borderColor: tokens.color.surfaceApp },
  dayCircleToday: { backgroundColor: tokens.color.entityIconForeground, borderStyle: "solid", opacity: 1 },
  dayAddBadge: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: 8, borderWidth: 1, bottom: -3, height: 16, justifyContent: "center", position: "absolute", right: -3, width: 16 },
  dayDateMonth: { color: tokens.color.textMuted, fontSize: 8, fontWeight: tokens.weight.regular, lineHeight: 9 },
  dayDateNumber: { color: tokens.color.textMain, fontSize: 12, fontWeight: tokens.weight.semibold, lineHeight: 14 },
  dayDateTextToday: { color: tokens.color.surfaceApp },
  dayPlanIcon: { alignItems: "center", backgroundColor: tokens.color.dailyPlan, borderRadius: tokens.spacing.compact, height: 24, justifyContent: "center", width: 24 },
  daySelection: { gap: tokens.spacing.lg, minWidth: 0 },
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
});
