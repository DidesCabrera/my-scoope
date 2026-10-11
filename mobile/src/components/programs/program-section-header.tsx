import type { LucideIcon } from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export function ProgramSectionHeader({ icon: Icon, subtitle, title }: { icon: LucideIcon; subtitle: string; title: string }) {
  return (
    <View style={styles.header}>
      <View style={styles.heading}>
        <Icon color={tokens.color.textMain} size={19} strokeWidth={2.2} />
        <Text accessibilityRole="header" style={styles.title}>{title}</Text>
      </View>
      <Text style={styles.subtitle}>{subtitle}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { gap: tokens.spacing.sm, marginBottom: tokens.spacing.sm, marginTop: tokens.spacing.xxl },
  heading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  subtitle: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  title: { color: tokens.color.textMain, flexShrink: 1, fontSize: 20, fontWeight: tokens.weight.extraBold },
});
