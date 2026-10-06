import type { LucideIcon } from "lucide-react-native";
import { BadgeInfo, BookMarked, CalendarClock, ChartNoAxesColumnIncreasing, Files, Flame, HeartPulse, LibraryBig, LineChart, Salad, Scale, Sparkles, UserPlus } from "lucide-react-native";
import { StyleSheet, View } from "react-native";

import { tokens } from "@/design/tokens";

const icons: Record<string, LucideIcon> = {
  "badge-info": BadgeInfo, "book-marked": BookMarked, "calendar-clock": CalendarClock,
  "chart-no-axes-column-increasing": ChartNoAxesColumnIncreasing, files: Files, flame: Flame,
  "heart-pulse": HeartPulse, "library-big": LibraryBig, "line-chart": LineChart,
  salad: Salad, scale: Scale, sparkles: Sparkles, "user-plus": UserPlus,
};

export function LearningIcon({ name }: { name: string }) {
  const Icon = icons[name] ?? BookMarked;
  return <View style={styles.icon}><Icon color={tokens.color.textMain} size={22} strokeWidth={2} /></View>;
}

export const learningStyles = StyleSheet.create({
  card: { gap: tokens.spacing.md },
  cardHeading: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  cardText: { flex: 1, gap: 4 },
  intro: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 22 },
  summary: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 19 },
  title: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold, lineHeight: 22 },
});

const styles = StyleSheet.create({
  icon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 40, justifyContent: "center", width: 40 },
});
