import type { ReactNode } from "react";
import { Calendar1, Carrot, ClipboardList, Rows3, Utensils } from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

type SectionTitleIcon = "comparison" | "dailyPlans" | "foods" | "meals" | "planning";

function iconForSectionTitle(title: string): SectionTitleIcon | undefined {
  const normalizedTitle = title.trim().toLocaleLowerCase("es");
  if (normalizedTitle.startsWith("tabla de comparación")) return "comparison";
  if (normalizedTitle.startsWith("alimentos en est")) return "foods";
  if (normalizedTitle === "planificación semanal") return "planning";
  if (normalizedTitle.startsWith("detalle de cada comida")) return "meals";
  if (normalizedTitle === "planes diarios esta semana") return "dailyPlans";
  return undefined;
}

export function SectionHeading({ title, detail, icon }: { title: string; detail?: string; icon?: ReactNode }) {
  const titleIcon = icon ? undefined : iconForSectionTitle(title);
  const iconProps = { color: tokens.color.entityIconForeground, size: 18 };
  const resolvedIcon = icon
    ?? (titleIcon === "comparison" ? <Rows3 {...iconProps} />
      : titleIcon === "foods" ? <Carrot {...iconProps} />
      : titleIcon === "planning" ? <Calendar1 {...iconProps} />
      : titleIcon === "meals" ? <Utensils {...iconProps} />
      : titleIcon === "dailyPlans" ? <ClipboardList {...iconProps} />
      : null);
  return (
    <View style={styles.sectionHeading}>
      <View style={styles.sectionIdentity}>
        {resolvedIcon ? <View style={styles.sectionIcon}>{resolvedIcon}</View> : null}
        <Text style={styles.sectionTitle}>{title}</Text>
      </View>
      {detail ? <Text style={styles.sectionDetail}>{detail}</Text> : null}
    </View>
  );
}

/** @deprecated Use SectionHeading for the complete structural section header. */
export function SectionTitle(props: { title: string; detail?: string }) {
  return <SectionHeading {...props} />;
}

export const textStyles = StyleSheet.create({
  body: { color: tokens.color.textMain, fontSize: tokens.type.body, lineHeight: 24 },
  muted: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  caption: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 18 },
  strong: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: "700" },
});

const styles = StyleSheet.create({
  sectionHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", marginTop: tokens.spacing.sm, minWidth: 0 },
  sectionIdentity: { alignItems: "center", flexDirection: "row", flexShrink: 1, gap: tokens.spacing.sm, minWidth: 0 },
  sectionIcon: { alignItems: "center", justifyContent: "center" },
  sectionTitle: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold },
  sectionDetail: { color: tokens.color.textSoft, fontSize: tokens.type.caption },
});
