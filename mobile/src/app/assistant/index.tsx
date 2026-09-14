import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { AIChatListData, AIChatSummary, ProposalListData, ProposalStatus, ProposalSummary } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AssistantListActions, type ProposalFilter } from "@/components/assistant/assistant-list-actions";
import { AssistantSectionTabs, type AssistantSection } from "@/components/assistant/assistant-section-tabs";
import { AssistantCreditBalance } from "@/components/assistant/assistant-credit-balance";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { SectionPageHeader } from "@/components/ui";
import { EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { Button, Card, InlineNotice, LoadingState, Pill, Screen, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

const filters: { value: ProposalFilter; label: string }[] = [
  { value: "all", label: "Todas" },
  { value: "pending_review", label: "Pendientes" },
  { value: "approved", label: "Aprobadas" },
  { value: "applied", label: "Aplicadas" },
  { value: "rejected", label: "Rechazadas" },
];

const statusColors: Record<ProposalStatus, string> = {
  applied: tokens.color.success,
  approved: tokens.color.interactivePrimary,
  cancelled: tokens.color.textSoft,
  draft: tokens.color.textSoft,
  pending_review: tokens.color.warning,
  rejected: tokens.color.danger,
};

function ChatCard({ chat, onPress }: { chat: AIChatSummary; onPress(): void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => pressed && styles.pressed}>
      <Card>
        <View style={styles.row}>
          <View style={styles.copy}>
            <Text style={styles.title}>{chat.title}</Text>
            <Text style={textStyles.caption}>{new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(chat.updated_at))}</Text>
          </View>
          <Pill label={chat.status_label} />
        </View>
        <Text numberOfLines={3} style={textStyles.muted}>{chat.last_message_preview}</Text>
        <Text style={textStyles.caption}>{chat.message_count} mensajes · Continuar ›</Text>
      </Card>
    </Pressable>
  );
}

function displayDate(value: string | null): string {
  if (!value) return "Sin fecha";
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function ProposalCard({ proposal, onPress }: { proposal: ProposalSummary; onPress(): void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => pressed && styles.pressed}>
      <Card>
        <View style={styles.row}>
          <View style={styles.copy}>
            <Text style={styles.source}>{proposal.source === "ai" ? "AI" : proposal.source.toUpperCase()} · {displayDate(proposal.created_at)}</Text>
            <Text style={styles.title}>{proposal.title}</Text>
          </View>
          <Pill color={statusColors[proposal.status]} label={proposal.status_label} />
        </View>
        {proposal.summary ? <Text numberOfLines={3} style={textStyles.muted}>{proposal.summary}</Text> : null}
        <View style={styles.attachment}>
          <View style={styles.copy}>
            <Text style={textStyles.caption}>{proposal.attachment_label}</Text>
            <Text style={textStyles.strong}>{proposal.attachment_name}</Text>
          </View>
          <Text style={styles.chevron}>›</Text>
        </View>
      </Card>
    </Pressable>
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
  const [filter, setFilter] = useState<ProposalFilter>("all");
  const [actionsVisible, setActionsVisible] = useState(false);
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
      const query = filter === "all" ? "" : `?status=${filter}`;
      setProposalPage(await apiRequest<ProposalListData>(`/api/v1/proposals${query}`));
    } catch (nextError) {
      setProposalError(userFacingError(nextError));
    } finally {
      setProposalsLoading(false);
    }
  }, [apiRequest, filter]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void loadChats(); }, [loadChats, status]));
  useFocusEffect(useCallback(() => { if (status === "authenticated") void loadProposals(); }, [loadProposals, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      action: { label: activeSection === "chats" ? "Acciones de Chats" : "Acciones de Propuestas", onPress: () => setActionsVisible(true) },
      identityVisible: compactHeaderVisible,
      mode: "default",
      title: "Asistente AI",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [activeSection, compactHeaderVisible, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (chatsLoading && proposalsLoading && !chatPage && !proposalPage) return <LoadingState label="Abriendo el Asistente AI…" />;

  const counts = { chats: chatPage?.total ?? 0, proposals: proposalPage?.total ?? 0 };
  const scrollHeader = (
    <View style={styles.scrollHeader}>
      <SectionPageHeader countLabel="elementos" section="chat" title="Asistente AI" />
      {chatPage?.availability ? (
        <AssistantCreditBalance availability={chatPage.availability} />
      ) : null}
    </View>
  );

  return (
    <Screen
      headerMode="preserve"
      onScroll={({ nativeEvent }) => {
        const visible = nativeEvent.contentOffset.y > 1;
        if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible);
      }}
      scrollHeader={scrollHeader}
      stickyHeader={<AssistantSectionTabs activeSection={activeSection} counts={counts} onChange={setActiveSection} />}
      stickyHeaderStyle={styles.stickyHeader}
    >
      {activeSection === "chats" ? (
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
          <Text style={textStyles.caption}>Filtro: {filters.find((item) => item.value === filter)?.label ?? "Todas"}</Text>
          {proposalError ? <RecoverableErrorState message={proposalError} onRetry={() => void loadProposals()} /> : null}
          {proposalsLoading && proposalPage ? <Text style={textStyles.caption}>Actualizando…</Text> : null}
          {proposalPage?.items.length ? proposalPage.items.map((proposal) => (
            <ProposalCard key={proposal.id} onPress={() => router.push(`/proposals/${proposal.id}` as Href)} proposal={proposal} />
          )) : !proposalError && !proposalsLoading ? (
            <EmptyState message="Las propuestas creadas por el Asistente aparecerán aquí para que puedas revisarlas antes de modificar tu librería." title={filter === "all" ? "Aún no hay propuestas" : "No hay propuestas en este estado"} />
          ) : null}
        </>
      )}
      <AssistantListActions
        activeSection={activeSection}
        onClose={() => setActionsVisible(false)}
        onNewChat={() => router.push("/assistant/new" as Href)}
        onProposalFilterChange={setFilter}
        proposalFilter={filter}
        visible={actionsVisible}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  attachment: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, flexDirection: "row", gap: tokens.spacing.md, padding: tokens.spacing.md },
  chevron: { color: tokens.color.textSoft, fontSize: 28 },
  copy: { flex: 1, gap: 4 },
  creditCopy: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  creditTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  pressed: { opacity: 0.65 },
  row: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  scrollHeader: { gap: tokens.spacing.md },
  source: { color: tokens.color.textSoft, fontSize: 11, fontWeight: "900", letterSpacing: 1.1, textTransform: "uppercase" },
  stickyHeader: { paddingTop: tokens.spacing.sm },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
});
