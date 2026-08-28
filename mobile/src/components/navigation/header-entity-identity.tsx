import { StyleSheet, Text, View } from "react-native";

import type { LibraryEntity } from "@/api/types";
import { EntityIcon } from "@/components/ui/product";
import { tokens } from "@/design/tokens";

export function HeaderEntityIdentity({ entity, title }: { entity: LibraryEntity; title: string }) {
  return <View accessibilityLabel={title} accessible style={styles.identity}><EntityIcon entity={entity} size="header" /><Text numberOfLines={1} style={styles.title}>{title}</Text></View>;
}
const styles = StyleSheet.create({
  identity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  title: { color: tokens.color.textMain, flexShrink: 1, fontSize: 16, fontWeight: "600", lineHeight: 22 },
});
