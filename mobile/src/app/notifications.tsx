import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import * as Linking from "expo-linking";
import { Bell, CheckCheck, Megaphone, Send, Sparkles } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { NotificationFeed, NotificationItem } from "@/api/notification-types";
import { useSession } from "@/auth/session-context";
import { AssistantGradientIcon } from "@/components/ui/assistant-gradient-icon";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { InlineNotice, LoadingState, Screen, SectionPageHeader } from "@/components/ui";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { tokens } from "@/design/tokens";
import { formatCompactDate } from "@/presentation/date";

const kindLabel = { proposal: "Propuesta", share: "Compartido", invitation: "Invitación", announcement: "Actualización" } as const;
const kindIcon = { proposal: Sparkles, share: Send, invitation: Send, announcement: Megaphone } as const;

function sharedIconColor(item: NotificationItem): string | undefined {
  if (item.kind !== "share" && item.kind !== "invitation") return undefined;
  if (item.subject_type === "comparison") {
    const comparisonColors = { foods: tokens.color.food, meals: tokens.color.meal, dailyplans: tokens.color.dailyPlan };
    return item.comparison_kind ? comparisonColors[item.comparison_kind] : undefined;
  }
  const subjectColors = { daily_plan: tokens.color.dailyPlan, food: tokens.color.food, meal: tokens.color.meal, program: tokens.color.program };
  return item.subject_type ? subjectColors[item.subject_type] : undefined;
}

export default function NotificationsScreen() {
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [feed, setFeed] = useState<NotificationFeed | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [menuVisible, setMenuVisible] = useState(false);
  const [markingAll, setMarkingAll] = useState(false);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ action: { icon: "more", label: "Opciones de notificaciones", onPress: () => setMenuVisible(true) }, identityVisible: compactHeaderVisible, mode: "default", title: "Notificaciones" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, setHeaderPresentation]));

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

  const markAllRead = async () => {
    if (markingAll || !feed?.unread_count) return;
    setMarkingAll(true);
    setError(null);
    try {
      setFeed(await apiRequest<NotificationFeed>("/api/v1/notifications/read-all", { method: "POST" }));
      setMenuVisible(false);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setMarkingAll(false);
    }
  };

  return (
    <>
    <Screen headerMode="preserve" onHeaderVisibilityChange={setCompactHeaderVisible} refreshControl={<RefreshControl onRefresh={() => void load(true)} refreshing={refreshing} tintColor={tokens.color.interactivePrimary} />}>
      <SectionPageHeader section="notifications" title="Notificaciones" />
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {feed?.items.length ? feed.items.map((item) => {
        const Icon = kindIcon[item.kind];
        const iconColor = sharedIconColor(item);
        return (
          <Pressable
            accessibilityLabel={`${kindLabel[item.kind]}: ${item.title}${item.is_read ? "" : ", sin leer"}`}
            accessibilityRole="button"
            key={`${item.kind}-${item.id}`}
            onPress={() => void open(item)}
            style={({ pressed }) => [styles.card, pressed && styles.pressed]}>
            {item.kind === "proposal" ? <AssistantGradientIcon size={36} /> : <View style={[styles.icon, iconColor ? { backgroundColor: iconColor } : undefined]}><Icon color={iconColor ? tokens.color.entityIconForeground : tokens.color.textMain} size={20} strokeWidth={2} /></View>}
            <View style={styles.copy}>
              <View style={styles.meta}>
                <View style={styles.kindRow}><Text style={styles.kind}>{kindLabel[item.kind]}</Text>{!item.is_read ? <View accessibilityLabel="Sin leer" style={styles.unreadDot} /> : null}</View>
                <Text style={styles.date}>{formatCompactDate(item.created_at)}</Text>
              </View>
              <Text style={styles.title}>{item.title}</Text>
              <Text style={styles.body}>{item.body}</Text>
              {item.kind === "announcement" && !item.is_read ? <Text style={styles.action}>Marcar como leída</Text> : null}
            </View>
          </Pressable>
        );
      }) : <View style={styles.empty}><Bell color={tokens.color.textMuted} size={32} /><Text style={styles.title}>Todo al día</Text><Text style={styles.body}>Aquí aparecerán tus próximas notificaciones.</Text></View>}
    </Screen>
    <ActionSheetModal onRequestClose={() => setMenuVisible(false)} visible={menuVisible}>
      <SafeAreaView edges={["left", "right"]} style={styles.sheet}>
        <ActionSheetHeader icon={Bell} onClose={() => setMenuVisible(false)} title="Opciones de notificaciones" />
        <View style={styles.sheetContent}>
          <ActionSheetActions>
            <ActionSheetAction disabled={markingAll || !feed?.unread_count} icon={CheckCheck} label="Marcar todos como leídos" loading={markingAll} onPress={() => void markAllRead()} />
          </ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
    </>
  );
}

const styles = StyleSheet.create({
  card: { alignItems: "flex-start", backgroundColor: tokens.color.surfaceCard, borderRadius: 16, flexDirection: "row", gap: 12, marginBottom: 10, marginHorizontal: -18, padding: 16 },
  pressed: { opacity: 0.7 },
  icon: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, borderRadius: 10, height: 36, justifyContent: "center", width: 36 },
  copy: { flex: 1 },
  meta: { flexDirection: "row", gap: 12, marginBottom: 6 },
  kind: { color: tokens.color.textMuted, fontSize: 11, fontWeight: "700", textTransform: "uppercase" },
  kindRow: { alignItems: "center", flexDirection: "row", gap: 6 },
  unreadDot: { backgroundColor: tokens.color.danger, borderRadius: 4, height: 6, width: 6 },
  date: { color: tokens.color.textMuted, fontSize: 11 },
  title: { color: tokens.color.textMain, fontSize: 16, fontWeight: "700", marginBottom: 5 },
  body: { color: tokens.color.textMuted, fontSize: 14, lineHeight: 20 },
  action: { color: tokens.color.interactivePrimary, fontSize: 13, fontWeight: "700", marginTop: 10 },
  empty: { alignItems: "center", gap: 10, paddingVertical: 60 },
  sheet: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  sheetContent: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
});
