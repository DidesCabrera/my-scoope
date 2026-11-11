import * as Crypto from "expo-crypto";
import { type Href, useRouter } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarDayDetailData, CalendarDayHistoryData, LibraryPageData } from "@/api/types";
import { CalendarCommitmentListCard } from "@/components/calendarization/calendar-commitment-list-card";
import { CalendarizedDailyPlanCard } from "@/components/calendarization/calendarized-daily-plan-card";
import { DailyPlanPreviewCard } from "@/components/calendarization/daily-plan-preview-card";
import { ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, Card, InlineNotice, LoadingState, SearchField } from "@/components/ui";
import { SearchSuggestions } from "@/components/ui/search-suggestions";
import { useSearchSuggestions } from "@/components/ui/use-search-suggestions";
import { tokens } from "@/design/tokens";

type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

export function CalendarPlanEditor({ apiRequest, day, localToday, onChanged, onClose, onSelectItem, selectedItem }: {
  apiRequest: ApiRequest;
  day: CalendarDayDetailData;
  localToday: string;
  onChanged(): Promise<void> | void;
  onClose(): void;
  onSelectItem(item: "assign" | "replace" | "history" | null): void;
  selectedItem: "assign" | "replace" | "history" | null;
}) {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [submittedSearch, setSubmittedSearch] = useState("");
  const [plans, setPlans] = useState<LibraryPageData["items"]>([]);
  const [plansLoading, setPlansLoading] = useState(true);
  const [history, setHistory] = useState<CalendarDayHistoryData["items"]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<{ id: number; name: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const assigningRef = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const loadPlans = useCallback((term: string, limit: number) =>
    apiRequest<LibraryPageData>(`/api/v1/library/daily-plans?limit=${limit}&search=${encodeURIComponent(term)}`)
      .then((result) => result.items), [apiRequest]);
  const suggestions = useSearchSuggestions({
    enabled: selectedItem === "assign" || selectedItem === "replace" || !day.has_plan,
    load: useCallback((term: string) => loadPlans(term, 5), [loadPlans]),
    query: search,
    submittedQuery: submittedSearch,
  });

  useEffect(() => {
    if (day.has_plan && selectedItem !== "replace") return;
    let active = true;
    const timeout = setTimeout(() => {
      setPlansLoading(true);
      void loadPlans(submittedSearch, 50)
        .then((items) => { if (active) setPlans(items); })
        .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
        .finally(() => { if (active) setPlansLoading(false); });
    }, submittedSearch ? 200 : 0);
    return () => { active = false; clearTimeout(timeout); };
  }, [day.has_plan, loadPlans, selectedItem, submittedSearch]);
  useEffect(() => {
    if (selectedItem !== "history") return;
    let active = true;
    void apiRequest<CalendarDayHistoryData>(`/api/v1/calendar/days/${day.calendar_date}/history`)
      .then((result) => { if (active) setHistory(result.items); })
      .catch((nextError) => { if (active) setHistoryError(userFacingError(nextError)); })
      .finally(() => { if (active) setHistoryLoading(false); });
    return () => { active = false; };
  }, [apiRequest, day.calendar_date, selectedItem]);

  async function assign(replaceExisting: boolean, plan = selectedPlan) {
    if (!plan || assigningRef.current) return;
    assigningRef.current = true;
    setBusy(true);
    setError(null);
    try {
      await apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${day.calendar_date}/plan`, {
        body: JSON.stringify({ dailyplan_id: plan.id, assignment_key: Crypto.randomUUID(), replace_existing: replaceExisting }),
        method: "PUT",
      });
      await onChanged();
      onClose();
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      assigningRef.current = false;
      setBusy(false);
    }
  }

  const past = day.calendar_date < localToday;
  const locked = past || day.has_execution;

  if (selectedItem === "assign" || selectedItem === "replace") {
    const replacing = selectedItem === "replace";
    return <>
    <Text style={styles.sectionTitle}>{replacing ? "Reemplazar minuta diaria" : "Agregar minuta"}</Text>
    <Text style={styles.helper}>Selecciona una minuta de tu biblioteca para {shortDate(day.calendar_date)}.</Text>
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    {!replacing && busy ? <View accessibilityLiveRegion="polite" style={styles.assignmentStatus}>
      <ActivityIndicator color={tokens.color.dailyPlan} size="small" />
      <Text style={styles.assignmentStatusText}>Agregando minuta…</Text>
    </View> : null}
    <View style={styles.searchWrap}>
      <SearchField busy={plansLoading} onChangeText={setSearch} onClear={() => { setSearch(""); setSubmittedSearch(""); }} onSubmitEditing={() => setSubmittedSearch(search.trim())} placeholder="Buscar minuta diaria" returnKeyType="search" value={search} />
      <SearchSuggestions items={suggestions} onSelect={(plan) => {
        const choice = { id: plan.id, name: plan.name };
        if (replacing) setSelectedPlan(choice);
        else void assign(false, choice);
      }} />
    </View>
    <View style={styles.alternatives}>
      {plans.map((plan) => <DailyPlanPreviewCard action={{ disabled: busy, label: "Seleccionar", onPress: () => {
        const choice = { id: plan.id, name: plan.name };
        if (replacing) setSelectedPlan(choice);
        else void assign(false, choice);
      } }} item={plan} key={plan.id} />)}
    </View>
    {!plansLoading && !plans.length && !error ? <Text style={styles.helper}>No encontramos minutas diarias.</Text> : null}
    {replacing ? <ActionSheetModal onRequestClose={() => { if (!busy) setSelectedPlan(null); }} visible={selectedPlan != null}>
      <SafeAreaView edges={["left", "right"]} style={styles.planMenu}>
        <ActionSheetHeader entity="dailyPlan" onClose={() => { if (!busy) setSelectedPlan(null); }} title="¿Reemplazar esta minuta?" />
        <View style={styles.confirmationContent}>
          {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
          <Text style={styles.confirmationText}>“{day.plan_name}” conservará su historial. “{selectedPlan?.name}” quedará vigente para esta fecha.</Text>
          <Button label="Reemplazar minuta" loading={busy} onPress={() => void assign(true)} />
          <Button disabled={busy} label="Cancelar" onPress={() => setSelectedPlan(null)} variant="secondary" />
        </View>
      </SafeAreaView>
    </ActionSheetModal> : null}
    </>;
  }
  if (selectedItem === "history") return <>
    <Text style={styles.sectionTitle}>Historial de esta fecha</Text>
    {historyError ? <InlineNotice tone="error">{historyError}</InlineNotice> : null}
    {historyLoading ? <LoadingState label="Cargando historial…" /> : history.length ? history.map((version) => <Card accent={tokens.color.dailyPlan} key={version.id}>
      <Text style={styles.assignmentTitle}>{version.plan_name || "Día sin plan"}</Text>
      <Text style={styles.historyMeta}>
        {version.assignment_state === "current" ? "Vigente" : version.assignment_state === "removed" ? "Quitado" : "Sustituido"}
        {version.source_program_name ? ` · ${version.source_program_name}` : " · Plan individual"}
        {version.execution_events ? ` · ${version.execution_events} registros` : ""}
      </Text>
    </Card>) : !historyError ? <InlineNotice>No hay cambios anteriores para esta fecha.</InlineNotice> : null}
  </>;
  return (<>
    {day.has_plan && day.plan_snapshot ? <CalendarizedDailyPlanCard
      apiRequest={apiRequest}
      calendarActionsDisabled={locked}
      calendarDate={day.calendar_date}
      dateLabel={shortDate(day.calendar_date)}
      dayId={day.id}
      eyebrow={day.source_program_name ?? "PLAN DE CALENDARIO"}
      localToday={localToday}
      mealExecution={day.meal_execution}
      onChanged={onChanged}
      onMovePlan={onChanged}
      onRemoveFromCalendar={async () => {
        await apiRequest(`/api/v1/calendar/days/${day.calendar_date}/plan`, { method: "DELETE" });
        await onChanged();
      }}
      onRenameCalendarized={async (name) => {
        await apiRequest(`/api/v1/program/days/${day.id}`, { body: JSON.stringify({ name }), method: "PATCH" });
        await onChanged();
      }}
      onReplacePlan={() => onSelectItem("replace")}
      planName={day.plan_name}
      snapshot={day.plan_snapshot}
      sourceKind={day.source_kind}
    /> : null}
    {day.commitments?.map((commitment) => <CalendarCommitmentListCard commitment={commitment} key={commitment.id} onPress={() => router.push(`/calendar/commitments/${commitment.id}?date=${day.calendar_date}` as Href)} />)}
    {!day.has_plan && !day.commitments?.length ? <InlineNotice>No hay planes ni compromisos programados para este día.</InlineNotice> : null}
    {!day.has_plan ? <>
      <Text style={styles.title}>Asignar minuta diaria</Text>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {locked ? <InlineNotice>{past ? "Los días anteriores no se modifican. Su evidencia permanece en el historial." : "Este día ya tiene cumplimiento registrado y no se puede sustituir ni mover."}</InlineNotice> : (
        <View style={styles.group}>
          <View style={styles.searchWrap}>
            <SearchField onChangeText={setSearch} onClear={() => { setSearch(""); setSubmittedSearch(""); }} onSubmitEditing={() => setSubmittedSearch(search.trim())} placeholder="Buscar plan de biblioteca" returnKeyType="search" value={search} />
            <SearchSuggestions items={suggestions} onSelect={(plan) => { if (!busy) void assignPlanFromChoice(plan.id, plan.name); }} />
          </View>
          <View style={styles.alternatives}>
            {plans.map((plan) => <DailyPlanPreviewCard action={{ label: "Asignar", onPress: () => { if (!busy) void assignPlanFromChoice(plan.id, plan.name); } }} item={plan} key={plan.id} />)}
          </View>
        </View>
      )}
    </> : null}
    </>
  );

  async function assignPlanFromChoice(planId: number, planName: string) {
    setBusy(true);
    setError(null);
    try {
      await apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${day.calendar_date}/plan`, {
        body: JSON.stringify({ dailyplan_id: planId, assignment_key: Crypto.randomUUID(), replace_existing: false }),
        method: "PUT",
      });
      await onChanged();
      onClose();
    } catch (nextError) {
      setSelectedPlan({ id: planId, name: planName });
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }
}

const styles = StyleSheet.create({
  alternatives: { gap: tokens.spacing.md, marginHorizontal: -6 },
  assignmentStatus: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  assignmentStatusText: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  assignmentTitle: { color: tokens.color.textMain, fontSize: 18, fontWeight: "700" },
  group: { gap: tokens.spacing.md },
  searchWrap: { position: "relative", zIndex: 2 },
  helper: { color: tokens.color.textMuted, fontSize: 13 },
  historyMeta: { color: tokens.color.textMuted, fontSize: 12 },
  planMenu: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  confirmationContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl, paddingTop: 0 },
  confirmationText: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23, marginBottom: 18 },
  sectionTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "700" },
  title: { color: tokens.color.textMain, fontSize: 18, fontWeight: "600" },
});
