import { type Href, Redirect, Stack, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { CalendarDays, ClipboardList, Pin, Trash2 } from "lucide-react-native";
import { useCallback, useState } from "react";
import { StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarDayDetailData, CalendarOverviewData } from "@/api/types";
import type { CalendarCommitment } from "@/api/calendar-types";
import { useSession } from "@/auth/session-context";
import { commitmentActionLabel, commitmentDayTitle, commitmentKinds, commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { CalendarPlanEditor } from "@/components/calendarization/calendar-plan-editor";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { InlineNotice, LoadingState, Screen, SectionPageHeader } from "@/components/ui";
import { ConfirmationState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";
import { loadCommitmentReminderSettings, syncCommitmentReminders } from "@/notifications/commitment-reminders";

type DaySection = "assign" | "replace" | "remove" | "move" | "history" | null;

function dayLabel(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

export default function CalendarDayScreen() {
  const { date, origin, section: initialSection } = useLocalSearchParams<{ date: string; origin?: string; section?: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [day, setDay] = useState<CalendarDayDetailData | null>(null);
  const [localToday, setLocalToday] = useState("");
  const [sectionOverride, setSection] = useState<DaySection | undefined>(undefined);
  const section = sectionOverride === undefined ? (initialSection === "assign" || initialSection === "replace" ? initialSection : null) : sectionOverride;
  const [addMenuVisible, setAddMenuVisible] = useState(false);
  const [menuVisible, setMenuVisible] = useState(false);
  const [commitmentToDelete, setCommitmentToDelete] = useState<CalendarCommitment | null>(null);
  const [deletingCommitment, setDeletingCommitment] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const title = "Plan del día";

  async function deleteCommitment() {
    if (!commitmentToDelete || deletingCommitment) return;
    setDeletingCommitment(true);
    setDeleteError(null);
    try {
      await apiRequest(`/api/v1/calendar/commitments/${commitmentToDelete.id}`, { method: "DELETE" });
      await load();
      setCommitmentToDelete(null);
      setMenuVisible(false);
      void loadCommitmentReminderSettings().then((settings) => syncCommitmentReminders(settings, apiRequest)).catch(() => undefined);
    } catch (nextError) {
      setDeleteError(userFacingError(nextError));
    } finally {
      setDeletingCommitment(false);
    }
  }

  const load = useCallback(async () => {
    if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return;
    setError(null);
    try {
      const [nextDay, overview] = await Promise.all([
        apiRequest<CalendarDayDetailData>(`/api/v1/calendar/days/${date}`),
        apiRequest<CalendarOverviewData>("/api/v1/calendar?days=1"),
      ]);
      setDay(nextDay);
      setLocalToday(overview.local_date);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, date]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      action: section == null ? { icon: "more", label: "Opciones de esta fecha", onPress: () => setMenuVisible(true) } : undefined,
      fallback: (origin === "home" ? "/today" : "/calendar") as Href,
      identityVisible: compactHeaderVisible,
      leadingAction: section == null ? undefined : { icon: "back", label: "Volver al día", onPress: () => setSection(null) },
      mode: "back",
      secondaryAction: section == null ? { icon: "plus", label: "Agregar a esta fecha", onPress: () => setAddMenuVisible(true) } : undefined,
      title,
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, origin, section, setHeaderPresentation, title]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return <Redirect href="/calendar" />;
  if (loading && !day) return <><Stack.Screen options={{ headerShown: false }} /><LoadingState headerVisible={false} label="Abriendo esta fecha…" /></>;

  return <>
    <Stack.Screen options={{ headerShown: true }} />
    <Screen headerMode="preserve" onHeaderVisibilityChange={setCompactHeaderVisible}>
      {section == null ? <SectionPageHeader icon={<Pin color={tokens.color.textMain} size={28} strokeWidth={1.8} />} section="calendarization" subtitle={dayLabel(date)} subtitleStyle={styles.dateSubtitle} title={title} /> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {day && localToday ? <CalendarPlanEditor
        apiRequest={apiRequest}
        day={day}
        key={`${date}:${section ?? "list"}`}
        localToday={localToday}
        onChanged={load}
        onClose={() => origin === "home" ? router.dismissTo("/today" as Href) : router.back()}
        onSelectItem={setSection}
        selectedItem={section}
      /> : null}
    </Screen>
    <ActionSheetModal onRequestClose={() => setAddMenuVisible(false)} visible={addMenuVisible}>
      <SafeAreaView edges={["left", "right"]} style={{ backgroundColor: tokens.color.surfaceCard, flexShrink: 1 }}>
        <ActionSheetHeader icon={CalendarDays} onClose={() => setAddMenuVisible(false)} title="Agregar a esta fecha" />
        <View style={{ padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl }}>
          <ActionSheetActions>
            <ActionSheetAction icon={ClipboardList} label={day?.has_plan ? "Reemplazar minuta diaria" : "Agregar minuta diaria"} onPress={() => { setAddMenuVisible(false); setSection(day?.has_plan ? "replace" : "assign"); }} />
            {commitmentKinds.map((kind) => <ActionSheetAction
              icon={commitmentPresentation[kind].icon}
              key={kind}
              label={commitmentActionLabel[kind]}
              onPress={() => {
                setAddMenuVisible(false);
                router.push(`/calendar/commitments?kind=${kind}&date=${date}${origin === "home" ? "&origin=home" : ""}` as Href);
              }}
            />)}
          </ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
    <ActionSheetModal onRequestClose={() => { setMenuVisible(false); setCommitmentToDelete(null); }} visible={menuVisible}>
      <SafeAreaView edges={["left", "right"]} style={{ backgroundColor: tokens.color.surfaceCard, flexShrink: 1 }}>
        <ActionSheetHeader icon={commitmentToDelete ? Trash2 : CalendarDays} onClose={() => { setMenuVisible(false); setCommitmentToDelete(null); }} title={commitmentToDelete ? "Eliminar compromiso" : "Esta fecha"} />
        <View style={{ padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl }}>
          {commitmentToDelete ? <>
            {deleteError ? <InlineNotice tone="error">{deleteError}</InlineNotice> : null}
            <ConfirmationState busy={deletingCommitment} confirmLabel="Eliminar compromiso" danger message={`Se eliminará ${commitmentDayTitle[commitmentToDelete.kind].toLowerCase()} del ${dayLabel(commitmentToDelete.calendar_date)}.`} onCancel={() => { setCommitmentToDelete(null); setDeleteError(null); }} onConfirm={() => void deleteCommitment()} title="¿Eliminar este compromiso?" />
          </> : <ActionSheetActions>
            <ActionSheetAction icon={CalendarDays} label="Ver historial de esta fecha" onPress={() => { setMenuVisible(false); setSection("history"); }} />
            {day?.has_plan ? <ActionSheetAction destructive disabled={day.calendar_date < localToday || day.has_execution} icon={Trash2} label="Eliminar minuta" onPress={() => { setMenuVisible(false); setSection("remove"); }} /> : null}
            {day?.commitments?.map((commitment) => <ActionSheetAction destructive icon={commitmentPresentation[commitment.kind].icon} key={commitment.id} label={`Eliminar ${commitmentPresentation[commitment.kind].label.toLowerCase()}`} onPress={() => { setDeleteError(null); setCommitmentToDelete(commitment); }} />)}
          </ActionSheetActions>}
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  </>;
}

const styles = StyleSheet.create({
  dateSubtitle: { fontSize: 17, fontWeight: "600", lineHeight: 23, marginTop: -4 },
});
