import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { CalendarDays } from "lucide-react-native";
import { useCallback, useState } from "react";
import { View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { CalendarDayDetailData, CalendarOverviewData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarPlanEditor } from "@/components/calendarization/calendar-plan-editor";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ActionSheetAction, ActionSheetActions, ActionSheetHeader, ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { InlineNotice, LoadingState, Screen } from "@/components/ui";
import { tokens } from "@/design/tokens";

type DaySection = "replace" | "remove" | "move" | "history" | null;

function dayLabel(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

export default function CalendarDayScreen() {
  const { date, section: initialSection } = useLocalSearchParams<{ date: string; section?: string }>();
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [day, setDay] = useState<CalendarDayDetailData | null>(null);
  const [localToday, setLocalToday] = useState("");
  const [sectionOverride, setSection] = useState<DaySection | undefined>(undefined);
  const section = sectionOverride === undefined ? (initialSection === "replace" ? "replace" : null) : sectionOverride;
  const [menuVisible, setMenuVisible] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      fallback: "/calendar" as Href,
      leadingAction: section == null ? undefined : { icon: "back", label: "Volver al día", onPress: () => setSection(null) },
      mode: "back",
      title: date ? dayLabel(date) : "Detalle del día",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [date, section, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return <Redirect href="/calendar" />;

  return <>
    <Screen headerMode="preserve">
      {loading && !day ? <LoadingState label="Abriendo esta fecha…" /> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {day && localToday ? <CalendarPlanEditor
        apiRequest={apiRequest}
        day={day}
        key={`${date}:${section ?? "list"}`}
        localToday={localToday}
        onChanged={load}
        onClose={() => router.back()}
        onSelectItem={setSection}
        selectedItem={section}
      /> : null}
    </Screen>
    <ActionSheetModal onRequestClose={() => setMenuVisible(false)} visible={menuVisible}>
      <SafeAreaView edges={["left", "right"]} style={{ backgroundColor: tokens.color.surfaceCard, flexShrink: 1 }}>
        <ActionSheetHeader icon={CalendarDays} onClose={() => setMenuVisible(false)} title="Esta fecha" />
        <View style={{ padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl }}>
          <ActionSheetActions>
            <ActionSheetAction icon={CalendarDays} label="Ver historial de esta fecha" onPress={() => { setMenuVisible(false); setSection("history"); }} />
          </ActionSheetActions>
        </View>
      </SafeAreaView>
    </ActionSheetModal>
  </>;
}
