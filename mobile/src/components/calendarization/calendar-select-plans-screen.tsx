import * as Crypto from "expo-crypto";
import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarDayDetailData, CalendarOverviewData, LibraryItem, LibraryPageData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { NutritionEntityCard } from "@/components/nutrition";
import { PickerCardAction } from "@/components/pickers/picker-card-action";
import { PickerEntryTabs } from "@/components/pickers/picker-entry-tabs";
import { Button, InlineNotice, LoadingState, NativeDateTimeField, Screen, SearchField, SectionHeading } from "@/components/ui";
import { ConfirmationState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";

function readableDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

export default function SelectCalendarPlansScreen() {
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [plans, setPlans] = useState<LibraryItem[]>([]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<LibraryItem | null>(null);
  const [localToday, setLocalToday] = useState("");
  const [date, setDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [confirmReplacement, setConfirmReplacement] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(useCallback(() => {
    const cancel = () => router.dismissTo("/calendar" as Href);
    setHeaderPresentation({
      action: selected ? undefined : { label: "Cancelar", onPress: cancel },
      fallback: "/calendar",
      leadingAction: selected ? { icon: "back", label: "Volver a los planes", onPress: () => { setSelected(null); setConfirmReplacement(null); setError(null); } } : undefined,
      mode: "back",
      title: selected ? "Calendarizar plan" : "Seleccionar plan individual",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [router, selected, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated") return;
    let active = true;
    void apiRequest<CalendarOverviewData>("/api/v1/calendar?days=1")
      .then((overview) => {
        if (!active) return;
        setLocalToday(overview.local_date);
        setDate((current) => current || overview.local_date);
      })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [apiRequest, status]));

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated") return;
    let active = true;
    const timeout = setTimeout(() => {
      setLoading(true);
      setError(null);
      void apiRequest<LibraryPageData>(`/api/v1/library/daily-plans?limit=50&search=${encodeURIComponent(query)}`)
        .then((page) => { if (active) setPlans(page.items); })
        .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
        .finally(() => { if (active) setLoading(false); });
    }, query ? 220 : 0);
    return () => { active = false; clearTimeout(timeout); };
  }, [apiRequest, query, status]));

  async function assign(replaceExisting: boolean) {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${date}/plan`, {
        body: JSON.stringify({ dailyplan_id: selected.id, assignment_key: Crypto.randomUUID(), replace_existing: replaceExisting }),
        method: "PUT",
      });
      router.dismissTo("/calendar" as Href);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function reviewAssignment() {
    if (!selected || !date || date < localToday) return;
    setBusy(true);
    setError(null);
    try {
      const current = await apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${date}`);
      if (current.has_execution) {
        setError("Esta fecha ya tiene registros de cumplimiento y no se puede reemplazar su plan.");
      } else if (current.has_plan) {
        setConfirmReplacement(current.plan_name);
      } else {
        await assign(false);
      }
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  if (status === "anonymous") return <Redirect href="/login" />;

  if (selected) return <Screen headerMode="preserve">
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    <NutritionEntityCard entity="dailyPlan" indicators={selected.indicators} nutrition={libraryNutrition(selected.nutrition)} subtitle={selected.subtitle} title={selected.name} />
    {confirmReplacement ? <ConfirmationState
      busy={busy}
      confirmLabel="Reemplazar y calendarizar"
      message={`“${confirmReplacement}” conservará su historial. “${selected.name}” quedará asignado al ${readableDate(date)}.`}
      onCancel={() => setConfirmReplacement(null)}
      onConfirm={() => void assign(true)}
      title="¿Reemplazar el plan de esta fecha?"
    /> : <>
      <NativeDateTimeField label="Fecha del plan" minimumValue={localToday} mode="date" onChange={(value) => { setDate(value); setConfirmReplacement(null); }} value={date} />
      <Button disabled={busy || !localToday || !date || date < localToday} label="Calendarizar plan" loading={busy} onPress={() => void reviewAssignment()} />
    </>}
  </Screen>;

  return <SafeAreaView edges={["left", "right"]} style={styles.selectionSafeArea}>
    <ScrollView
      automaticallyAdjustKeyboardInsets
      contentContainerStyle={styles.selectionScrollContent}
      keyboardDismissMode="on-drag"
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
      stickyHeaderIndices={[0]}>
      <View style={styles.selectionSticky}>
        <PickerEntryTabs createLabel="Crear Nuevo" onCreate={() => router.push({ pathname: "/libraries/create", params: { entity: "dailyPlan" } })} />
        <SearchField accessibilityLabel="Buscar plan diario" autoCapitalize="words" bleed busy={loading} onChangeText={setQuery} placeholder="Escribe el nombre de un plan" value={query} />
      </View>
      <View style={styles.options}>
        <SectionHeading detail={`${plans.length} disponibles`} title="Selecciona un plan diario" />
        {plans.map((plan) => <NutritionEntityCard
          actions={<PickerCardAction label="Seleccionar" onPress={() => { setSelected(plan); setError(null); }} subject={plan.name} />}
          entity="dailyPlan"
          indicators={plan.indicators}
          key={plan.id}
          nutrition={libraryNutrition(plan.nutrition)}
          subtitle={plan.subtitle}
          title={plan.name}
        />)}
        {!loading && !plans.length && !error ? <Text style={styles.emptyText}>No encontramos planes diarios.</Text> : null}
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        {loading && !plans.length ? <LoadingState label="Buscando tus planes…" /> : null}
      </View>
    </ScrollView>
  </SafeAreaView>;
}

const styles = StyleSheet.create({
  emptyText: { color: tokens.color.textMuted, fontSize: tokens.type.body },
  options: { gap: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen },
  selectionSafeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  selectionScrollContent: { flexGrow: 1, paddingBottom: 42 },
  selectionSticky: { backgroundColor: tokens.color.surfaceApp, gap: tokens.spacing.xs, paddingBottom: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen, zIndex: 2 },
});
