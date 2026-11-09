import { Pin } from "lucide-react-native";
import { useId } from "react";
import { StyleSheet, Text, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import type { CalendarCommitment } from "@/api/calendar-types";
import { commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { Chip } from "@/components/ui";
import { tokens } from "@/design/tokens";

function readableDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric" })
    .format(new Date(`${value}T12:00:00`));
}

function TodayChip() {
  const gradientId = useId().replace(/:/g, "");
  return <View accessibilityLabel="Hoy" accessible style={styles.todayChip}>
      <Svg aria-hidden height="100%" pointerEvents="none" style={StyleSheet.absoluteFill} width="100%">
        <Defs>
          <LinearGradient id={gradientId} x1="0" x2="1" y1="0" y2="1">
            <Stop offset="0" stopColor={tokens.color.protein} />
            <Stop offset="0.5" stopColor={tokens.color.carbs} />
            <Stop offset="1" stopColor={tokens.color.fat} />
          </LinearGradient>
        </Defs>
        <Rect fill={`url(#${gradientId})`} height="100%" rx={8} ry={8} width="100%" />
      </Svg>
      <Text numberOfLines={1} style={styles.todayLabel}>Hoy</Text>
    </View>;
}

export function CalendarDaySectionHeading({ commitments = [], date, hasPlan = false, today }: { commitments?: CalendarCommitment[]; date: string; hasPlan?: boolean; today: string }) {
  const isToday = date === today;
  return <View style={styles.section}>
    <View style={styles.heading}>
      <Pin color={tokens.color.textMain} size={16} strokeWidth={2} />
      {isToday ? <TodayChip /> : null}
      <Text accessibilityRole="header" style={styles.date}>{readableDate(date)}</Text>
    </View>
    {isToday && (hasPlan || commitments.length) ? <View accessibilityLabel="Planificado para hoy" style={styles.planChips}>
      {hasPlan ? <Chip backgroundColor={`${tokens.color.dailyPlan}1A`} borderColor={tokens.color.dailyPlan} label="Minuta diaria" textColor={tokens.color.textMain} /> : null}
      {commitments.map((commitment) => {
        const presentation = commitmentPresentation[commitment.kind];
        return <Chip backgroundColor={`${presentation.color}1A`} borderColor={presentation.color} key={commitment.id} label={presentation.label} textColor={tokens.color.textMain} />;
      })}
    </View> : null}
  </View>;
}

const styles = StyleSheet.create({
  date: { color: tokens.color.textMain, flexShrink: 1, fontSize: 16, fontWeight: tokens.weight.bold },
  heading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  planChips: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.xs, marginBottom: 8 },
  section: { gap: tokens.spacing.sm },
  todayChip: { alignItems: "center", borderRadius: 7, flexShrink: 0, height: 24, justifyContent: "center", marginRight: 4, overflow: "hidden", width: 44 },
  todayLabel: { color: tokens.color.surfaceApp, fontSize: 14, fontWeight: tokens.weight.bold, lineHeight: 18 },
});
