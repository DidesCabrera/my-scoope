import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export function ProgramSectionHeader({ action, bottomSpacing, detail, icon: Icon, subtitle, subtitleTopSpacing, title, topSpacing, variant }: { action?: ReactNode; bottomSpacing?: number; detail?: ReactNode; icon: LucideIcon; subtitle?: string; subtitleTopSpacing?: number; title: string; topSpacing?: number; variant?: "home" }) {
  return (
    <View style={[styles.header, topSpacing !== undefined && { marginTop: topSpacing }, bottomSpacing !== undefined && { marginBottom: bottomSpacing }]}>
      <View style={styles.headerRow}>
        <View style={styles.heading}>
          <Icon color={tokens.color.textMain} size={variant === "home" ? 25 : 19} strokeWidth={2.2} />
          <Text accessibilityRole="header" style={[styles.title, variant === "home" && styles.homeTitle]}>{title}</Text>
        </View>
        {action}
      </View>
      {subtitle ? <Text style={[styles.subtitle, subtitleTopSpacing !== undefined && { marginTop: subtitleTopSpacing }]}>{subtitle}</Text> : null}
      {detail}
    </View>
  );
}

const styles = StyleSheet.create({
  header: { gap: tokens.spacing.sm, marginBottom: tokens.spacing.sm, marginTop: tokens.spacing.xxl },
  headerRow: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  heading: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  subtitle: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  title: { color: tokens.color.textMain, flexShrink: 1, fontSize: 20, fontWeight: tokens.weight.extraBold },
  homeTitle: { fontSize: 22, letterSpacing: -0.3 },
});
