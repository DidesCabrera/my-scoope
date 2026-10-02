import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { ChevronRight, Mail, MailOpen, Send, Trash2 } from "lucide-react-native";
import { useCallback, useState } from "react";
import { RefreshControl, StyleSheet } from "react-native";

import { userFacingError } from "@/api/errors";
import type { SharingInboxData, SharingInboxItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import {
  CollectionEmptyState,
  DistributedTabBar,
  EntityCard,
  EntityCardAction,
  InlineNotice,
  LoadingState,
  Screen,
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

type SharingScope = "received" | "sent";

export default function InboxScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [activeScope, setActiveScope] = useState<SharingScope>("received");
  const [data, setData] = useState<Record<SharingScope, SharingInboxData> | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setHeaderPresentation = useHeaderPresentation();
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ identityVisible: compactHeaderVisible, mode: "default", title: "Compartidos" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, setHeaderPresentation]));

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    setError(null);
    try {
      const [received, sent] = await Promise.all([
        apiRequest<SharingInboxData>("/api/v1/shares/inbox"),
        apiRequest<SharingInboxData>("/api/v1/shares/inbox?scope=sent"),
      ]);
      setData({ received, sent });
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
    if (activeScope === "received") void update(item, { is_read: true });
    router.push(`/share/${item.resource_id}` as Href);
  };

  const visibleData = data?.[activeScope];

  return (
    <Screen
      headerMode="preserve"
      onHeaderVisibilityChange={setCompactHeaderVisible}
      refreshControl={<RefreshControl onRefresh={() => void load(true)} refreshing={refreshing} tintColor={tokens.color.interactivePrimary} />}
      scrollHeader={<SectionPageHeader section="inbox" title="Compartidos" />}
      stickyHeader={<DistributedTabBar<SharingScope>
        accessibilityLabel="Tipo de contenido compartido"
        activeTab={activeScope}
        onChange={setActiveScope}
        tabs={[
          {
            count: data?.received.count ?? 0,
            icon: (selected) => <MailOpen color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />,
            key: "received",
            label: "Recibidos",
          },
          {
            count: data?.sent.count ?? 0,
            icon: (selected) => <Send color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />,
            key: "sent",
            label: "Enviados",
          },
        ]}
      />}
      stickyHeaderStyle={styles.stickyHeader}>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {!data && !error ? <LoadingState label="Cargando compartidos…" /> : null}
      {visibleData?.items.map((item) => (
        <EntityCard
          accessory={activeScope === "sent"
            ? <Send color={tokens.color.textMuted} size={20} />
            : item.is_read
            ? <MailOpen color={tokens.color.textMuted} size={20} />
            : <Mail color={tokens.color[entityBySubject[item.subject_type]]} size={20} />}
          actions={<>
            {activeScope === "received" ? <EntityCardAction label="Eliminar de Compartidos" onPress={() => void update(item, { dismissed: true })}>
              <Trash2 color={tokens.color.textMuted} size={19} />
            </EntityCardAction> : null}
            <EntityCardAction label={`Ver detalle de ${item.title}`} onPress={() => open(item)} role="link">
              <ChevronRight color={tokens.color.textMuted} size={21} strokeWidth={2.2} />
            </EntityCardAction>
          </>}
          entity={entityBySubject[item.subject_type]}
          eyebrow={activeScope === "sent" ? "Enviado" : item.is_read ? "Recibido" : "Nuevo"}
          key={item.id}
          onPress={() => open(item)}
          subtitle={`${item.sender} · ${new Date(item.created_at).toLocaleDateString()}`}
          title={item.title}
        />
      ))}
      {visibleData && visibleData.count === 0 ? (
        <CollectionEmptyState
          description={activeScope === "sent" ? "Los alimentos, comidas, planes y programas que compartas aparecerán aquí." : "Los alimentos, comidas, planes y programas que agregues desde un enlace compartido aparecerán aquí."}
          title={activeScope === "sent" ? "Aún no has compartido elementos" : "Aún no tienes compartidos recibidos"}
        />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  stickyHeader: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, paddingTop: tokens.spacing.sm },
});
