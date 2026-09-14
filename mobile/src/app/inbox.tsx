import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { ChevronRight, Mail, MailOpen, Trash2 } from "lucide-react-native";
import { useCallback, useState } from "react";
import { RefreshControl, ScrollView, StyleSheet } from "react-native";

import { userFacingError } from "@/api/errors";
import type { SharingInboxData, SharingInboxItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import {
  CollectionEmptyState,
  EntityCard,
  EntityCardAction,
  InlineNotice,
  LoadingState,
  SectionPageHeader,
  type EntityKind,
} from "@/components/ui";
import { tokens } from "@/design/tokens";

const entityBySubject: Record<SharingInboxItem["subject_type"], EntityKind> = {
  daily_plan: "dailyPlan",
  food: "food",
  meal: "meal",
  program: "program",
};

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

  const open = (item: SharingInboxItem) => {
    void update(item, { is_read: true });
    router.push(`/share/${item.resource_id}` as Href);
  };

  return (
    <ScrollView
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl onRefresh={() => void load(true)} refreshing={refreshing} tintColor={tokens.color.interactivePrimary} />}>
      <SectionPageHeader count={data?.count} countLabel="recibidos" section="inbox" title="Inbox" />
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {!data && !error ? <LoadingState label="Cargando Inbox…" /> : null}
      {data?.items.map((item) => (
        <EntityCard
          accessory={item.is_read
            ? <MailOpen color={tokens.color.textMuted} size={20} />
            : <Mail color={tokens.color[entityBySubject[item.subject_type]]} size={20} />}
          actions={<>
            <EntityCardAction label="Eliminar del Inbox" onPress={() => void update(item, { dismissed: true })}>
              <Trash2 color={tokens.color.textMuted} size={19} />
            </EntityCardAction>
            <EntityCardAction label={`Ver detalle de ${item.title}`} onPress={() => open(item)} role="link">
              <ChevronRight color={tokens.color.textMuted} size={21} strokeWidth={2.2} />
            </EntityCardAction>
          </>}
          entity={entityBySubject[item.subject_type]}
          eyebrow={item.is_read ? "Recibido" : "Nuevo"}
          key={item.id}
          onPress={() => open(item)}
          subtitle={`${item.sender} · ${new Date(item.created_at).toLocaleDateString()}`}
          title={item.title}
        />
      ))}
      {data && data.count === 0 ? (
        <CollectionEmptyState
          description="Los alimentos, comidas, planes y programas que agregues desde un enlace compartido aparecerán aquí."
          title="Tu Inbox está vacío"
        />
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { gap: tokens.spacing.lg, padding: tokens.spacing.screen, paddingBottom: 42 },
});
