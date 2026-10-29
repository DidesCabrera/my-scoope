import { Fragment, useEffect, useMemo, useState } from "react";
import { StyleSheet, Text, useWindowDimensions, View } from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from "react-native-reanimated";
import { CalendarDays } from "lucide-react-native";

import type { CalendarCommitment, CalendarDay } from "@/api/calendar-types";
import { commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { useWeekDayLayout, WeekDayCell, WeekDayGrid, WeekDaySelectionRing } from "@/components/ui";
import { font, tokens } from "@/design/tokens";
import { currentWeekDays, type CurrentWeekDay } from "./current-week";

const WEEK_GAP = 18;
const CALENDAR_ACTION_GAP = 12;

function CurrentWeekDayCell({ commitments, day, localDate, planTone, onPress, panGesture }: { commitments: CalendarCommitment[]; day: CurrentWeekDay; localDate: string; planTone: "past" | "future" | null; onPress?: () => void; panGesture: ReturnType<typeof Gesture.Pan> }) {
  const { compact } = useWeekDayLayout();
  const tapGesture = useMemo(() => Gesture.Tap()
    .maxDistance(10)
    .requireExternalGestureToFail(panGesture)
    .runOnJS(true)
    .onEnd((_event, success) => { if (success) onPress?.(); }), [onPress, panGesture]);
  const circle = <View
    accessibilityActions={onPress ? [{ name: "activate" }] : undefined}
    accessibilityLabel={`Ver detalle del ${day.date}${day.isToday ? ", hoy" : ""}${commitments.length ? `; ${commitments.map((item) => commitmentPresentation[item.kind].label).join(", ")}` : ""}`}
    accessibilityRole={onPress ? "button" : undefined}
    accessible={Boolean(onPress)}
    onAccessibilityAction={onPress ? (event) => { if (event.nativeEvent.actionName === "activate") onPress(); } : undefined}
    style={[styles.dayCircle, compact && styles.dayCircleCompact, planTone === "past" && styles.dayCirclePastPlan, planTone === "future" && styles.dayCircleFuturePlan, day.isToday && styles.dayCircleToday, day.isToday && compact && styles.dayCircleTodayCompact]}>
    {day.isToday ? <WeekDaySelectionRing /> : null}
    <Text style={[styles.dayNumber, day.isToday && styles.dayNumberToday]}>{day.dayOfMonth}</Text>
    <Text style={[styles.monthLabel, day.isToday && styles.monthLabelToday]}>{day.monthLabel}</Text>
  </View>;
  return (
    <WeekDayCell label={day.label}>
      {onPress ? <GestureDetector gesture={tapGesture}>{circle}</GestureDetector> : circle}
      <View style={[styles.commitmentDotsSlot, day.date < localDate && styles.commitmentDotsPast]}>
        {commitments.map((commitment) => <View key={commitment.id} style={[styles.commitmentDot, { backgroundColor: commitmentPresentation[commitment.kind].color }]} />)}
      </View>
    </WeekDayCell>
  );
}

function CalendarActionPage({ onPress, panGesture, width }: { onPress: () => void; panGesture: ReturnType<typeof Gesture.Pan>; width: number }) {
  const tapGesture = useMemo(() => Gesture.Tap()
    .maxDistance(10)
    .requireExternalGestureToFail(panGesture)
    .runOnJS(true)
    .onEnd((_event, success) => { if (success) onPress(); }), [onPress, panGesture]);
  return <GestureDetector gesture={tapGesture}>
    <View accessibilityActions={[{ name: "activate" }]} accessibilityLabel="Ver calendario" accessibilityRole="button" accessible onAccessibilityAction={(event) => { if (event.nativeEvent.actionName === "activate") onPress(); }} style={[styles.calendarActionPage, { width }]}>
      <CalendarDays color={tokens.color.textMain} size={20} strokeWidth={2.2} />
      <Text style={styles.calendarActionLabel}>Ver calendario</Text>
    </View>
  </GestureDetector>;
}

export function CurrentWeekSection({ localDate, onOpenCalendar, onPressDay, weekDays = [] }: { localDate: string; onOpenCalendar?: () => void; onPressDay?: (date: string) => void; weekDays?: CalendarDay[] }) {
  const lastPage = onOpenCalendar ? 2 : 1;
  const { width: windowWidth } = useWindowDimensions();
  const [measuredWidth, setMeasuredWidth] = useState<number | null>(null);
  const pageWidth = measuredWidth ?? windowWidth - tokens.spacing.screen * 2 + 12;
  const pageStride = pageWidth + WEEK_GAP;
  const actionWidth = Math.min(144, Math.round(pageWidth * 0.42));
  const pageOffsets = useMemo(() => [0, pageStride, pageStride + CALENDAR_ACTION_GAP + actionWidth], [actionWidth, pageStride]);
  const selectedPage = useSharedValue(0);
  const translateX = useSharedValue(0);
  useEffect(() => {
    translateX.set(-pageOffsets[selectedPage.get()]);
  }, [pageOffsets, selectedPage, translateX]);
  const panGesture = Gesture.Pan()
    .activeOffsetX([-12, 12])
    .failOffsetY([-12, 12])
    .onUpdate((event) => {
      const atBoundary = (selectedPage.get() === 0 && event.translationX > 0)
        || (selectedPage.get() === lastPage && event.translationX < 0);
      translateX.set(-pageOffsets[selectedPage.get()] + event.translationX * (atBoundary ? 0.18 : 1));
    })
    .onEnd((event) => {
      if (event.translationX < -48 || event.velocityX < -450) selectedPage.set(Math.min(lastPage, selectedPage.get() + 1));
      else if (event.translationX > 48 || event.velocityX > 450) selectedPage.set(Math.max(0, selectedPage.get() - 1));
      translateX.set(withTiming(-pageOffsets[selectedPage.get()], { duration: 220 }));
    })
    .onFinalize((_event, success) => {
      if (!success) translateX.set(withTiming(-pageOffsets[selectedPage.get()], { duration: 220 }));
    });
  const trackStyle = useAnimatedStyle(() => ({ transform: [{ translateX: translateX.get() }] }));
  const weekDaysByDate = new Map(weekDays.map((day) => [day.calendar_date, day]));
  return (
    <View style={styles.section}>
      <GestureDetector gesture={panGesture}>
      <View
        onLayout={({ nativeEvent }) => {
          const width = Math.round(nativeEvent.layout.width);
          setMeasuredWidth((current) => current === width ? current : width);
        }}
        style={styles.carousel}>
          <Animated.View style={[styles.weekTrack, { width: pageWidth * 2 + WEEK_GAP + (onOpenCalendar ? CALENDAR_ACTION_GAP + actionWidth : 0) }, trackStyle]}>
          {[0, 1].map((page) => <Fragment key={page}>
            {page > 0 ? <View pointerEvents="none" style={styles.weekGap} /> : null}
            <View accessibilityLabel={page === 0 ? "Calendario de la semana actual" : "Calendario de la semana siguiente"} style={[styles.weekPage, { width: pageWidth }]}>
              <WeekDayGrid>
                {currentWeekDays(localDate, page).map((day) => (
                  <CurrentWeekDayCell commitments={weekDaysByDate.get(day.date)?.commitments ?? []} day={day} key={day.date} localDate={localDate} onPress={onPressDay ? () => onPressDay(day.date) : undefined} panGesture={panGesture} planTone={weekDaysByDate.get(day.date)?.has_plan ? day.date < localDate ? "past" : day.date > localDate ? "future" : null : null} />
                ))}
              </WeekDayGrid>
            </View>
          </Fragment>)}
          {onOpenCalendar ? <><View pointerEvents="none" style={styles.calendarActionGap} /><CalendarActionPage onPress={onOpenCalendar} panGesture={panGesture} width={actionWidth} /></> : null}
        </Animated.View>
      </View>
      </GestureDetector>
    </View>
  );
}

const styles = StyleSheet.create({
  commitmentDot: { borderRadius: 3, height: 5, width: 5 },
  commitmentDotsSlot: { alignItems: "center", flexDirection: "row", gap: 2, height: 5, justifyContent: "center", marginTop: -2 },
  commitmentDotsPast: { opacity: 0.5 },
  calendarActionGap: { width: CALENDAR_ACTION_GAP },
  calendarActionLabel: { color: tokens.color.textMain, fontSize: 13, fontWeight: tokens.weight.semibold, textAlign: "center" },
  calendarActionPage: { alignItems: "center", alignSelf: "stretch", backgroundColor: `${tokens.color.dailyPlan}80`, gap: 4, justifyContent: "center", paddingHorizontal: tokens.spacing.sm },
  dayCircle: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.pill, height: 44, justifyContent: "center", overflow: "visible", position: "relative", width: 44 },
  dayCircleCompact: { height: 40, width: 40 },
  dayCirclePastPlan: { backgroundColor: `${tokens.color.dailyPlan}1A` },
  dayCircleFuturePlan: { backgroundColor: `${tokens.color.dailyPlan}4D` },
  dayCircleToday: { backgroundColor: tokens.color.entityIconForeground, height: 42, margin: 1, width: 42 },
  dayCircleTodayCompact: { height: 38, width: 38 },
  dayNumber: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, fontVariant: ["tabular-nums"] },
  dayNumberToday: { color: tokens.color.surfaceApp, fontWeight: tokens.weight.bold },
  monthLabel: { color: tokens.color.textMuted, fontFamily: font.regular, fontSize: 9, fontWeight: tokens.weight.medium, lineHeight: 10 },
  monthLabelToday: { color: tokens.color.surfaceApp, fontWeight: tokens.weight.bold },
  carousel: { marginHorizontal: -6, overflow: "hidden" },
  section: { gap: tokens.spacing.md, minWidth: 0, width: "100%" },
  weekPage: { paddingHorizontal: 6 },
  weekGap: { width: WEEK_GAP },
  weekTrack: { flexDirection: "row" },
});
