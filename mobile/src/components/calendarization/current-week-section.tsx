import { CalendarRange } from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";

import { SectionHeading } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { currentWeekDays, currentWeekRange } from "./current-week";

export function CurrentWeekSection({ localDate }: { localDate: string }) {
  const days = currentWeekDays(localDate);
  return (
    <View accessibilityLabel="Semana en curso" style={styles.section}>
      <SectionHeading
        detail={currentWeekRange(localDate)}
        icon={<CalendarRange color={tokens.color.textMuted} size={18} strokeWidth={2.2} />}
        title="Semana en curso"
      />
      <View style={styles.days}>
        {days.map((day) => (
          <View accessibilityLabel={`${day.label}, ${day.date}${day.isToday ? ", hoy" : ""}`} accessible key={day.date} style={styles.day}>
            <Text style={[styles.dayLabel, day.isToday && styles.dayLabelToday]}>{day.label}</Text>
            <View style={[styles.dayCircle, day.isToday && styles.dayCircleToday]}>
              {day.isToday ? <View pointerEvents="none" style={styles.todayRing} /> : null}
              <Text style={[styles.dayNumber, day.isToday && styles.dayNumberToday]}>{day.dayOfMonth}</Text>
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  day: { alignItems: "center", flex: 1, gap: tokens.spacing.sm, minWidth: 0 },
  dayCircle: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, height: 38, justifyContent: "center", overflow: "visible", position: "relative", width: 38 },
  dayCircleToday: { backgroundColor: tokens.color.entityIconForeground },
  dayLabel: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.semibold },
  dayLabelToday: { color: tokens.color.textMain },
  dayNumber: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, fontVariant: ["tabular-nums"] },
  dayNumberToday: { color: tokens.color.surfaceApp },
  days: { flexDirection: "row", gap: tokens.spacing.compact, justifyContent: "space-between" },
  section: { gap: tokens.spacing.md, minWidth: 0, width: "100%" },
  todayRing: { borderColor: tokens.color.dailyPlan, borderRadius: tokens.radius.pill, borderWidth: 3, bottom: -5, left: -5, position: "absolute", right: -5, top: -5 },
});
