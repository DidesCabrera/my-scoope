import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useRef, useState } from "react";
import { ScrollView, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CompositionMutationResult, LibraryItem, LibraryWeekPanelItem, PickerCommitResult, PickerPreview } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { EntityDetailPage } from "@/components/details";
import { ProgramWeekDetail } from "@/components/libraries/program-detail-preview";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { pickerHref } from "@/components/pickers/composition-picker-screen";
import { LoadingState } from "@/components/ui";
import { RecoverableErrorState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";

function filledDays(week?: LibraryWeekPanelItem): number {
  return week?.filled_days_count ?? week?.days.filter((day) => day.plan_name).length ?? 0;
}

export default function WeekToProgramPickerRoute() {
  const { programId, weekNumber } = useLocalSearchParams<{ programId?: string; weekNumber?: string }>();
  const targetId = Number(programId);
  const createdWeek = Number(weekNumber);
  const hasCreatedWeek = Number.isInteger(createdWeek) && createdWeek > 0;
  const router = useRouter();
  const detailHref = `/libraries/programs/${targetId}` as Href;
  const returnHref = `/pickers/week-to-program?programId=${targetId}&weekNumber=${createdWeek}` as Href;
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [target, setTarget] = useState<LibraryItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const creatingWeek = useRef(false);

  const finish = useCallback(() => router.dismissTo(detailHref), [detailHref, router]);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      action: { label: hasCreatedWeek ? "Finalizar" : "Cancelar", onPress: finish },
      fallback: detailHref,
      mode: "back",
      title: hasCreatedWeek ? `Nueva semana ${createdWeek}` : "Agregar semana",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [createdWeek, detailHref, finish, hasCreatedWeek, setHeaderPresentation]));

  const load = useCallback(async ({ showLoading = false } = {}) => {
    if (!targetId) return;
    if (!hasCreatedWeek && creatingWeek.current) return;
    if (!hasCreatedWeek) creatingWeek.current = true;
    if (showLoading) setLoading(true);
    setError(null);
    try {
      if (!hasCreatedWeek) {
        const nextPreview = await apiRequest<PickerPreview>(`/api/v1/library/programs/${targetId}/week-picker/preview`, { method: "POST" });
        const result = await apiRequest<PickerCommitResult>(`/api/v1/library/programs/${targetId}/week-picker/commit?expected_week_number=${nextPreview.selection.id}`, { method: "POST" });
        router.replace(`/pickers/week-to-program?programId=${targetId}&weekNumber=${result.created_id}` as Href);
        return;
      }
      setTarget(await apiRequest<LibraryItem>(`/api/v1/library/programs/${targetId}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
      creatingWeek.current = false;
    } finally {
      setLoading(false);
    }
  }, [apiRequest, hasCreatedWeek, router, targetId]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));

  async function removeDailyPlan(week: number, day: number) {
    try {
      await apiRequest<CompositionMutationResult>(`/api/v1/library/programs/${targetId}/weeks/${week}/days/${day}`, { method: "DELETE" });
      await load();
    } catch (nextError) {
      setError(userFacingError(nextError));
      throw nextError;
    }
  }

  if (!Number.isInteger(targetId) || targetId <= 0) return <Redirect href="/libraries/programs" />;
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label={hasCreatedWeek ? "Preparando la nueva semana…" : "Creando nueva semana…"} />;
  if (!hasCreatedWeek) return <RecoverableErrorState message={error ?? "No pudimos crear la nueva semana."} onRetry={() => void load({ showLoading: true })} />;

  const week = target?.panel.kind === "weeks" ? target.panel.weeks.find((item) => item.week_number === createdWeek) : undefined;
  const assignedPlans = filledDays(week);
  const weekIndicators = week && assignedPlans > 0 ? [
    { icon: "dailyPlan" as const, label: "planes diarios", value: assignedPlans },
    { icon: "meal" as const, label: "comidas", value: week.meals_count ?? 0 },
    { icon: "food" as const, label: "alimentos", value: week.foods_count ?? week.foods?.length ?? 0 },
  ] : undefined;

  return (
    <SafeAreaView edges={["left", "right"]} style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        {target && week ? (
          <EntityDetailPage
            entity="program"
            eyebrow="Nueva semana"
            indicators={weekIndicators}
            nutrition={libraryNutrition(target.nutrition)}
            showNutrition={false}
            title={`Semana ${createdWeek}`}>
            {error ? <RecoverableErrorState message={error} onRetry={() => void load({ showLoading: true })} /> : null}
            <ProgramWeekDetail
              onAssignDailyPlan={(selectedWeek, day) => router.push(pickerHref("dailyplan-to-program", { dayNumber: day, programId: targetId, returnTo: String(returnHref), weekNumber: selectedWeek }))}
              onRemoveDailyPlan={removeDailyPlan}
              showHeading={false}
              week={createdWeek}
              weekData={week}
            />
          </EntityDetailPage>
        ) : (
          <RecoverableErrorState message={error ?? "La nueva semana no está disponible."} onRetry={() => void load({ showLoading: true })} />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.sm },
});
