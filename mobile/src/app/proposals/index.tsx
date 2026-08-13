import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ProposalListData, ProposalStatus, ProposalSummary } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { AppHeader, Card, ChoiceRow, LoadingState, Pill, Screen, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

type Filter = "all" | "pending_review" | "approved" | "applied" | "rejected";

const filters: { value: Filter; label: string }[] = [
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

function displayDate(value: string | null): string {
  if (!value) return "Sin fecha";
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function ProposalCard({ proposal, onPress }: { proposal: ProposalSummary; onPress(): void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => pressed && styles.pressed}>
      <Card accent={statusColors[proposal.status]}>
        <View style={styles.row}>
          <View style={styles.copy}><Text style={styles.source}>{proposal.source === "ai" ? "AI" : proposal.source.toUpperCase()} · {displayDate(proposal.created_at)}</Text><Text style={styles.title}>{proposal.title}</Text></View>
          <Pill color={statusColors[proposal.status]} label={proposal.status_label} />
        </View>
        {proposal.summary ? <Text numberOfLines={3} style={textStyles.muted}>{proposal.summary}</Text> : null}
        <View style={styles.attachment}><View style={styles.copy}><Text style={textStyles.caption}>{proposal.attachment_label}</Text><Text style={textStyles.strong}>{proposal.attachment_name}</Text></View><Text style={styles.chevron}>›</Text></View>
      </Card>
    </Pressable>
  );
}

export default function ProposalsScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [page, setPage] = useState<ProposalListData | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query = filter === "all" ? "" : `?status=${filter}`;
      setPage(await apiRequest<ProposalListData>(`/api/v1/proposals${query}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, filter]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !page) return <LoadingState label="Buscando tus propuestas…" />;

  return (
    <Screen>
      <AppHeader eyebrow={page?.pending_count ? `${page.pending_count} por revisar` : "Centro de revisión"} title="Propuestas" />
      <ChoiceRow<Filter> label="Estado" onChange={setFilter} options={filters} value={filter} />
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {loading ? <Text style={textStyles.caption}>Actualizando…</Text> : null}
      {page?.items.length ? page.items.map((proposal) => <ProposalCard key={proposal.id} onPress={() => router.push(`/proposals/${proposal.id}` as Href)} proposal={proposal} />) : (
        <EmptyState message="Las propuestas creadas por el Asistente aparecerán aquí para que puedas revisarlas antes de modificar tu librería." title={filter === "all" ? "Aún no hay propuestas" : "No hay propuestas en este estado"} />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  attachment: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, flexDirection: "row", gap: tokens.spacing.md, padding: tokens.spacing.md },
  chevron: { color: tokens.color.textSoft, fontSize: 28 },
  copy: { flex: 1, gap: 4 },
  pressed: { opacity: 0.65 },
  row: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  source: { color: tokens.color.textSoft, fontSize: 11, fontWeight: "900", letterSpacing: 1.1, textTransform: "uppercase" },
  title: { color: tokens.color.textMain, fontSize: 20, fontWeight: "900" },
});
