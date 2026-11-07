import type { PropsWithChildren, ReactNode } from "react";
import type { Href } from "expo-router";
import type { LucideIcon } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { AssistantGradientIcon } from "@/components/ui/assistant-gradient-icon";
import { EntityIcon, type EntityKind } from "@/components/ui/product";
import { tokens } from "@/design/tokens";

export type NavigationSidebarItemData = { href: Href; icon: LucideIcon; iconTreatment?: "assistant" | "plain"; label: string };
export type EntitySidebarItemData = { entity: EntityKind; href: Href; label: string };

type SharedProps = { active: boolean; label: string; onPress(): void };

function SidebarItemFrame({ accessory, active, children, count, label, onPress }: PropsWithChildren<SharedProps & { accessory?: ReactNode; count?: number | null }>) {
  return <Pressable accessibilityRole="button" accessibilityState={{ selected: active }} onPress={onPress} style={({ pressed }) => [styles.item, active && styles.itemActive, pressed && styles.pressed]}>{children}<Text style={[styles.label, active && styles.labelActive]}>{label}</Text>{accessory}{count !== undefined ? <View accessibilityLabel={count == null ? "Cantidad no disponible" : `${count} elementos`} accessible style={styles.countChip}><Text style={styles.countChipText}>{count ?? "—"}</Text></View> : null}</Pressable>;
}
export function EntitySidebarItem({ accessory, active, count, entity, label, onPress }: SharedProps & { accessory?: ReactNode; count?: number | null; entity: EntityKind }) {
  return <SidebarItemFrame accessory={accessory} active={active} count={count} label={label} onPress={onPress}><EntityIcon entity={entity} size="regular" /></SidebarItemFrame>;
}
export function NavigationSidebarItem({ accessory, active, icon: Icon, iconTreatment = "plain", label, onPress }: SharedProps & { accessory?: ReactNode; icon: LucideIcon; iconTreatment?: "assistant" | "plain" }) {
  const assistant = iconTreatment === "assistant";
  return <SidebarItemFrame accessory={accessory} active={active} label={label} onPress={onPress}>{assistant ? <AssistantGradientIcon /> : <Icon color={tokens.color.textMain} size={20} strokeWidth={2} />}</SidebarItemFrame>;
}
export function SidebarProBadge() {
  return <View accessibilityLabel="Requiere plan Pro" accessible style={styles.proBadge}>
    <Svg aria-hidden pointerEvents="none" style={StyleSheet.absoluteFill}>
      <Defs>
        <LinearGradient id="sidebar-pro-badge-macros" x1="0" x2="1" y1="0" y2="0">
          <Stop offset="0" stopColor={tokens.color.protein} />
          <Stop offset="0.55" stopColor={tokens.color.carbs} />
          <Stop offset="1" stopColor={tokens.color.fat} />
        </LinearGradient>
      </Defs>
      <Rect fill="url(#sidebar-pro-badge-macros)" height="100%" width="100%" />
    </Svg>
    <Text style={styles.proBadgeText}>Pro</Text>
  </View>;
}
const styles = StyleSheet.create({
  countChip: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, justifyContent: "center", minWidth: 30, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  countChipText: { color: tokens.color.textMain, fontSize: tokens.type.label - 1, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.semibold },
  item: { alignItems: "center", borderRadius: tokens.radius.md, flexDirection: "row", gap: tokens.spacing.md, minHeight: 48, paddingHorizontal: tokens.spacing.md },
  itemActive: { backgroundColor: tokens.color.surfaceMuted },
  label: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, fontWeight: "600" },
  labelActive: { color: tokens.color.textMain, fontWeight: "800" },
  pressed: { opacity: 0.65 },
  proBadge: { alignItems: "center", borderRadius: tokens.radius.pill, justifyContent: "center", minWidth: 42, overflow: "hidden", paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  proBadgeText: { color: tokens.color.surfaceApp, fontSize: tokens.type.label - 1, fontWeight: tokens.weight.bold },
});
