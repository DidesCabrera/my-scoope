import * as Notifications from "expo-notifications";
import * as SecureStore from "expo-secure-store";

import type { CalendarCommitmentKind, CalendarOverviewData } from "@/api/calendar-types";

export type CommitmentReminderSettings = Record<CalendarCommitmentKind, boolean>;

export const defaultCommitmentReminderSettings: CommitmentReminderSettings = {
  shopping: false,
  cooking: false,
  training: false,
  nutritionist: false,
};

const SETTINGS_KEY = "my-scoope.commitment-reminders.v1";
const OWNER = "my-scoope-commitments";

export async function loadCommitmentReminderSettings(): Promise<CommitmentReminderSettings> {
  const raw = await SecureStore.getItemAsync(SETTINGS_KEY);
  if (!raw) return defaultCommitmentReminderSettings;
  try { return { ...defaultCommitmentReminderSettings, ...JSON.parse(raw) }; }
  catch { return defaultCommitmentReminderSettings; }
}

export async function saveCommitmentReminderSettings(settings: CommitmentReminderSettings): Promise<void> {
  await SecureStore.setItemAsync(SETTINGS_KEY, JSON.stringify(settings), { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY });
}

export async function syncCommitmentReminders(settings: CommitmentReminderSettings, apiRequest: <T>(path: string, init?: RequestInit) => Promise<T>): Promise<number> {
  const scheduled = await Notifications.getAllScheduledNotificationsAsync();
  await Promise.all(scheduled.filter((item) => item.content.data?.owner === OWNER).map((item) => Notifications.cancelScheduledNotificationAsync(item.identifier)));
  if (!Object.values(settings).some(Boolean)) return 0;
  let permission = await Notifications.getPermissionsAsync();
  if (!permission.granted && permission.canAskAgain) permission = await Notifications.requestPermissionsAsync({ ios: { allowAlert: true, allowBadge: false, allowSound: true } });
  if (!permission.granted) return 0;
  const overview = await apiRequest<CalendarOverviewData>("/api/v1/calendar?days=62");
  const now = new Date();
  let count = 0;
  for (const day of overview.days) for (const commitment of day.commitments ?? []) {
    if (!settings[commitment.kind]) continue;
    const date = new Date(`${commitment.calendar_date}T09:00:00`);
    if (date <= now) continue;
    await Notifications.scheduleNotificationAsync({
      identifier: `commitment-${commitment.id}`,
      content: { title: "My Scoope", body: `Hoy: ${commitment.kind === "shopping" ? "hacer compras" : commitment.kind === "cooking" ? "cocinar" : commitment.kind === "training" ? "entrenar" : "nutricionista"}`, data: { owner: OWNER, url: `/calendar/commitments/${commitment.id}?date=${commitment.calendar_date}` }, sound: "default" },
      trigger: { type: Notifications.SchedulableTriggerInputTypes.DATE, date },
    });
    count += 1;
  }
  return count;
}
