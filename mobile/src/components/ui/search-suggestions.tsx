import { Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export function SearchSuggestions<T extends { id: number; name: string }>({ bleed = false, items, onSelect }: {
  bleed?: boolean;
  items: T[];
  onSelect(item: T): void;
}) {
  if (!items.length) return null;

  return (
    <View accessibilityLabel="Sugerencias de búsqueda" style={[styles.panel, bleed && styles.bleed]}>
      {items.map((item) => (
        <Pressable accessibilityLabel={`Seleccionar ${item.name}`} accessibilityRole="button" key={item.id} onPress={() => onSelect(item)} style={styles.option}>
          <Text numberOfLines={1} style={styles.name}>{item.name}</Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  bleed: { left: tokens.layout.reducedInset - tokens.card.outerPadding, right: tokens.layout.reducedInset - tokens.card.outerPadding },
  panel: {
    backgroundColor: tokens.color.surfaceCard,
    borderColor: tokens.color.borderSoft,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    elevation: 8,
    left: 0,
    position: "absolute",
    right: 0,
    top: 44,
    zIndex: 10,
  },
  option: { borderBottomColor: tokens.color.borderSoft, borderBottomWidth: StyleSheet.hairlineWidth, minHeight: 42, justifyContent: "center", paddingHorizontal: tokens.spacing.md },
  name: { color: tokens.color.textMain, fontSize: tokens.type.body },
});
