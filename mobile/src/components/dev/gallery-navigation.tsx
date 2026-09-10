import { ChevronDown } from "lucide-react-native";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export type GalleryTab = "components" | "calendars" | "program" | "details" | "proposals" | "comparisons" | "states" | "tokens";

const tabs: { key: GalleryTab; label: string }[] = [
  { key: "components", label: "Componentes" }, { key: "calendars", label: "Calendarios" },
  { key: "program", label: "Programa" }, { key: "details", label: "Detalle" },
  { key: "proposals", label: "Propuestas" }, { key: "comparisons", label: "Comparaciones" },
  { key: "states", label: "Estados" }, { key: "tokens", label: "Tokens" },
];

export function GalleryNavigation({ activeTab, onChange, wide }: { activeTab: GalleryTab; onChange: (tab: GalleryTab) => void; wide: boolean }) {
  const [open, setOpen] = useState(false);
  const activeLabel = tabs.find((item) => item.key === activeTab)?.label ?? "Sección";
  const options = tabs.map((item) => {
    const active = activeTab === item.key;
    return (
      <Pressable accessibilityRole={wide ? "tab" : "button"} accessibilityState={{ selected: active }} key={item.key} onPress={() => { onChange(item.key); setOpen(false); }} style={({ pressed }) => [styles.item, active && styles.itemActive, pressed && styles.pressed]}>
        <Text style={[styles.itemText, active && styles.itemTextActive]}>{item.label}</Text>
      </Pressable>
    );
  });

  if (wide) return <View accessibilityLabel="Secciones de la galería" accessibilityRole="tablist" style={[styles.container, styles.wide]}><Text style={styles.label}>Secciones</Text>{options}</View>;
  return (
    <View style={styles.container}>
      <Text style={styles.label}>Sección de la galería</Text>
      <Pressable accessibilityLabel={`Sección actual: ${activeLabel}`} accessibilityRole="button" accessibilityState={{ expanded: open }} onPress={() => setOpen((current) => !current)} style={({ pressed }) => [styles.trigger, pressed && styles.pressed]}>
        <Text style={styles.value}>{activeLabel}</Text><ChevronDown color={tokens.color.textMuted} size={18} style={open && styles.chevronOpen} />
      </Pressable>
      {open ? <View accessibilityLabel="Secciones disponibles" style={styles.menu}>{options}</View> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignSelf: "stretch", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, gap: tokens.spacing.xs, padding: tokens.spacing.sm },
  wide: { flexBasis: 156, flexGrow: 0, flexShrink: 0 }, label: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs, textTransform: "uppercase" },
  trigger: { alignItems: "center", backgroundColor: tokens.color.surfaceElevated, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, flexDirection: "row", justifyContent: "space-between", minHeight: 44, paddingHorizontal: tokens.spacing.md },
  value: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold }, chevronOpen: { transform: [{ rotate: "180deg" }] }, menu: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, gap: tokens.spacing.xs, marginTop: tokens.spacing.xs, paddingTop: tokens.spacing.sm },
  item: { borderRadius: tokens.radius.md, minHeight: 40, paddingHorizontal: tokens.spacing.sm, paddingVertical: 10 }, itemActive: { backgroundColor: tokens.color.surfaceElevated, borderLeftColor: tokens.color.interactivePrimary, borderLeftWidth: 3 }, pressed: { opacity: 0.7 }, itemText: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium }, itemTextActive: { color: tokens.color.textMain, fontWeight: tokens.weight.bold },
});
