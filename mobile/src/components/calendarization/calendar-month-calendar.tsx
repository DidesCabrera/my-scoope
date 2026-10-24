import { ChevronLeft, ChevronRight } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { CalendarDay } from "@/api/calendar-types";
import { commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { monthKeyFromDate, monthLabel } from "@/components/calendarization/calendar-month";
import { InlineNotice } from "@/components/ui";
import { tokens } from "@/design/tokens";

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

export function CalendarMonthPlaceholder() {
  return <View accessibilityLabel="Cargando días del mes" accessible style={styles.grid}>
    {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`placeholder-weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
    {Array.from({ length: 42 }, (_, index) => <View key={`placeholder-day-${index}`} style={styles.gridPlaceholderDate}><View style={styles.gridPlaceholderNumber} /></View>)}
  </View>;
}

export function CalendarMonthCalendar({ days, error, localDate, onChangeMonth, onOpenDay, onReturnToCurrentMonth, visibleMonth }: {
  days: CalendarDay[];
  error?: string | null;
  localDate: string;
  onChangeMonth(delta: number): void;
  onOpenDay(date: string): void;
  onReturnToCurrentMonth(): void;
  visibleMonth: string;
}) {
  const currentMonth = monthKeyFromDate(localDate);
  return <View style={styles.calendarSection}>
    <View style={styles.monthNavigation}>
      <Pressable accessibilityLabel="Mes anterior" accessibilityRole="button" onPress={() => onChangeMonth(-1)} style={styles.monthArrow}>
        <ChevronLeft color={tokens.color.textMain} size={20} />
      </Pressable>
      <Text accessibilityRole="header" style={styles.monthTitle}>{monthLabel(visibleMonth)}</Text>
      <Pressable accessibilityLabel="Mes siguiente" accessibilityRole="button" onPress={() => onChangeMonth(1)} style={styles.monthArrow}>
        <ChevronRight color={tokens.color.textMain} size={20} />
      </Pressable>
    </View>
    {visibleMonth !== currentMonth ? <Pressable accessibilityRole="button" onPress={onReturnToCurrentMonth}><Text style={styles.monthTodayLink}>Volver al mes actual</Text></Pressable> : null}
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    {!days.length && !error ? <CalendarMonthPlaceholder /> : <View style={styles.grid}>
      {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
      {days.map((day) => (
        <Pressable
          accessibilityLabel={`${dateLabel(day.calendar_date)}: ${day.has_plan ? "Con plan" : "Sin plan"}${day.commitments?.length ? `; ${day.commitments.map((item) => commitmentPresentation[item.kind].label).join(", ")}` : ""}`}
          accessibilityRole="button"
          key={day.calendar_date}
          onPress={() => onOpenDay(day.calendar_date)}
          style={[styles.gridDate, day.has_plan && styles.gridDateFilled, monthKeyFromDate(day.calendar_date) !== visibleMonth && styles.gridDateAdjacent, day.calendar_date === localDate && styles.gridDateToday]}>
          <Text style={[styles.gridNumber, day.has_plan && styles.gridNumberWithPlan]}>{day.calendar_date.slice(8, 10)}</Text>
          {day.commitments?.length ? <View style={styles.gridCommitmentDots}>{day.commitments.map((item) => <View key={item.id} style={[styles.gridCommitmentDot, { backgroundColor: commitmentPresentation[item.kind].color }]} />)}</View> : null}
        </Pressable>
      ))}
    </View>}
  </View>;
}

const styles = StyleSheet.create({
  calendarSection: { marginBottom: 12, marginTop: -12, paddingVertical: tokens.spacing.sm },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: tokens.spacing.sm },
  gridCommitmentDots: { bottom: 2, flexDirection: "row", gap: 2, position: "absolute" },
  gridCommitmentDot: { borderRadius: 3, height: 4, width: 4 },
  gridDate: { alignItems: "center", borderColor: "transparent", borderRadius: 10, borderWidth: 2, justifyContent: "center", minHeight: 38, width: "13.5%" },
  gridDateAdjacent: { opacity: 0.5 },
  gridDateFilled: { backgroundColor: `${tokens.color.dailyPlan}33` },
  gridDateToday: { borderColor: tokens.color.success },
  gridHeader: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center", width: "13.5%" },
  gridNumber: { color: tokens.color.textMain, fontSize: 14, fontWeight: "500" },
  gridNumberWithPlan: { color: tokens.color.textMain, fontWeight: "700" },
  gridPlaceholderDate: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: 10, justifyContent: "center", minHeight: 38, opacity: 0.55, width: "13.5%" },
  gridPlaceholderNumber: { backgroundColor: tokens.color.borderStrong, borderRadius: tokens.radius.pill, height: 5, opacity: 0.7, width: 14 },
  monthArrow: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: 10, borderWidth: 1, height: 36, justifyContent: "center", width: 36 },
  monthNavigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: tokens.spacing.md },
  monthTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "600" },
  monthTodayLink: { color: tokens.color.interactivePrimary, fontSize: 13, marginBottom: tokens.spacing.sm, textAlign: "center" },
});
