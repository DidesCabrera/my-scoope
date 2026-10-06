import type { ReactNode } from "react";
import { Activity, Calendar1, Carrot, ClipboardList, Rows3, Utensils } from "lucide-react-native";
import { type StyleProp, StyleSheet, Text, type TextStyle, View } from "react-native";

import { tokens } from "@/design/tokens";

type SectionTitleIcon = "chart" | "comparison" | "dailyPlans" | "foods" | "meals" | "planning";

function iconForSectionTitle(title: string): SectionTitleIcon | undefined {
  const normalizedTitle = title.trim().toLocaleLowerCase("es");
  if (normalizedTitle === "gráfico de la semana") return "chart";
  if (normalizedTitle === "composición" || normalizedTitle.startsWith("tabla de comparación")) return "comparison";
  if (normalizedTitle.startsWith("alimentos en est")) return "foods";
  if (normalizedTitle === "planificación semanal") return "planning";
  if (normalizedTitle.startsWith("detalle de cada comida")) return "meals";
  if (normalizedTitle === "planes diarios esta semana") return "dailyPlans";
  return undefined;
}

export function SectionHeading({ title, detail, icon, titleStyle }: { title: string; detail?: string; icon?: ReactNode; titleStyle?: StyleProp<TextStyle> }) {
  const titleIcon = icon ? undefined : iconForSectionTitle(title);
  const iconProps = { color: tokens.color.entityIconForeground, size: 18 };
  const resolvedIcon = icon
    ?? (titleIcon === "chart" ? <Activity {...iconProps} />
      : titleIcon === "comparison" ? <Rows3 {...iconProps} />
      : titleIcon === "foods" ? <Carrot {...iconProps} />
      : titleIcon === "planning" ? <Calendar1 {...iconProps} />
      : titleIcon === "meals" ? <Utensils {...iconProps} />
      : titleIcon === "dailyPlans" ? <ClipboardList {...iconProps} />
      : null);
  return (
    <View style={styles.sectionHeading}>
      <View style={styles.sectionIdentity}>
        {resolvedIcon ? <View style={styles.sectionIcon}>{resolvedIcon}</View> : null}
        <Text style={[styles.sectionTitle, titleStyle]}>{title}</Text>
      </View>
      {detail ? <Text style={styles.sectionDetail}>{detail}</Text> : null}
    </View>
  );
}

/** @deprecated Use SectionHeading for the complete structural section header. */
export function SectionTitle(props: { title: string; detail?: string; titleStyle?: StyleProp<TextStyle> }) {
  return <SectionHeading {...props} />;
}

export const textStyles = StyleSheet.create({
  body: { color: tokens.color.textMain, fontSize: tokens.type.body, lineHeight: 24 },
  muted: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  caption: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 18 },
  strong: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: "700" },
});

const styles = StyleSheet.create({
  sectionHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", marginBottom: tokens.spacing.xs, marginTop: tokens.spacing.sm, minWidth: 0 },
  sectionIdentity: { alignItems: "center", flexDirection: "row", flexShrink: 1, gap: tokens.spacing.sm, minWidth: 0 },
  sectionIcon: { alignItems: "center", justifyContent: "center" },
  sectionTitle: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  sectionDetail: { color: tokens.color.textSoft, fontSize: tokens.type.caption },
});
