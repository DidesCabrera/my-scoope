import type { PropsWithChildren } from "react";
import type { Href } from "expo-router";
import type { LucideIcon } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import type { LibraryEntity } from "@/api/types";
import { EntityIcon } from "@/components/ui/product";
import { tokens } from "@/design/tokens";

export type NavigationSidebarItemData = { href: Href; icon: LucideIcon; iconTreatment?: "assistant" | "plain"; label: string };
export type EntitySidebarItemData = { entity: LibraryEntity; href: Href; label: string };

type SharedProps = { active: boolean; label: string; onPress(): void };

function SidebarItemFrame({ active, children, label, onPress }: PropsWithChildren<SharedProps>) {
  return <Pressable accessibilityRole="button" accessibilityState={{ selected: active }} onPress={onPress} style={({ pressed }) => [styles.item, active && styles.itemActive, pressed && styles.pressed]}>{children}<Text style={[styles.label, active && styles.labelActive]}>{label}</Text></Pressable>;
}
export function EntitySidebarItem({ active, entity, label, onPress }: SharedProps & { entity: LibraryEntity }) {
  return <SidebarItemFrame active={active} label={label} onPress={onPress}><EntityIcon entity={entity} size="regular" /></SidebarItemFrame>;
}
export function NavigationSidebarItem({ active, icon: Icon, iconTreatment = "plain", label, onPress }: SharedProps & { icon: LucideIcon; iconTreatment?: "assistant" | "plain" }) {
  const assistant = iconTreatment === "assistant";
  return <SidebarItemFrame active={active} label={label} onPress={onPress}><View style={[styles.navigationIcon, assistant && styles.navigationIconAssistant]}>{assistant ? <Svg aria-hidden height={22} pointerEvents="none" style={StyleSheet.absoluteFill} width={22}><Defs><LinearGradient id="assistant-navigation-macros" x1="0" x2="1" y1="0" y2="1"><Stop offset="0" stopColor={tokens.color.protein} /><Stop offset="0.5" stopColor={tokens.color.carbs} /><Stop offset="1" stopColor={tokens.color.fat} /></LinearGradient></Defs><Rect fill="url(#assistant-navigation-macros)" height={22} rx={5} ry={5} width={22} /></Svg> : null}<Icon color={assistant ? tokens.color.surfaceApp : active ? tokens.color.textMain : tokens.color.textMuted} size={assistant ? 13 : 20} strokeWidth={assistant ? 2.4 : 2} /></View></SidebarItemFrame>;
}
const styles = StyleSheet.create({
  item: { alignItems: "center", borderRadius: tokens.radius.md, flexDirection: "row", gap: tokens.spacing.md, minHeight: 48, paddingHorizontal: tokens.spacing.md },
  itemActive: { backgroundColor: tokens.color.surfaceMuted },
  label: { color: tokens.color.textMuted, flex: 1, fontSize: tokens.type.body, fontWeight: "600" },
  labelActive: { color: tokens.color.textMain, fontWeight: "800" },
  navigationIcon: { alignItems: "center", backgroundColor: "transparent", height: 22, justifyContent: "center", width: 22 },
  navigationIconAssistant: { borderRadius: 5, overflow: "hidden" },
  pressed: { opacity: 0.65 },
});
