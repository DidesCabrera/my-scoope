import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export function SectionTitle({ title, detail }: { title: string; detail?: string }) {
  return (
    <View style={styles.sectionTitleRow}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {detail ? <Text style={styles.sectionDetail}>{detail}</Text> : null}
    </View>
  );
}

export const textStyles = StyleSheet.create({
  body: { color: tokens.color.textMain, fontSize: tokens.type.body, lineHeight: 24 },
  muted: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  caption: { color: tokens.color.textSoft, fontSize: tokens.type.caption, lineHeight: 18 },
  strong: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: "700" },
});

const styles = StyleSheet.create({
  sectionTitleRow: { alignItems: "baseline", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  sectionTitle: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.section, fontWeight: "800" },
  sectionDetail: { color: tokens.color.textSoft, fontSize: tokens.type.caption },
});
