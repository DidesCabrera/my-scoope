import { StyleSheet, Text, View } from "react-native";

import { useWeekDayLayout, WeekDayCell, WeekDayGrid, WeekDaySelectionRing } from "@/components/ui";
import { font, tokens } from "@/design/tokens";
import { currentWeekDays, type CurrentWeekDay } from "./current-week";

function CurrentWeekDayCell({ day }: { day: CurrentWeekDay }) {
  const { compact } = useWeekDayLayout();
  return (
    <WeekDayCell accessibilityLabel={`${day.label}, ${day.date}${day.isToday ? ", hoy" : ""}`} label={day.label}>
      <View style={[styles.dayCircle, compact && styles.dayCircleCompact, day.isToday && styles.dayCircleToday]}>
        {day.isToday ? <WeekDaySelectionRing /> : null}
        <Text style={[styles.dayNumber, day.isToday && styles.dayNumberToday]}>{day.dayOfMonth}</Text>
        <Text style={[styles.monthLabel, day.isToday && styles.monthLabelToday]}>{day.monthLabel}</Text>
      </View>
    </WeekDayCell>
  );
}

export function CurrentWeekSection({ localDate }: { localDate: string }) {
  const days = currentWeekDays(localDate);
  return (
    <View accessibilityLabel="Calendario de la semana actual" style={styles.section}>
      <WeekDayGrid>
        {days.map((day) => (
          <CurrentWeekDayCell day={day} key={day.date} />
        ))}
      </WeekDayGrid>
    </View>
  );
}

const styles = StyleSheet.create({
  dayCircle: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, height: 44, justifyContent: "center", overflow: "visible", position: "relative", width: 44 },
  dayCircleCompact: { height: 40, width: 40 },
  dayCircleToday: { backgroundColor: tokens.color.entityIconForeground },
  dayNumber: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, fontVariant: ["tabular-nums"] },
  dayNumberToday: { color: tokens.color.surfaceApp },
  monthLabel: { color: tokens.color.textMuted, fontFamily: font.regular, fontSize: 9, fontWeight: "300", lineHeight: 10 },
  monthLabelToday: { color: tokens.color.surfaceApp, fontWeight: tokens.weight.regular },
  section: { gap: tokens.spacing.md, minWidth: 0, width: "100%" },
});
