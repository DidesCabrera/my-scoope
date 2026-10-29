import { ChevronLeft, ChevronRight } from "lucide-react-native";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { CalendarDay } from "@/api/calendar-types";
import { commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { CalendarTodayOutline } from "@/components/calendarization/calendar-today-outline";
import { isCurrentMonthFromToday, monthKeyFromDate, monthLabel } from "@/components/calendarization/calendar-month";
import { InlineNotice } from "@/components/ui";
import { tokens } from "@/design/tokens";

export const calendarTopSpacing = -24;

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

export function CalendarMonthPlaceholder() {
  return <View accessibilityLabel="Cargando días del mes" accessible style={styles.grid}>
    {(["L", "M", "M", "J", "V", "S", "D"] as const).map((label, index) => <Text key={`placeholder-weekday-${index}`} style={styles.gridHeader}>{label}</Text>)}
    {Array.from({ length: 42 }, (_, index) => <View key={`placeholder-day-${index}`} style={styles.gridPlaceholderDate}><View style={styles.gridPlaceholderNumber} /></View>)}
  </View>;
}

export function CalendarMonthCalendar({ days, embedded = false, error, localDate, onChangeMonth, onOpenDay, onReturnToCurrentMonth, selectedDate, visibleMonth }: {
  days: CalendarDay[];
  embedded?: boolean;
  error?: string | null;
  localDate: string;
  onChangeMonth(delta: number): void;
  onOpenDay(date: string): void;
  onReturnToCurrentMonth(): void;
  selectedDate?: string;
  visibleMonth: string;
}) {
  const currentMonth = monthKeyFromDate(localDate);
  const [todaySize, setTodaySize] = useState({ width: 0, height: 0 });
  return <View style={[styles.calendarSection, embedded && styles.calendarSectionEmbedded]}>
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
          accessibilityState={{ selected: day.calendar_date === selectedDate }}
          key={day.calendar_date}
          onLayout={day.calendar_date === localDate ? ({ nativeEvent: { layout } }) => {
            setTodaySize((current) => current.width === layout.width && current.height === layout.height ? current : { width: layout.width, height: layout.height });
          } : undefined}
          onPress={() => onOpenDay(day.calendar_date)}
          style={[styles.gridDate, day.has_plan && styles.gridDateFilled, day.has_plan && isCurrentMonthFromToday(day.calendar_date, localDate) && styles.gridDateUpcomingFilled, monthKeyFromDate(day.calendar_date) !== visibleMonth && styles.gridDateAdjacent, day.calendar_date === localDate && styles.gridDateToday, day.calendar_date === selectedDate && day.calendar_date !== localDate && styles.gridDateSelected]}>
          <Text style={[styles.gridNumber, day.has_plan && styles.gridNumberWithPlan, day.calendar_date < localDate && styles.gridNumberPast]}>{day.calendar_date.slice(8, 10)}</Text>
          {day.commitments?.length ? <View style={[styles.gridCommitmentDots, day.calendar_date < localDate && styles.gridCommitmentDotsPast, day.calendar_date === localDate && styles.gridCommitmentDotsToday]}>{day.commitments.map((item) => <View key={item.id} style={[styles.gridCommitmentDot, { backgroundColor: commitmentPresentation[item.kind].color }]} />)}</View> : null}
          {day.calendar_date === localDate ? <CalendarTodayOutline {...todaySize} /> : null}
        </Pressable>
      ))}
    </View>}
  </View>;
}

const styles = StyleSheet.create({
  calendarSection: { marginBottom: 12, marginTop: calendarTopSpacing, paddingVertical: tokens.spacing.sm },
  calendarSectionEmbedded: { marginBottom: 0, marginTop: 0, paddingVertical: 0 },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: tokens.spacing.sm },
  gridCommitmentDots: { bottom: 3, flexDirection: "row", gap: 2, position: "absolute" },
  gridCommitmentDotsPast: { opacity: 0.5 },
  gridCommitmentDotsToday: { bottom: 6 },
  gridCommitmentDot: { borderRadius: 3, height: 4, width: 4 },
  gridDate: { alignItems: "center", borderColor: "transparent", borderRadius: 10, borderWidth: 2, justifyContent: "center", minHeight: 38, width: "13.5%" },
  gridDateToday: { borderWidth: 0 },
  gridDateSelected: { borderColor: tokens.color.interactivePrimary },
  gridDateAdjacent: { opacity: 0.5 },
  gridDateFilled: { backgroundColor: `${tokens.color.dailyPlan}2E` },
  gridDateUpcomingFilled: { backgroundColor: `${tokens.color.dailyPlan}59` },
  gridHeader: { color: tokens.color.textMuted, fontSize: 11, textAlign: "center", width: "13.5%" },
  gridNumber: { color: tokens.color.textMain, fontSize: 14, fontWeight: "500" },
  gridNumberPast: { opacity: 0.8 },
  gridNumberWithPlan: { color: tokens.color.textMain, fontWeight: "700" },
  gridPlaceholderDate: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: 10, justifyContent: "center", minHeight: 38, opacity: 0.55, width: "13.5%" },
  gridPlaceholderNumber: { backgroundColor: tokens.color.borderStrong, borderRadius: tokens.radius.pill, height: 5, opacity: 0.7, width: 14 },
  monthArrow: { alignItems: "center", height: 36, justifyContent: "center", width: 36 },
  monthNavigation: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: tokens.spacing.md },
  monthTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "600" },
  monthTodayLink: { color: tokens.color.interactivePrimary, fontSize: 13, marginBottom: tokens.spacing.sm, textAlign: "center" },
});
