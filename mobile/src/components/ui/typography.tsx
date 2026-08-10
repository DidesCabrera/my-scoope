import type { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export function SectionHeading({ title, detail, icon }: { title: string; detail?: string; icon?: ReactNode }) {
  return (
    <View style={styles.sectionHeading}>
      <View style={styles.sectionIdentity}>
        {icon ? <View style={styles.sectionIcon}>{icon}</View> : null}
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
  sectionTitle: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.section, fontWeight: "800" },
  sectionDetail: { color: tokens.color.textSoft, fontSize: tokens.type.caption },
});
