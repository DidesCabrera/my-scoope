import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { Heart, Inbox as InboxIcon, Trash2 } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { SharingInboxData, SharingInboxItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { Button, Card, InlineNotice, SectionPageHeader, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";

export default function InboxScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [data, setData] = useState<SharingInboxData | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    setError(null);
    try {
      setData(await apiRequest<SharingInboxData>("/api/v1/shares/inbox"));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setRefreshing(false);
    }
  }, [apiRequest]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  if (status === "anonymous") return <Redirect href={{ pathname: "/login", params: { returnTo: "/inbox" } }} />;

  const update = async (item: SharingInboxItem, payload: Record<string, boolean>) => {
    try {
      await apiRequest(`/api/v1/shares/inbox/${item.id}`, { body: JSON.stringify(payload), method: "PATCH" });
      await load();
    } catch (nextError) {
      setError(userFacingError(nextError));
    }
  };

  const save = async (item: SharingInboxItem) => {
    try {
      const result = await apiRequest<{ entity: "dailyPlan"; item_id: number }>(`/api/v1/shares/inbox/${item.id}/save`, { method: "POST" });
      router.push(`/libraries/daily-plans/${result.item_id}`);
    } catch (nextError) {
      setError(userFacingError(nextError));
    }
  };

  return (
    <ScrollView
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl onRefresh={() => void load(true)} refreshing={refreshing} tintColor={tokens.color.interactivePrimary} />}>
      <SectionPageHeader count={data?.count} countLabel="recibidos" section="inbox" title="Inbox" />
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {data?.items.map((item) => (
        <Card accent={item.is_read ? undefined : tokens.color.dailyPlan} key={item.id}>
          <View style={styles.heading}>
            <View style={styles.identity}><InboxIcon color={tokens.color.textMuted} size={18} /><Text style={styles.title}>{item.title}</Text></View>
            <Pressable accessibilityLabel={item.is_favorite ? "Quitar favorito" : "Marcar favorito"} onPress={() => void update(item, { is_favorite: !item.is_favorite })}><Heart color={item.is_favorite ? tokens.color.fat : tokens.color.textMuted} fill={item.is_favorite ? tokens.color.fat : "transparent"} size={21} /></Pressable>
          </View>
          <Text style={textStyles.muted}>{item.sender} · {new Date(item.created_at).toLocaleDateString()}</Text>
          <Button label="Ver plan" onPress={() => { void update(item, { is_read: true }); router.push(`/share/${item.resource_id}` as Href); }} variant="secondary" />
          <Button label={item.is_saved ? "Abrir copia guardada" : "Guardar en Mis Planes"} onPress={() => void save(item)} />
          <Pressable accessibilityLabel="Eliminar del Inbox" onPress={() => void update(item, { dismissed: true })} style={styles.delete}><Trash2 color={tokens.color.textSoft} size={17} /><Text style={styles.deleteText}>Eliminar del Inbox</Text></Pressable>
        </Card>
      ))}
      {data && data.count === 0 ? <Card><Text style={styles.emptyTitle}>Tu Inbox está vacío</Text><Text style={textStyles.muted}>Los planes que agregues desde un enlace compartido aparecerán aquí.</Text></Card> : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { gap: tokens.spacing.lg, padding: tokens.spacing.screen, paddingBottom: 42 },
  delete: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "center", padding: tokens.spacing.sm },
  deleteText: { color: tokens.color.textSoft, fontSize: 13, fontWeight: "700" },
  emptyTitle: { color: tokens.color.textMain, fontSize: 18, fontWeight: "800" },
  heading: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  identity: { alignItems: "center", flexDirection: "row", flex: 1, gap: tokens.spacing.sm },
  title: { color: tokens.color.textMain, flex: 1, fontSize: 18, fontWeight: "800" },
});
