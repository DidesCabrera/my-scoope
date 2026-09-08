import { type Href, useRouter } from "expo-router";
import { Bookmark, CalendarDays, Carrot, ClipboardList, Plus, Utensils } from "lucide-react-native";
import type { LucideIcon } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { LibraryEntity } from "@/api/types";
import { SectionDivider } from "@/components/ui";
import { tokens } from "@/design/tokens";

export type HomeLibraryCounts = Record<LibraryEntity, number>;

type LibraryEntry = {
  entity: LibraryEntity;
  href: Href;
  icon: LucideIcon;
  title: string;
};

const entries: LibraryEntry[] = [
  { entity: "program", href: "/libraries/programs", icon: CalendarDays, title: "Mis Programas\nSemanales" },
  { entity: "dailyPlan", href: "/libraries/daily-plans", icon: ClipboardList, title: "Mis Planes\nDiarios" },
  { entity: "meal", href: "/libraries/meals", icon: Utensils, title: "Mis Comidas" },
  { entity: "food", href: "/libraries/foods", icon: Carrot, title: "Mis Alimentos" },
];

export function HomeLibraryGrid({ counts }: { counts: HomeLibraryCounts }) {
  const router = useRouter();
  return (
    <View accessibilityLabel="Mis librerías" style={styles.section}>
      <SectionDivider spacing="compact" />
      <View style={styles.heading}>
        <Bookmark color={tokens.color.textMain} size={21} strokeWidth={2.2} />
        <Text style={styles.headingText}>Mis librerías</Text>
      </View>
      <View style={styles.grid}>
        {entries.map((entry) => {
          const Icon = entry.icon;
          const accessibleTitle = entry.title.replace("\n", " ");
          return (
            <View key={entry.entity} style={[styles.card, { borderTopColor: tokens.color[entry.entity] }]}>
              <Pressable accessibilityLabel={`Abrir ${accessibleTitle}`} accessibilityRole="link" onPress={() => router.push(entry.href)} style={({ pressed }) => [styles.cardMain, pressed && styles.pressed]}>
                <View style={[styles.icon, { backgroundColor: tokens.color[entry.entity] }]}><Icon color={tokens.color.entityIconForeground} size={20} strokeWidth={2.2} /></View>
                <Text numberOfLines={2} style={styles.title}>{entry.title}</Text>
              </Pressable>
              <View style={styles.footer}>
                <Pressable accessibilityLabel={`Crear en ${accessibleTitle}`} accessibilityRole="button" onPress={() => router.push({ pathname: "/libraries/create", params: { entity: entry.entity } })} style={({ pressed }) => [styles.create, pressed && styles.pressed]}>
                  <Plus color={tokens.color.surfaceApp} size={20} strokeWidth={2.2} />
                </Pressable>
                <View style={styles.count}><Bookmark color={tokens.color.textMain} size={18} /><Text style={styles.countText}>{counts[entry.entity]}</Text></View>
              </View>
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderTopWidth: 3, borderWidth: 1, flexBasis: "47%", flexGrow: 1, minHeight: 172, overflow: "hidden", padding: tokens.card.outerPadding },
  cardMain: { flex: 1 },
  count: { alignItems: "center", flexDirection: "row", gap: 3 },
  countText: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.extraBold },
  create: { alignItems: "center", backgroundColor: tokens.color.textMain, borderRadius: tokens.radius.sm, height: 30, justifyContent: "center", width: 30 },
  footer: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginTop: tokens.spacing.sm },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  heading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  headingText: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.extraBold },
  icon: { alignItems: "center", borderRadius: tokens.radius.sm, height: 34, justifyContent: "center", marginBottom: tokens.spacing.sm, width: 34 },
  pressed: { opacity: 0.65 },
  section: { gap: tokens.spacing.md, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
  title: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.extraBold, lineHeight: 19, minHeight: 38 },
});
