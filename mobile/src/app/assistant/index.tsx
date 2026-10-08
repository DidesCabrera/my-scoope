import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronRight, MessageCircle } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { AIChatListData, AIChatSummary, LibraryListActionResult, ProposalListData, ProposalSummary } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AssistantListActions } from "@/components/assistant/assistant-list-actions";
import { AssistantListEditor, type AssistantListItem } from "@/components/assistant/assistant-list-editor";
import { AssistantSectionTabs, type AssistantSection } from "@/components/assistant/assistant-section-tabs";
import { AssistantCreditBalance } from "@/components/assistant/assistant-credit-balance";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProposalListCard } from "@/components/proposals";
import { EntityCardAction, EntityCardActions, SectionPageHeader } from "@/components/ui";
import { EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { Button, Card, InlineNotice, LoadingState, Screen, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";
import { formatCompactDate } from "@/presentation/date";

function ChatCard({ chat, onPress }: { chat: AIChatSummary; onPress(): void }) {
  const detailLabel = `Abrir conversación ${chat.title}`;
  return (
    <Card accent={tokens.color.carbs} style={styles.chatCard}>
      <Pressable
        accessibilityLabel={detailLabel}
        accessibilityRole="link"
        onPress={onPress}
        style={({ pressed }) => [styles.chatLink, pressed && styles.pressed]}>
        <View style={styles.row}>
          <View style={styles.copy}>
            <View style={styles.eyebrowRow}>
              <MessageCircle color={tokens.color.textMain} size={16} strokeWidth={2} />
              <Text style={styles.eyebrow}>Chat</Text>
            </View>
            <Text style={styles.title}>{chat.title}</Text>
            <Text style={textStyles.caption}>{formatCompactDate(chat.updated_at) ?? "Fecha no disponible"}</Text>
          </View>
        </View>
        <Text numberOfLines={3} style={textStyles.muted}>{chat.last_message_preview}</Text>
      </Pressable>
      <EntityCardActions>
        <EntityCardAction label={detailLabel} onPress={onPress} role="link">
          <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
        </EntityCardAction>
      </EntityCardActions>
    </Card>
  );
}

export default function AssistantHistoryScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ section?: string }>();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [activeSection, setActiveSection] = useState<AssistantSection>(params.section === "proposals" ? "proposals" : "chats");
  const [chatPage, setChatPage] = useState<AIChatListData | null>(null);
  const [proposalPage, setProposalPage] = useState<ProposalListData | null>(null);
  const [actionsVisible, setActionsVisible] = useState(false);
  const [mode, setMode] = useState<"list" | "edit">("list");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [chatsLoading, setChatsLoading] = useState(true);
  const [proposalsLoading, setProposalsLoading] = useState(true);
  const [chatError, setChatError] = useState<string | null>(null);
  const [proposalError, setProposalError] = useState<string | null>(null);

  const loadChats = useCallback(async () => {
    setChatsLoading(true);
    setChatError(null);
    try {
      setChatPage(await apiRequest<AIChatListData>("/api/v1/ai/chats?limit=50"));
    } catch (nextError) {
      setChatError(userFacingError(nextError));
    } finally {
      setChatsLoading(false);
    }
  }, [apiRequest]);

  const loadProposals = useCallback(async () => {
    setProposalsLoading(true);
    setProposalError(null);
    try {
      setProposalPage(await apiRequest<ProposalListData>("/api/v1/proposals"));
    } catch (nextError) {
      setProposalError(userFacingError(nextError));
    } finally {
      setProposalsLoading(false);
    }
  }, [apiRequest]);

  const loadAll = useCallback(async (section: AssistantSection) => {
    const items: (AIChatSummary | ProposalSummary)[] = [];
    let total = 0;
    do {
      const endpoint = section === "chats" ? "/api/v1/ai/chats" : "/api/v1/proposals";
      const next = await apiRequest<AIChatListData | ProposalListData>(`${endpoint}?limit=50&offset=${items.length}`);
      items.push(...next.items);
      total = next.total;
      if (section === "chats") setChatPage({ ...(next as AIChatListData), items: items as AIChatSummary[], limit: items.length, offset: 0 });
      else setProposalPage({ ...(next as ProposalListData), items: items as ProposalSummary[], limit: items.length, offset: 0 });
    } while (items.length < total);
  }, [apiRequest]);

  const beginEdit = useCallback(async () => {
    setActionsVisible(false);
    setMode("edit");
    setSelectedIds(new Set());
    const setLoading = activeSection === "chats" ? setChatsLoading : setProposalsLoading;
    const setError = activeSection === "chats" ? setChatError : setProposalError;
    setLoading(true);
    setError(null);
    try {
      await loadAll(activeSection);
    } catch (nextError) {
      setMode("list");
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [activeSection, loadAll]);

  const finishEdit = useCallback(() => {
    if (submitting) return;
    setMode("list");
    setSelectedIds(new Set());
  }, [submitting]);

  const cancelSelection = useCallback(() => setSelectedIds(new Set()), []);

  const deleteItems = useCallback(async (itemIds: number[]) => {
    if (!itemIds.length) return;
    setSubmitting(true);
    const setError = activeSection === "chats" ? setChatError : setProposalError;
    setError(null);
    try {
      const endpoint = activeSection === "chats" ? "/api/v1/ai/chats/bulk-delete" : "/api/v1/proposals/bulk-delete";
      const result = await apiRequest<LibraryListActionResult>(endpoint, {
        body: JSON.stringify({ item_ids: itemIds }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      const affectedIds = new Set(result.affected_ids);
      if (activeSection === "chats") {
        setChatPage((current) => current ? { ...current, items: current.items.filter(({ id }) => !affectedIds.has(id)), total: Math.max(0, current.total - affectedIds.size) } : current);
      } else {
        setProposalPage((current) => current ? {
          ...current,
          items: current.items.filter(({ id }) => !affectedIds.has(id)),
          pending_count: current.items.filter(({ id, status: proposalStatus }) => affectedIds.has(id) && proposalStatus === "pending_review").reduce((count) => Math.max(0, count - 1), current.pending_count),
          total: Math.max(0, current.total - affectedIds.size),
        } : current);
      }
      setSelectedIds((current) => new Set([...current].filter((id) => !affectedIds.has(id))));
      Alert.alert(result.affected_ids.length === 1 ? "Elemento eliminado" : "Elementos eliminados", result.message);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSubmitting(false);
    }
  }, [activeSection, apiRequest]);

  const confirmDeleteItem = useCallback((item: AssistantListItem) => {
    Alert.alert(
      `¿Eliminar “${item.title}”?`,
      "Esta acción no se puede deshacer.",
      [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void deleteItems([item.id]) }],
    );
  }, [deleteItems]);

  const confirmDeleteSelected = useCallback(() => {
    if (!selectedIds.size) return;
    Alert.alert(
      activeSection === "chats" ? "Eliminar chats" : "Eliminar propuestas",
      `¿Eliminar ${selectedIds.size} elemento(s)? Esta acción no se puede deshacer.`,
      [{ text: "Cancelar", style: "cancel" }, { text: "Eliminar", style: "destructive", onPress: () => void deleteItems([...selectedIds]) }],
    );
  }, [activeSection, deleteItems, selectedIds]);

  const toggleSelected = useCallback((item: AssistantListItem) => setSelectedIds((current) => {
    const next = new Set(current);
    if (next.has(item.id)) next.delete(item.id);
    else next.add(item.id);
    return next;
  }), []);

  const changeSection = useCallback((section: AssistantSection) => {
    setMode("list");
    setSelectedIds(new Set());
    setActiveSection(section);
  }, []);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void loadChats(); }, [loadChats, status]));
  useFocusEffect(useCallback(() => { if (status === "authenticated") void loadProposals(); }, [loadProposals, status]));
  useFocusEffect(useCallback(() => {
    if (mode === "edit" && selectedIds.size) {
      setHeaderPresentation({
        action: { disabled: submitting, label: "Eliminar", onPress: confirmDeleteSelected },
        identityVisible: true,
        leadingAction: { disabled: submitting, label: "Cancelar", onPress: cancelSelection },
        mode: "back",
        title: activeSection === "chats" ? "Eliminar chats" : "Eliminar propuestas",
      });
    } else if (mode === "edit") {
      setHeaderPresentation({
        action: { disabled: chatsLoading || proposalsLoading || submitting, label: "Listo", onPress: finishEdit },
        identityVisible: true,
        mode: "default",
        title: activeSection === "chats" ? "Editar chats" : "Editar propuestas",
      });
    } else {
      setHeaderPresentation({
        action: { icon: "more", label: activeSection === "chats" ? "Acciones de Chats" : "Acciones de Propuestas", onPress: () => setActionsVisible(true) },
        createAction: { icon: "plus", label: "Nuevo chat", onPress: () => router.push("/assistant/new" as Href) },
        identityVisible: compactHeaderVisible,
        mode: "default",
        title: "Asistente Nutricional",
      });
    }
    return () => setHeaderPresentation({ mode: "default" });
  }, [activeSection, cancelSelection, chatsLoading, compactHeaderVisible, confirmDeleteSelected, finishEdit, mode, proposalsLoading, router, selectedIds.size, setHeaderPresentation, submitting]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (chatsLoading && proposalsLoading && !chatPage && !proposalPage) return <LoadingState label="Abriendo el Asistente Nutricional…" />;

  const counts = { chats: chatPage?.total ?? 0, proposals: proposalPage?.total ?? 0 };
  const scrollHeader = (
    <View style={styles.scrollHeader}>
      <SectionPageHeader countLabel="elementos" section="chat" title="Asistente Nutricional" />
      {chatPage?.availability ? (
        <AssistantCreditBalance availability={chatPage.availability} />
      ) : null}
    </View>
  );

  return (
    <Screen
      headerMode="preserve"
      onHeaderVisibilityChange={setCompactHeaderVisible}
      scrollHeader={scrollHeader}
      stickyHeader={mode === "list" ? <AssistantSectionTabs activeSection={activeSection} counts={counts} onChange={changeSection} /> : undefined}
      stickyHeaderStyle={styles.stickyHeader}
    >
      {mode === "edit" ? (
        <>
          {(activeSection === "chats" ? chatError : proposalError) ? <InlineNotice tone="error">{activeSection === "chats" ? chatError : proposalError}</InlineNotice> : null}
          <AssistantListEditor
            busy={submitting}
            items={activeSection === "chats" ? (chatPage?.items ?? []) : (proposalPage?.items ?? [])}
            kind={activeSection === "chats" ? "chat" : "proposal"}
            onDelete={confirmDeleteItem}
            onToggle={toggleSelected}
            selectedIds={selectedIds}
          />
        </>
      ) : activeSection === "chats" ? (
        <>
          {chatPage?.availability.available_credits === 0 ? (
            <Card accent={tokens.color.warning}>
              <Text style={styles.creditTitle}>No tienes créditos disponibles</Text>
              <Text style={styles.creditCopy}>Agrega créditos para iniciar una conversación nueva o continuar una existente.</Text>
              <Button label="Comprar créditos" onPress={() => router.push("/subscription" as Href)} />
            </Card>
          ) : null}
          {chatPage?.pending_new_turn ? <InlineNotice tone="warning">Hay una conversación nueva procesándose. Ábrela para recuperar su resultado.</InlineNotice> : null}
          {chatError ? <RecoverableErrorState message={chatError} onRetry={() => void loadChats()} /> : null}
          {chatsLoading && chatPage ? <Text style={textStyles.caption}>Actualizando…</Text> : null}
          {chatPage?.items.length ? chatPage.items.map((chat) => (
            <ChatCard chat={chat} key={chat.id} onPress={() => router.push(`/assistant/${chat.id}` as Href)} />
          )) : !chatError && !chatsLoading ? (
            <EmptyState actionLabel="Iniciar conversación" message="Conversa con el Asistente para definir o ajustar tu planificación nutricional." onAction={() => router.push("/assistant/new" as Href)} title="Aún no tienes chats" />
          ) : null}
        </>
      ) : (
        <>
          {proposalError ? <RecoverableErrorState message={proposalError} onRetry={() => void loadProposals()} /> : null}
          {proposalsLoading && proposalPage ? <Text style={textStyles.caption}>Actualizando…</Text> : null}
          {proposalPage?.items.length ? proposalPage.items.map((proposal) => (
            <ProposalListCard key={proposal.id} onPress={() => router.push(`/proposals/${proposal.id}` as Href)} proposal={proposal} />
          )) : !proposalError && !proposalsLoading ? (
            <EmptyState message="Las propuestas creadas por el Asistente aparecerán aquí para que puedas revisarlas antes de modificar tu librería." title="Aún no hay propuestas" />
          ) : null}
        </>
      )}
      <AssistantListActions
        onClose={() => setActionsVisible(false)}
        onEdit={() => void beginEdit()}
        section={activeSection}
        visible={actionsVisible}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  chatCard: { paddingBottom: tokens.card.innerPadding },
  chatLink: { gap: tokens.card.gap },
  copy: { flex: 1, gap: 4 },
  creditCopy: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  creditTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  eyebrow: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, textTransform: "uppercase" },
  eyebrowRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  pressed: { opacity: 0.65 },
  row: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  scrollHeader: { alignSelf: "stretch", gap: tokens.spacing.md },
  stickyHeader: { marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, paddingTop: tokens.spacing.sm },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
});
