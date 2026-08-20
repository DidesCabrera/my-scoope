import type { PropsWithChildren } from "react";
import type { Href } from "expo-router";
import type { LucideIcon } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { LibraryEntity } from "@/api/types";
import { EntityIcon } from "@/components/ui";
import { tokens } from "@/design/tokens";

export type NavigationSidebarItemData = { href: Href; icon: LucideIcon; label: string };
export type EntitySidebarItemData = { entity: LibraryEntity; href: Href; label: string };

type SharedProps = { active: boolean; label: string; onPress(): void };

function SidebarItemFrame({ active, children, label, onPress }: PropsWithChildren<SharedProps>) {
  return <Pressable accessibilityRole="button" accessibilityState={{ selected: active }} onPress={onPress} style={({ pressed }) => [styles.item, active && styles.itemActive, pressed && styles.pressed]}>{children}<Text style={[styles.label, active && styles.labelActive]}>{label}</Text></Pressable>;
}
export function EntitySidebarItem({ active, entity, label, onPress }: SharedProps & { entity: LibraryEntity }) {
  return <SidebarItemFrame active={active} label={label} onPress={onPress}><EntityIcon entity={entity} size="regular" /></SidebarItemFrame>;
}
export function NavigationSidebarItem({ active, icon: Icon, label, onPress }: SharedProps & { icon: LucideIcon }) {
  return <SidebarItemFrame active={active} label={label} onPress={onPress}><View style={styles.navigationIcon}><Icon color={active ? tokens.color.textMain : tokens.color.textMuted} size={20} strokeWidth={2} /></View></SidebarItemFrame>;
}
const styles = StyleSheet.create({
  item: { alignItems: "center", borderRadius: tokens.radius.md, flexDirection: "row", gap: tokens.spacing.md, minHeight: 50, paddingHorizontal: tokens.spacing.md },
  itemActive: { backgroundColor: tokens.color.surfaceMuted },
  label: { color: tokens.color.textMuted, flex: 1, fontSize: 15, fontWeight: "600" },
  labelActive: { color: tokens.color.textMain, fontWeight: "800" },
  navigationIcon: { alignItems: "center", backgroundColor: "transparent", height: 22, justifyContent: "center", width: 22 },
  pressed: { opacity: 0.65 },
});
