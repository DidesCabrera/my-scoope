import { ChevronRight, List, Paperclip } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { CalendarCommitment } from "@/api/calendar-types";
import { commitmentDayTitle, commitmentPresentation, commitmentSupportsFoods } from "@/components/calendarization/calendar-commitments";
import { calendarFoodPeriodDayCount } from "@/components/calendarization/calendar-food-period";
import { PickerCardAction } from "@/components/pickers/picker-card-action";
import { Card, Chip } from "@/components/ui";
import { tokens } from "@/design/tokens";

function readableDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric" })
    .format(new Date(`${value}T12:00:00`));
}

export function CalendarCommitmentListCard({ commitment, onCreateFoodList, onPress, showFoodListDetails = false }: {
  commitment: CalendarCommitment;
  onCreateFoodList?(): void;
  onPress(): void;
  showFoodListDetails?: boolean;
}) {
  const presentation = commitmentPresentation[commitment.kind];
  const Icon = presentation.icon;
  const hasAttachedFoods = Boolean(commitment.food_period_start && commitment.food_period_end);
  const showCreateFoodList = showFoodListDetails && commitmentSupportsFoods(commitment.kind) && !hasAttachedFoods && onCreateFoodList;
  return <Card style={styles.card}>
    <Pressable accessibilityLabel={`Ver ${presentation.label} del ${readableDate(commitment.calendar_date)}`} accessibilityRole="link" onPress={onPress} style={({ pressed }) => [styles.content, pressed && styles.pressed]}>
      <View style={styles.row}>
        <View style={[styles.icon, { backgroundColor: `${presentation.color}33` }]}>
          <Icon color={presentation.color} size={23} strokeWidth={2.1} />
        </View>
        <View style={styles.copy}>
          <Text style={styles.title}>{showFoodListDetails ? commitmentDayTitle[commitment.kind] : presentation.label}</Text>
          <Text style={styles.date}>{readableDate(commitment.calendar_date)}</Text>
          {commitment.note ? <Text style={styles.note}>{commitment.note}</Text> : null}
        </View>
        {!showFoodListDetails ? <ChevronRight color={tokens.color.textMuted} size={20} /> : null}
      </View>
      {showFoodListDetails && hasAttachedFoods ? <View style={styles.attachmentRow}>
        <View style={styles.attachmentIcon}><Paperclip accessibilityLabel="Lista de alimentos adjunta" color={tokens.color.textSoft} size={18} strokeWidth={2} /></View>
        <View style={styles.chips}>
          <Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={`${commitment.foods.length} ${commitment.foods.length === 1 ? "alimento" : "alimentos"}`} textColor={tokens.color.textMain} />
          <Chip backgroundColor={`${tokens.color.dailyPlan}1A`} borderColor={tokens.color.dailyPlan} label={`${commitment.food_plans_count} ${commitment.food_plans_count === 1 ? "plan" : "planes"}`} textColor={tokens.color.textMain} />
          <Chip backgroundColor={`${tokens.color.program}1A`} borderColor={tokens.color.program} label={`${calendarFoodPeriodDayCount(commitment.food_period_start!, commitment.food_period_end!)} ${calendarFoodPeriodDayCount(commitment.food_period_start!, commitment.food_period_end!) === 1 ? "día" : "días"}`} textColor={tokens.color.textMain} />
        </View>
      </View> : null}
    </Pressable>
    {showCreateFoodList ? <PickerCardAction icon={<List color={tokens.color.textMain} size={18} strokeWidth={2} />} label="Crear lista de alimentos" onPress={onCreateFoodList} subject={readableDate(commitment.calendar_date)} variant="mutedFullWidth" /> : null}
  </Card>;
}

const styles = StyleSheet.create({
  attachmentIcon: { alignItems: "center", justifyContent: "center", width: 40 },
  attachmentRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  card: { gap: tokens.spacing.sm },
  chips: { alignItems: "center", flex: 1, flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.xs },
  content: { gap: tokens.spacing.sm },
  copy: { flex: 1, gap: tokens.spacing.xs },
  date: { color: tokens.color.textMuted, fontSize: 13 },
  icon: { alignItems: "center", borderRadius: 10, height: 40, justifyContent: "center", width: 40 },
  note: { color: tokens.color.textMain, fontSize: 13, lineHeight: 19 },
  pressed: { opacity: 0.65 },
  row: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md },
  title: { color: tokens.color.textMain, fontSize: 16, fontWeight: tokens.weight.semibold },
});
