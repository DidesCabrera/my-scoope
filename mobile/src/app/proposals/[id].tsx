import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Text } from "react-native";

import { userFacingError } from "@/api/errors";
import type { MobileAction, ProposalDetail, ProposalStatus } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import {
  ProposalDailyPlanCard,
  ProposalEvaluationContext,
  ProposalFacts,
  ProposalMealCard,
} from "@/components/proposals/proposal-preview";
import {
  ProposalDetailPage,
  ProposalEntitySection,
  ProposalReviewActions,
} from "@/components/proposals";
import { ConfirmationState, RecoverableErrorState } from "@/components/ui/screen-states";
import { Button, Card, EntityCardAction, InlineNotice, LoadingState, Screen, SectionTitle, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { ProposalProgramPreview } from "@/components/proposals/proposal-program-preview";

const confirmationCopy: Record<string, { title: string; message: string; label: string; danger?: boolean }> = {
  approve: { title: "¿Aprobar esta propuesta?", message: "La aprobación confirma tu revisión, pero aún no crea ni modifica ninguna entidad. Después podrás aplicarla en un paso separado.", label: "Aprobar" },
  reject: { title: "¿Rechazar esta propuesta?", message: "La propuesta quedará cerrada como rechazada y no podrá aplicarse.", label: "Rechazar", danger: true },
  cancel: { title: "¿Cancelar esta propuesta?", message: "La propuesta quedará cerrada y no se aplicará a tu librería.", label: "Cancelar propuesta", danger: true },
  apply: { title: "¿Aplicar esta propuesta?", message: "Se creará la entidad propuesta en tu librería usando el contenido que revisaste.", label: "Aplicar" },
};

function proposalStatus(status: ProposalStatus): "pending" | "approved" | "applied" | "rejected" | "cancelled" {
  if (status === "pending_review" || status === "draft") return "pending";
  return status;
}

function receivedAt(value: string | null): string {
  if (!value) return "Fecha de recepción no disponible";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Fecha de recepción no disponible";
  return `Recibida ${date.toLocaleDateString("es-CL", { day: "numeric", month: "short", year: "numeric" })}`;
}

export default function ProposalDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
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
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/assistant?section=proposals" as Href, mode: "back", title: "Detalle de propuesta" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [setHeaderPresentation]));

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
    const path = result.kind === "program" ? `/libraries/programs/${result.object_id}` : result.kind === "meal" ? `/libraries/meals/${result.object_id}` : `/libraries/daily-plans/${result.object_id}`;
    router.push(path as Href);
  }

  const confirmation = pendingAction ? confirmationCopy[pendingAction.key] : null;
  const applyWarning = pendingAction?.key === "apply" && proposal?.subject_context_warning.requires_warning ? proposal.subject_context_warning : null;
  const action = (key: string) => proposal?.actions.find((item) => item.key === key);
  const openEntity = () => proposal && router.push(`/proposals/${proposal.id}/entity` as Href);
  const entityAction = proposal && (proposal.meal || proposal.dailyplan) ? (
    <EntityCardAction label={`Ver detalle de ${proposal.attachment_name}`} onPress={openEntity} role="link">
      <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
    </EntityCardAction>
  ) : undefined;

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {proposal ? (
        <ProposalDetailPage
          isRead
          proposedEntity={proposal.meal || proposal.dailyplan ? (
            <ProposalEntitySection entity={proposal.meal ? "meal" : "dailyPlan"}>
              {proposal.meal ? <ProposalMealCard actions={entityAction} meal={proposal.meal} onOpenFood={(foodId) => router.push(`/libraries/foods/${foodId}` as Href)} /> : null}
              {proposal.dailyplan ? <ProposalDailyPlanCard actions={entityAction} dailyplan={proposal.dailyplan} /> : null}
            </ProposalEntitySection>
          ) : undefined}
          receivedAt={receivedAt(proposal.created_at)}
          status={proposalStatus(proposal.status)}
          summary={proposal.summary}
          title={proposal.title}
          typeLabel={proposal.attachment_label}>
          {proposal.subject_context_warning.requires_warning ? <InlineNotice tone="warning">{proposal.subject_context_warning.message}</InlineNotice> : null}
          {proposal.program ? <ProposalEntitySection entity="program"><ProposalProgramPreview program={proposal.program} onOpenFood={(foodId) => router.push(`/libraries/foods/${foodId}` as Href)} /></ProposalEntitySection> : null}
          {!proposal.meal && !proposal.dailyplan && !proposal.program ? <InlineNotice>Esta propuesta conserva su contenido y validación, pero su tipo no genera una entidad aplicable desde móvil.</InlineNotice> : null}

          <ProposalEvaluationContext current={proposal.current_facts} targets={proposal.target_facts} />
          <ProposalFacts description="Comprobaciones realizadas antes de permitir que la propuesta se aplique." facts={proposal.validation_facts} title="Validación" />

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
            <ProposalReviewActions
              description="Revisa el contenido y la validación antes de confirmar cualquier cambio en tu biblioteca."
              onApply={action("apply") ? () => setPendingAction(action("apply")!) : undefined}
              onApprove={action("approve") ? () => setPendingAction(action("approve")!) : undefined}
              onCancel={action("cancel") ? () => setPendingAction(action("cancel")!) : undefined}
              onReject={action("reject") ? () => setPendingAction(action("reject")!) : undefined}
            />
          ) : <Text style={textStyles.caption}>Esta propuesta no tiene acciones pendientes.</Text>}
          <Button label="Volver a Propuestas" onPress={() => { if (router.canGoBack()) router.back(); else router.replace("/assistant?section=proposals" as Href); }} variant="secondary" />
        </ProposalDetailPage>
      ) : null}
    </Screen>
  );
}
