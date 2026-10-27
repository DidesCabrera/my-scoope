import { ChevronRight } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { CalendarCommitment } from "@/api/calendar-types";
import { commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { Card } from "@/components/ui";
import { tokens } from "@/design/tokens";

function readableDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric" })
    .format(new Date(`${value}T12:00:00`));
}

export function CalendarCommitmentListCard({ commitment, onPress }: { commitment: CalendarCommitment; onPress(): void }) {
  const presentation = commitmentPresentation[commitment.kind];
  const Icon = presentation.icon;
  return <Pressable accessibilityLabel={`Ver ${presentation.label} del ${readableDate(commitment.calendar_date)}`} accessibilityRole="link" onPress={onPress} style={({ pressed }) => pressed && styles.pressed}>
    <Card>
      <View style={styles.row}>
        <View style={[styles.icon, { backgroundColor: `${presentation.color}33` }]}>
          <Icon color={presentation.color} size={23} strokeWidth={2.1} />
        </View>
        <View style={styles.copy}>
          <Text style={styles.title}>{presentation.label}</Text>
          <Text style={styles.date}>{readableDate(commitment.calendar_date)}</Text>
          {commitment.note ? <Text style={styles.note}>{commitment.note}</Text> : null}
        </View>
        <ChevronRight color={tokens.color.textMuted} size={20} />
      </View>
    </Card>
  </Pressable>;
}

const styles = StyleSheet.create({
  copy: { flex: 1, gap: tokens.spacing.xs },
  date: { color: tokens.color.textMuted, fontSize: 13 },
  icon: { alignItems: "center", borderRadius: 10, height: 40, justifyContent: "center", width: 40 },
  note: { color: tokens.color.textMain, fontSize: 13, lineHeight: 19 },
  pressed: { opacity: 0.65 },
  row: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  title: { color: tokens.color.textMain, fontSize: 16, fontWeight: tokens.weight.semibold },
});
