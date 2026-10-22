import * as Crypto from "expo-crypto";
import { type Href, useRouter } from "expo-router";
import { ChevronRight, Ellipsis, MoveRight, Paperclip, Repeat2, Trash2 } from "lucide-react-native";
import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarDay, CalendarDayDetailData, CalendarDayHistoryData, LibraryPageData } from "@/api/types";
import { commitmentDayTitle, commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { libraryNutrition } from "@/components/libraries/presentation-adapters";
import { NutritionEntityCard } from "@/components/nutrition";
import { PickerCardAction } from "@/components/pickers/picker-card-action";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { Button, Card, Chip, EntityCard, EntityCardAction, InlineNotice, LoadingState, NativeDateTimeField, SearchField } from "@/components/ui";
import { ConfirmationState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";

type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

export function CalendarPlanEditor({ apiRequest, day, localToday, onChanged, onClose, onSelectItem, selectedItem }: {
  apiRequest: ApiRequest;
  day: CalendarDay;
  localToday: string;
  onChanged(): Promise<void> | void;
  onClose(): void;
  onSelectItem(item: "replace" | "remove" | "move" | "history" | null): void;
  selectedItem: "replace" | "remove" | "move" | "history" | null;
}) {
  const router = useRouter();
  const [mode, setMode] = useState<"choose" | "confirm-move" | "confirm-assign">("choose");
  const [search, setSearch] = useState("");
  const [plans, setPlans] = useState<LibraryPageData["items"]>([]);
  const [plansLoading, setPlansLoading] = useState(true);
  const [history, setHistory] = useState<CalendarDayHistoryData["items"]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<{ id: number; name: string } | null>(null);
  const [targetDate, setTargetDate] = useState(day.calendar_date);
  const [targetPlan, setTargetPlan] = useState<CalendarDayDetailData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [planMenuVisible, setPlanMenuVisible] = useState(false);

  useEffect(() => {
    if (day.has_plan && selectedItem !== "replace") return;
    let active = true;
    const timeout = setTimeout(() => {
      setPlansLoading(true);
      void apiRequest<LibraryPageData>(`/api/v1/library/daily-plans?limit=50&search=${encodeURIComponent(search)}`)
        .then((result) => { if (active) setPlans(result.items); })
        .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
        .finally(() => { if (active) setPlansLoading(false); });
    }, search ? 200 : 0);
    return () => { active = false; clearTimeout(timeout); };
  }, [apiRequest, day.has_plan, search, selectedItem]);
  useEffect(() => {
    if (selectedItem !== "history") return;
    let active = true;
    void apiRequest<CalendarDayHistoryData>(`/api/v1/calendar/days/${day.calendar_date}/history`)
      .then((result) => { if (active) setHistory(result.items); })
      .catch((nextError) => { if (active) setHistoryError(userFacingError(nextError)); })
      .finally(() => { if (active) setHistoryLoading(false); });
    return () => { active = false; };
  }, [apiRequest, day.calendar_date, selectedItem]);

  async function assign(replaceExisting: boolean) {
    if (!selectedPlan) return;
    setBusy(true);
    setError(null);
    try {
      await apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${day.calendar_date}/plan`, {
        body: JSON.stringify({ dailyplan_id: selectedPlan.id, assignment_key: Crypto.randomUUID(), replace_existing: replaceExisting }),
        method: "PUT",
      });
      await onChanged();
      onClose();
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      await apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${day.calendar_date}/plan`, { method: "DELETE" });
      await onChanged();
      onClose();
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function move() {
    setBusy(true);
    setError(null);
    try {
      await apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${day.calendar_date}/move`, {
        body: JSON.stringify({ target_date: targetDate, assignment_key: Crypto.randomUUID(), replace_existing: Boolean(targetPlan?.has_plan) }),
        method: "POST",
      });
      await onChanged();
      onClose();
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  const past = day.calendar_date < localToday;
  const locked = past || day.has_execution;
  async function reviewMove() {
    setBusy(true);
    setError(null);
    try {
      setTargetPlan(await apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${targetDate}`));
      setMode("confirm-move");
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  if (selectedItem === "replace") return <>
    <Text style={styles.sectionTitle}>Reemplazar plan diario</Text>
    <Text style={styles.helper}>Selecciona un plan de tu biblioteca para {shortDate(day.calendar_date)}.</Text>
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    {mode === "confirm-assign" && selectedPlan ? <ConfirmationState
      busy={busy}
      confirmLabel="Reemplazar plan diario"
      message={`“${day.plan_name}” conservará su historial. “${selectedPlan.name}” quedará vigente para esta fecha.`}
      onCancel={() => setMode("choose")}
      onConfirm={() => void assign(true)}
      title="¿Reemplazar el plan de esta fecha?"
    /> : <>
      <SearchField busy={plansLoading} onChangeText={setSearch} onClear={() => setSearch("")} placeholder="Buscar plan diario" value={search} />
      {plans.map((plan) => <NutritionEntityCard
        actions={<PickerCardAction label="Seleccionar" onPress={() => { setSelectedPlan({ id: plan.id, name: plan.name }); setMode("confirm-assign"); }} subject={plan.name} />}
        entity="dailyPlan"
        indicators={plan.indicators}
        key={plan.id}
        nutrition={libraryNutrition(plan.nutrition)}
        subtitle={plan.subtitle}
        title={plan.name}
      />)}
      {!plansLoading && !plans.length && !error ? <Text style={styles.helper}>No encontramos planes diarios.</Text> : null}
    </>}
  </>;
  if (selectedItem === "remove") return <>
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    <ConfirmationState
      busy={busy}
      confirmLabel="Eliminar plan del calendario"
      danger
      message={`“${day.plan_name}” dejará de estar asignado a ${shortDate(day.calendar_date)}. Su historial y registros anteriores permanecerán guardados.`}
      onCancel={() => onSelectItem(null)}
      onConfirm={() => void remove()}
      title="¿Eliminar este plan del calendario?"
    />
  </>;
  if (selectedItem === "move") return <>
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    {mode === "confirm-move" ? <ConfirmationState
      busy={busy}
      confirmLabel="Confirmar movimiento"
      message={targetPlan?.has_plan
        ? `“${day.plan_name}” pasará a ${targetDate}. El plan “${targetPlan.plan_name}” conservará su snapshot e historial, pero dejará de estar vigente.`
        : `“${day.plan_name}” pasará a ${targetDate}. La fecha original quedará libre y su snapshot permanecerá en el historial.`}
      onCancel={() => setMode("choose")}
      onConfirm={() => void move()}
      title="¿Mover este plan?"
    /> : <Card>
      <Text style={styles.title}>Mover plan diario</Text>
      <NativeDateTimeField label="Nueva fecha" minimumValue={localToday} mode="date" onChange={setTargetDate} value={targetDate} />
      <Button disabled={busy || targetDate < localToday || targetDate === day.calendar_date} label="Revisar movimiento" loading={busy} onPress={() => void reviewMove()} />
    </Card>}
  </>;
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
    <Text style={styles.sectionTitle}>Programado para este día</Text>
    {day.has_plan ? <EntityCard
      actions={<>
        <EntityCardAction label="Opciones del plan diario" onPress={() => setPlanMenuVisible(true)}><Ellipsis color={tokens.color.textMuted} size={23} strokeWidth={2.2} /></EntityCardAction>
        {day.id != null ? <EntityCardAction label="Ver detalle del plan diario" onPress={() => router.push(`/program/days/${day.id}` as Href)} role="link"><ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} /></EntityCardAction> : null}
      </>}
      entity="dailyPlan"
      eyebrow="PLAN DIARIO"
      headingLink={day.id != null ? { label: "Ver detalle del plan diario", onPress: () => router.push(`/program/days/${day.id}` as Href) } : undefined}
      subtitle={day.source_program_name ?? undefined}
      title={day.plan_name}
    /> : null}
    <ActionSheetModal onRequestClose={() => setPlanMenuVisible(false)} visible={planMenuVisible}>
      <SafeAreaView edges={["left", "right"]} style={styles.planMenu}>
        <ActionSheetHeader entity="dailyPlan" onClose={() => setPlanMenuVisible(false)} title="Plan diario" />
        <View style={styles.planMenuContent}>
          {locked ? <InlineNotice>{past ? "Los días anteriores no se modifican." : "Este día ya tiene cumplimiento registrado y no se puede modificar."}</InlineNotice> : null}
          <ActionSheetActions>
            <ActionSheetAction disabled={locked} icon={Repeat2} label="Reemplazar plan diario" onPress={() => { setPlanMenuVisible(false); onSelectItem("replace"); }} />
            {day.source_kind === "manual" && day.calendar_date > localToday ? <ActionSheetAction disabled={locked} icon={MoveRight} label="Mover plan diario" onPress={() => { setPlanMenuVisible(false); onSelectItem("move"); }} /> : null}
            <ActionSheetAction destructive disabled={locked} icon={Trash2} label="Eliminar plan del calendario" onPress={() => { setPlanMenuVisible(false); onSelectItem("remove"); }} />
          </ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
    {day.commitments?.map((commitment) => {
      const presentation = commitmentPresentation[commitment.kind];
      const CommitmentIcon = presentation.icon;
      const hasFoodList = commitment.kind !== "training" && commitment.food_period_start && commitment.food_period_end;
      return <View key={commitment.id}>
        <Card accent={presentation.color}>
          <View style={styles.assignmentHeading}>
            <CommitmentIcon color={presentation.color} size={19} strokeWidth={2} />
            <Text style={styles.assignmentEyebrow}>{commitmentDayTitle[commitment.kind].toUpperCase()}</Text>
            {hasFoodList ? <Paperclip accessibilityLabel="Lista de alimentos adjunta" color={tokens.color.textMuted} size={17} /> : null}
          </View>
          <Pressable accessibilityLabel={`Ver detalle de ${commitmentDayTitle[commitment.kind]}`} accessibilityRole="link" onPress={() => router.push(`/calendar/commitments/${commitment.id}?date=${day.calendar_date}` as Href)}><Text style={styles.assignmentTitle}>{commitmentDayTitle[commitment.kind]}</Text></Pressable>
          {commitment.note ? <Text style={styles.assignmentMeta}>{commitment.note}</Text> : null}
          {hasFoodList ? <View style={styles.assignmentChips}>
            <Chip backgroundColor={`${tokens.color.food}1A`} borderColor={tokens.color.food} label={`${commitment.foods.length} ${commitment.foods.length === 1 ? "alimento" : "alimentos"}`} textColor={tokens.color.textMain} />
            <Chip backgroundColor={`${tokens.color.dailyPlan}1A`} borderColor={tokens.color.dailyPlan} label={`${commitment.food_plans_count} ${commitment.food_plans_count === 1 ? "plan" : "planes"}`} textColor={tokens.color.textMain} />
          </View> : null}
          <View style={styles.assignmentActions}><EntityCardAction label={`Ver detalle de ${commitmentDayTitle[commitment.kind]}`} onPress={() => router.push(`/calendar/commitments/${commitment.id}?date=${day.calendar_date}` as Href)} role="link"><ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} /></EntityCardAction></View>
        </Card>
      </View>;
    })}
    {!day.has_plan && !day.commitments?.length ? <InlineNotice>No hay planes ni compromisos programados para este día.</InlineNotice> : null}
    {!day.has_plan ? <Card>
      <Text style={styles.title}>Asignar plan diario</Text>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {locked ? <InlineNotice>{past ? "Los días anteriores no se modifican. Su evidencia permanece en el historial." : "Este día ya tiene cumplimiento registrado y no se puede sustituir ni mover."}</InlineNotice> : (
        <View style={styles.group}>
          <SearchField onChangeText={setSearch} onClear={() => setSearch("")} placeholder="Buscar plan de biblioteca" value={search} />
          {plans.map((plan) => (
            <Pressable accessibilityLabel={`Asignar ${plan.name}`} accessibilityRole="button" disabled={busy} key={plan.id} onPress={() => {
              void assignPlanFromChoice(plan.id, plan.name);
            }} style={styles.planRow}>
              <Text style={styles.planName}>{plan.name}</Text>
              <Text style={styles.planAction}>Elegir</Text>
            </Pressable>
          ))}
        </View>
      )}
    </Card> : null}
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
  assignmentActions: { alignItems: "flex-end" },
  assignmentChips: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.xs },
  assignmentEyebrow: { color: tokens.color.textMuted, flex: 1, fontSize: 11, fontWeight: "600" },
  assignmentHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  assignmentMeta: { color: tokens.color.textMuted, fontSize: 13 },
  assignmentTitle: { color: tokens.color.textMain, fontSize: 18, fontWeight: "700" },
  group: { gap: tokens.spacing.md },
  helper: { color: tokens.color.textMuted, fontSize: 13 },
  historyMeta: { color: tokens.color.textMuted, fontSize: 12 },
  planAction: { color: tokens.color.interactivePrimary, fontSize: 13 },
  planName: { color: tokens.color.textMain, flex: 1, fontSize: 15 },
  planRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, paddingVertical: tokens.spacing.sm },
  planMenu: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 },
  planMenuContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  sectionTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: "700" },
  title: { color: tokens.color.textMain, fontSize: 18, fontWeight: "600" },
});
