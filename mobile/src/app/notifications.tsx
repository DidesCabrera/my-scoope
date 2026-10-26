import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import * as Linking from "expo-linking";
import { Bell, Megaphone, Send, Sparkles } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { NotificationFeed, NotificationItem } from "@/api/notification-types";
import { useSession } from "@/auth/session-context";
import { AppHeader, InlineNotice, LoadingState, Screen } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { formatCompactDate } from "@/presentation/date";

const kindLabel = { proposal: "Propuesta", share: "Compartido", invitation: "Invitación", announcement: "Actualización" } as const;
const kindIcon = { proposal: Sparkles, share: Send, invitation: Send, announcement: Megaphone } as const;

export default function NotificationsScreen() {
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const [feed, setFeed] = useState<NotificationFeed | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    setError(null);
    try {
      setFeed(await apiRequest<NotificationFeed>("/api/v1/notifications"));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setRefreshing(false);
    }
  }, [apiRequest]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));

  if (status === "anonymous") return <Redirect href={{ pathname: "/login", params: { returnTo: "/notifications" } }} />;
  if (!feed && !error) return <LoadingState label="Cargando notificaciones…" />;

  const open = async (item: NotificationItem) => {
    try {
      if (!item.is_read) {
        setFeed(await apiRequest<NotificationFeed>(`/api/v1/notifications/${item.kind}/${item.id}/read`, { method: "POST" }));
      }
      if (item.kind === "invitation") await Linking.openURL(item.web_url);
      else if (item.kind !== "announcement") router.push(item.mobile_path as Href);
    } catch (nextError) {
      setError(userFacingError(nextError));
    }
  };

  return (
    <Screen refreshControl={<RefreshControl onRefresh={() => void load(true)} refreshing={refreshing} tintColor={tokens.color.interactivePrimary} />}>
      <AppHeader eyebrow="Tu actividad" title="Notificaciones" />
      <Text style={styles.intro}>Propuestas por revisar, contenido compartido y novedades de My Scoope.</Text>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {feed?.items.length ? feed.items.map((item) => {
        const Icon = kindIcon[item.kind];
        return (
          <Pressable
            accessibilityLabel={`${kindLabel[item.kind]}: ${item.title}${item.is_read ? "" : ", sin leer"}`}
            accessibilityRole="button"
            key={`${item.kind}-${item.id}`}
            onPress={() => void open(item)}
            style={({ pressed }) => [styles.card, !item.is_read && styles.unread, pressed && styles.pressed]}>
            <View style={styles.icon}><Icon color={tokens.color.textMain} size={20} strokeWidth={2} /></View>
            <View style={styles.copy}>
              <View style={styles.meta}><Text style={styles.kind}>{kindLabel[item.kind]}</Text><Text style={styles.date}>{formatCompactDate(item.created_at)}</Text></View>
              <Text style={styles.title}>{item.title}</Text>
              <Text style={styles.body}>{item.body}</Text>
              {item.kind === "announcement" && !item.is_read ? <Text style={styles.action}>Marcar como leída</Text> : null}
            </View>
          </Pressable>
        );
      }) : <View style={styles.empty}><Bell color={tokens.color.textMuted} size={32} /><Text style={styles.title}>Todo al día</Text><Text style={styles.body}>Aquí aparecerán tus próximas notificaciones.</Text></View>}
    </Screen>
  );
}

const styles = StyleSheet.create({
  intro: { color: tokens.color.textMuted, fontSize: 14, lineHeight: 21, marginBottom: 18 },
  card: { alignItems: "flex-start", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: 16, borderWidth: 1, flexDirection: "row", gap: 12, marginBottom: 10, padding: 16 },
  unread: { borderColor: tokens.color.danger },
  pressed: { opacity: 0.7 },
  icon: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, borderRadius: 10, height: 36, justifyContent: "center", width: 36 },
  copy: { flex: 1 },
  meta: { flexDirection: "row", gap: 12, marginBottom: 6 },
  kind: { color: tokens.color.textMuted, fontSize: 11, fontWeight: "700", textTransform: "uppercase" },
  date: { color: tokens.color.textMuted, fontSize: 11 },
  title: { color: tokens.color.textMain, fontSize: 16, fontWeight: "700", marginBottom: 5 },
  body: { color: tokens.color.textMuted, fontSize: 14, lineHeight: 20 },
  action: { color: tokens.color.interactivePrimary, fontSize: 13, fontWeight: "700", marginTop: 10 },
  empty: { alignItems: "center", gap: 10, paddingVertical: 60 },
});
