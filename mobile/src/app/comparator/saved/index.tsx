import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { SavedComparisonListData, SavedComparisonSummary } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { AppHeader, Card, LoadingState, Pill, Screen, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

function SavedCard({ item, onPress }: { item: SavedComparisonSummary; onPress(): void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => pressed && styles.pressed}>
      <Card>
        <View style={styles.row}>
          <View style={styles.copy}>
            <Text style={styles.title}>{item.name}</Text>
            <Text style={textStyles.caption}>{new Intl.DateTimeFormat("es-CL", { dateStyle: "medium" }).format(new Date(item.updated_at))}</Text>
          </View>
          <Pill label={item.kind_label} />
        </View>
        <Text style={textStyles.muted}>{item.item_count} elementos · Ver fotografía guardada ›</Text>
      </Card>
    </Pressable>
  );
}

export default function SavedComparisonsScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [page, setPage] = useState<SavedComparisonListData | null>(null);
  const [filter, setFilter] = useState<"all" | "foods" | "meals" | "dailyplans">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const kind = filter === "all" ? "" : `&kind=${filter}`;
      setPage(await apiRequest<SavedComparisonListData>(`/api/v1/comparisons/saved?limit=50${kind}`));
    }
    catch (nextError) { setError(userFacingError(nextError)); }
    finally { setLoading(false); }
  }, [apiRequest, filter]);
  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !page) return <LoadingState label="Buscando tus comparaciones…" />;
  return (
    <Screen>
      <AppHeader eyebrow="Fotografías nutricionales" title="Comparaciones guardadas" />
      <View style={styles.filters}>
        {([
          ["all", "Todas"],
          ["foods", "Alimentos"],
          ["meals", "Comidas"],
          ["dailyplans", "Planes"],
        ] as const).map(([value, label]) => (
          <Pressable accessibilityRole="radio" accessibilityState={{ selected: filter === value }} key={value} onPress={() => setFilter(value)} style={[styles.filter, filter === value && styles.filterSelected]}>
            <Text style={[styles.filterText, filter === value && styles.filterTextSelected]}>{label}</Text>
          </Pressable>
        ))}
      </View>
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {page?.items.length ? page.items.map((item) => <SavedCard item={item} key={item.id} onPress={() => router.push(`/comparator/saved/${item.id}` as Href)} />) : (
        <EmptyState actionLabel="Crear comparación" message="Guarda un resultado para revisarlo más adelante sin que sus cifras históricas cambien." onAction={() => router.push("/comparator" as Href)} title="Aún no hay comparaciones" />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  copy: { flex: 1, gap: tokens.spacing.xs },
  filter: { borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.sm },
  filterSelected: { backgroundColor: tokens.color.interactivePrimary, borderColor: tokens.color.interactivePrimary },
  filterText: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: "800" },
  filterTextSelected: { color: "#FFFFFF" },
  filters: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  pressed: { opacity: 0.7 },
  row: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
});
