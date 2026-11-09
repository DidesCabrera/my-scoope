import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { Pin } from "lucide-react-native";
import { useCallback, useMemo, useState } from "react";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import type { CalendarCommitment, CalendarOverviewData } from "@/api/calendar-types";
import { userFacingError } from "@/api/errors";
import { useSession } from "@/auth/session-context";
import { CalendarCommitmentListCard } from "@/components/calendarization/calendar-commitment-list-card";
import { commitmentActionLabel, commitmentKinds, commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import type { CommitmentScope } from "@/components/calendarization/calendar-commitment-registry";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Card, InlineNotice, LoadingState, Screen, ScrollableTabBar, SectionPageHeader } from "@/components/ui";
import { tokens } from "@/design/tokens";

const commitmentTabLabels = { shopping: "Hacer compras", cooking: "Cocinar", training: "Entrenar", nutritionist: "Nutricionista" } as const;

export default function FutureCommitmentsScreen() {
  const router = useRouter();
  const setHeaderPresentation = useHeaderPresentation();
  const { apiRequest, status } = useSession();
  const [commitments, setCommitments] = useState<CalendarCommitment[]>([]);
  const [scope, setScope] = useState<CommitmentScope>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [creationMenuVisible, setCreationMenuVisible] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const overview = await apiRequest<CalendarOverviewData>("/api/v1/calendar?days=1");
      const groups = await Promise.all(commitmentKinds.map((kind) =>
        apiRequest<{ items: CalendarCommitment[] }>(`/api/v1/calendar/commitments?kind=${kind}&from_date=${overview.local_date}`),
      ));
      setCommitments(groups.flatMap((group) => group.items).sort((left, right) =>
        left.calendar_date.localeCompare(right.calendar_date) || left.id - right.id));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ action: { icon: "plus", label: "Agregar compromiso", onPress: () => setCreationMenuVisible(true) }, fallback: "/calendar", identityVisible: compactHeaderVisible, mode: "back", title: "Compromisos futuros" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, setHeaderPresentation]));
  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));

  const visibleCommitments = useMemo(() => commitments.filter((commitment) => scope === "all" || commitment.kind === scope), [commitments, scope]);

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !commitments.length) return <LoadingState label="Cargando compromisos futuros…" />;

  return <><Screen headerMode="preserve" onHeaderVisibilityChange={setCompactHeaderVisible}>
    <SectionPageHeader icon={<Pin color={tokens.color.textMain} size={28} strokeWidth={1.8} />} section="calendarization" subtitle="Todos tus compromisos desde hoy, ordenados por fecha." title="Compromisos futuros" />
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    <ScrollableTabBar<CommitmentScope>
      accessibilityLabel="Tipos de compromisos futuros"
      activeTab={scope}
      density="compact"
      onChange={setScope}
      tabs={[{ key: "all", label: "Todos" }, ...commitmentKinds.map((kind) => {
        const presentation = commitmentPresentation[kind];
        const Icon = presentation.icon;
        return { icon: (selected: boolean) => <Icon color={selected ? tokens.color.surfaceApp : presentation.color} size={14} strokeWidth={2.1} />, key: kind, label: commitmentTabLabels[kind] };
      })]}
    />
    {!loading && !visibleCommitments.length ? <Card><InlineNotice>No hay compromisos futuros programados.</InlineNotice></Card> : null}
    {visibleCommitments.map((commitment) => <CalendarCommitmentListCard
      commitment={commitment}
      key={commitment.id}
      onCreateFoodList={() => router.push(`/calendar/commitments/${commitment.id}/foods?date=${commitment.calendar_date}` as Href)}
      onPress={() => router.push(`/calendar/commitments/${commitment.id}?date=${commitment.calendar_date}` as Href)}
      showFoodListDetails
    />)}
  </Screen>
    <ActionSheetModal onRequestClose={() => setCreationMenuVisible(false)} visible={creationMenuVisible}>
      <SafeAreaView edges={["left", "right"]} style={styles.sheet}>
        <ActionSheetHeader icon={Pin} onClose={() => setCreationMenuVisible(false)} title="Registrar compromiso" />
        <View style={styles.sheetContent}>
          <ActionSheetActions>
            {commitmentKinds.map((kind) => <ActionSheetAction
              icon={commitmentPresentation[kind].icon}
              iconBackgroundColor={`${commitmentPresentation[kind].color}33`}
              iconColor={commitmentPresentation[kind].color}
              key={kind}
              label={commitmentActionLabel[kind]}
              onPress={() => {
                setCreationMenuVisible(false);
                router.push(`/calendar/commitments?kind=${kind}` as Href);
              }}
            />)}
          </ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  </>;
}

const styles = StyleSheet.create({
  sheet: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  sheetContent: { padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
});
