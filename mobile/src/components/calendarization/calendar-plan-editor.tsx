import * as Crypto from "expo-crypto";
import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarDay, CalendarDayDetailData, CalendarDayHistoryData, LibraryPageData } from "@/api/types";
import { Button, Card, InlineNotice, NativeDateTimeField, SearchField } from "@/components/ui";
import { ConfirmationState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";

type ApiRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

export function CalendarPlanEditor({ apiRequest, day, localToday, onChanged, onClose }: {
  apiRequest: ApiRequest;
  day: CalendarDay;
  localToday: string;
  onChanged(): Promise<void> | void;
  onClose(): void;
}) {
  const [mode, setMode] = useState<"choose" | "move" | "confirm-move" | "confirm-assign" | "confirm-remove">("choose");
  const [search, setSearch] = useState("");
  const [plans, setPlans] = useState<LibraryPageData["items"]>([]);
  const [history, setHistory] = useState<CalendarDayHistoryData["items"]>([]);
  const [selectedPlan, setSelectedPlan] = useState<{ id: number; name: string } | null>(null);
  const [targetDate, setTargetDate] = useState(day.calendar_date);
  const [targetPlan, setTargetPlan] = useState<CalendarDayDetailData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const timeout = setTimeout(() => {
      void apiRequest<LibraryPageData>(`/api/v1/library/daily-plans?limit=50&search=${encodeURIComponent(search)}`)
        .then((result) => { if (active) setPlans(result.items); })
        .catch((nextError) => { if (active) setError(userFacingError(nextError)); });
    }, search ? 200 : 0);
    return () => { active = false; clearTimeout(timeout); };
  }, [apiRequest, search]);
  useEffect(() => {
    let active = true;
    void apiRequest<CalendarDayHistoryData>(`/api/v1/calendar/days/${day.calendar_date}/history`)
      .then((result) => { if (active) setHistory(result.items); })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); });
    return () => { active = false; };
  }, [apiRequest, day.calendar_date]);

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

  return (
    <Card>
      <Text style={styles.title}>Planificar {day.calendar_date}</Text>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {locked ? <InlineNotice>{past ? "Los días anteriores no se modifican. Su evidencia permanece en el historial." : "Este día ya tiene cumplimiento registrado y no se puede sustituir ni mover."}</InlineNotice> : mode === "confirm-assign" && selectedPlan ? (
        <ConfirmationState
          busy={busy}
          confirmLabel="Reemplazar plan"
          message={`El plan “${day.plan_name}” conservará su snapshot e historial. “${selectedPlan.name}” quedará vigente para esta fecha.`}
          onCancel={() => setMode("choose")}
          onConfirm={() => void assign(true)}
          title="¿Reemplazar el plan de esta fecha?"
        />
      ) : mode === "confirm-remove" ? (
        <ConfirmationState
          busy={busy}
          confirmLabel="Quitar de esta fecha"
          message="La asignación dejará de estar vigente, pero su snapshot y los registros anteriores permanecerán en el historial."
          onCancel={() => setMode("choose")}
          onConfirm={() => void remove()}
          title="¿Quitar este plan?"
        />
      ) : mode === "confirm-move" ? (
        <ConfirmationState
          busy={busy}
          confirmLabel="Confirmar movimiento"
          message={targetPlan?.has_plan
            ? `“${day.plan_name}” pasará a ${targetDate}. El plan “${targetPlan.plan_name}” conservará su snapshot e historial, pero dejará de estar vigente.`
            : `“${day.plan_name}” pasará a ${targetDate}. La fecha original quedará libre y su snapshot permanecerá en el historial.`}
          onCancel={() => setMode("move")}
          onConfirm={() => void move()}
          title="¿Mover este plan?"
        />
      ) : mode === "move" ? (
        <View style={styles.group}>
          <NativeDateTimeField label="Nueva fecha" minimumValue={localToday} mode="date" onChange={setTargetDate} value={targetDate} />
          <Button disabled={busy || targetDate < localToday || targetDate === day.calendar_date} label="Revisar movimiento" loading={busy} onPress={() => void reviewMove()} />
          <Button label="Volver" onPress={() => setMode("choose")} variant="secondary" />
        </View>
      ) : (
        <View style={styles.group}>
          <SearchField onChangeText={setSearch} onClear={() => setSearch("")} placeholder="Buscar plan de biblioteca" value={search} />
          {plans.map((plan) => (
            <Pressable accessibilityLabel={`Asignar ${plan.name}`} accessibilityRole="button" disabled={busy} key={plan.id} onPress={() => {
              setSelectedPlan({ id: plan.id, name: plan.name });
              if (day.has_plan) setMode("confirm-assign");
              else void assignPlanFromChoice(plan.id, plan.name);
            }} style={styles.planRow}>
              <Text style={styles.planName}>{plan.name}</Text>
              <Text style={styles.planAction}>Elegir</Text>
            </Pressable>
          ))}
          {day.has_plan ? <Button label="Quitar plan de esta fecha" onPress={() => setMode("confirm-remove")} variant="secondary" /> : null}
          {day.has_plan && day.source_kind === "manual" && day.calendar_date > localToday
            ? <Button label="Mover este plan" onPress={() => { setTargetDate(day.calendar_date); setMode("move"); }} variant="secondary" /> : null}
        </View>
      )}
      {history.length > 0 ? <View style={styles.group}>
        <Text style={styles.historyTitle}>Historial de esta fecha</Text>
        {history.map((version) => <View key={version.id} style={styles.historyRow}>
          <Text style={styles.planName}>{version.plan_name || "Día sin plan"}</Text>
          <Text style={styles.historyMeta}>
            {version.assignment_state === "current" ? "Vigente" : version.assignment_state === "removed" ? "Quitado" : "Sustituido"}
            {version.source_program_name ? ` · ${version.source_program_name}` : " · Plan individual"}
            {version.execution_events ? ` · ${version.execution_events} registros` : ""}
          </Text>
        </View>)}
      </View> : null}
      <Button label="Cerrar" onPress={onClose} variant="secondary" />
    </Card>
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
  group: { gap: tokens.spacing.md },
  historyMeta: { color: tokens.color.textMuted, fontSize: 12 },
  historyRow: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, gap: 3, paddingTop: tokens.spacing.sm },
  historyTitle: { color: tokens.color.textMain, fontSize: 15, fontWeight: "600" },
  planAction: { color: tokens.color.interactivePrimary, fontSize: 13 },
  planName: { color: tokens.color.textMain, flex: 1, fontSize: 15 },
  planRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, paddingVertical: tokens.spacing.sm },
  title: { color: tokens.color.textMain, fontSize: 18, fontWeight: "600" },
});
