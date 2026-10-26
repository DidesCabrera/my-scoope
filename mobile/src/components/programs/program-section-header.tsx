import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export function ProgramSectionHeader({ action, detail, icon: Icon, subtitle, title, topSpacing }: { action?: ReactNode; detail?: ReactNode; icon: LucideIcon; subtitle?: string; title: string; topSpacing?: number }) {
  return (
    <View style={[styles.header, topSpacing !== undefined && { marginTop: topSpacing }]}>
      <View style={styles.headerRow}>
        <View style={styles.heading}>
          <Icon color={tokens.color.textMain} size={19} strokeWidth={2.2} />
          <Text accessibilityRole="header" style={styles.title}>{title}</Text>
        </View>
        {action}
      </View>
      {detail ?? (subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null)}
    </View>
  );
}

const styles = StyleSheet.create({
  header: { gap: tokens.spacing.sm, marginBottom: tokens.spacing.sm, marginTop: tokens.spacing.xxl },
  headerRow: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  heading: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  subtitle: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  title: { color: tokens.color.textMain, flexShrink: 1, fontSize: 20, fontWeight: tokens.weight.extraBold },
});
