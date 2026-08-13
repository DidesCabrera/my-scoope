import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { MobileAction, ProposalDetail, ProposalStatus } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ProposalDailyPlanPreview, ProposalFacts, ProposalMealPreview } from "@/components/proposals/proposal-preview";
import { ConfirmationState, RecoverableErrorState } from "@/components/ui/screen-states";
import { AppHeader, Button, Card, InlineNotice, LoadingState, Pill, Screen, SectionTitle, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

const statusColors: Record<ProposalStatus, string> = {
  applied: tokens.color.success,
  approved: tokens.color.interactivePrimary,
  cancelled: tokens.color.textSoft,
  draft: tokens.color.textSoft,
  pending_review: tokens.color.warning,
  rejected: tokens.color.danger,
};

const confirmationCopy: Record<string, { title: string; message: string; label: string; danger?: boolean }> = {
  approve: { title: "¿Aprobar esta propuesta?", message: "La aprobación confirma tu revisión, pero aún no crea ni modifica ninguna entidad. Después podrás aplicarla en un paso separado.", label: "Aprobar" },
  reject: { title: "¿Rechazar esta propuesta?", message: "La propuesta quedará cerrada como rechazada y no podrá aplicarse.", label: "Rechazar", danger: true },
  cancel: { title: "¿Cancelar esta propuesta?", message: "La propuesta quedará cerrada y no se aplicará a tu librería.", label: "Cancelar propuesta", danger: true },
  apply: { title: "¿Aplicar esta propuesta?", message: "Se creará la entidad propuesta en tu librería usando el contenido que revisaste.", label: "Aplicar" },
};

export default function ProposalDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { status, apiRequest } = useSession();
  const [proposal, setProposal] = useState<ProposalDetail | null>(null);
  const [pendingAction, setPendingAction] = useState<MobileAction | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setProposal(await apiRequest<ProposalDetail>(`/api/v1/proposals/${id}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, id]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !proposal) return <LoadingState label="Abriendo la propuesta…" />;

  async function execute(action: MobileAction) {
    if (!proposal) return;
    setActing(true);
    setError(null);
    try {
      const body = action.key === "apply" ? JSON.stringify({ acknowledge_external_subject: proposal.subject_context_warning.requires_warning }) : undefined;
      const updated = await apiRequest<ProposalDetail>(`/api/v1/proposals/${proposal.id}/${action.key}`, { method: "POST", body });
      setProposal(updated);
      setPendingAction(null);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setActing(false);
    }
  }

  function openAppliedResult() {
    const result = proposal?.applied_result;
    if (!result?.object_id || !result.kind) return;
    const path = result.kind === "meal" ? `/libraries/meals/${result.object_id}` : `/libraries/daily-plans/${result.object_id}`;
    router.push(path as Href);
  }

  const confirmation = pendingAction ? confirmationCopy[pendingAction.key] : null;
  const applyWarning = pendingAction?.key === "apply" && proposal?.subject_context_warning.requires_warning ? proposal.subject_context_warning : null;

  return (
    <Screen>
      <AppHeader eyebrow={proposal?.entity_title || "Revisión confiable"} title={proposal?.title || "Propuesta"} />
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {proposal ? (
        <>
          <Card accent={statusColors[proposal.status]}>
            <View style={styles.row}><View style={styles.copy}><Text style={styles.source}>{proposal.source === "ai" ? "Creada por AI" : `Origen ${proposal.source}`}</Text><Text style={textStyles.muted}>{proposal.summary || "Sin resumen adicional."}</Text></View><Pill color={statusColors[proposal.status]} label={proposal.status_label} /></View>
            <Text style={textStyles.caption}>Creada por {proposal.created_by_username}{proposal.reviewed_by_username ? ` · Revisada por ${proposal.reviewed_by_username}` : ""}</Text>
          </Card>

          {proposal.subject_context_warning.requires_warning ? <InlineNotice tone="warning">{proposal.subject_context_warning.message}</InlineNotice> : null}
          {proposal.meal ? <ProposalMealPreview meal={proposal.meal} /> : null}
          {proposal.dailyplan ? <ProposalDailyPlanPreview dailyplan={proposal.dailyplan} /> : null}
          {!proposal.meal && !proposal.dailyplan ? <InlineNotice>Esta propuesta conserva su contenido y validación, pero su tipo no genera una entidad aplicable desde móvil.</InlineNotice> : null}

          <ProposalFacts facts={proposal.target_facts} title="Objetivos" />
          <ProposalFacts facts={proposal.current_facts} title="Estado de referencia" />
          <ProposalFacts facts={proposal.validation_facts} title="Validación" />

          {proposal.applied_result ? (
            <Card accent={tokens.color.success}>
              <SectionTitle title="Resultado aplicado" />
              <Text style={textStyles.muted}>La propuesta creó “{proposal.applied_result.object_name}” en tu librería.</Text>
              {proposal.applied_result.object_id ? <Button label="Abrir resultado" onPress={openAppliedResult} /> : null}
            </Card>
          ) : null}

          {pendingAction && confirmation ? (
            <ConfirmationState
              busy={acting}
              confirmLabel={confirmation.label}
              danger={confirmation.danger}
              message={applyWarning ? `${applyWarning.message} Al continuar confirmas que entiendes este cambio de referencia para PPK.` : confirmation.message}
              onCancel={() => setPendingAction(null)}
              onConfirm={() => void execute(pendingAction)}
              title={applyWarning?.title || confirmation.title}
            />
          ) : proposal.actions.length ? (
            <View style={styles.actions}>
              {proposal.actions.map((action) => <Button key={action.key} label={action.label} onPress={() => setPendingAction(action)} variant={action.tone === "danger" ? "danger" : action.key === "approve" || action.key === "apply" ? "primary" : "secondary"} />)}
            </View>
          ) : <Text style={textStyles.caption}>Esta propuesta no tiene acciones pendientes.</Text>}
          <Button label="Volver a Propuestas" onPress={() => { if (router.canGoBack()) router.back(); else router.replace("/proposals" as Href); }} variant="secondary" />
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: { gap: tokens.spacing.sm },
  copy: { flex: 1, gap: tokens.spacing.sm },
  row: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  source: { color: tokens.color.textSoft, fontSize: 11, fontWeight: "900", letterSpacing: 1.1, textTransform: "uppercase" },
});
