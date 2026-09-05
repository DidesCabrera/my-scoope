import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

import type { ApplePushRegistration, CalendarizationStatus, ReminderSettings, TodayData } from "@/api/types";
import { appConfig } from "@/config/app-config";
import {
  LOCAL_REMINDER_OWNER,
  localReminderEvents,
  localReminderIdentifier,
  shouldScheduleNativeReminders,
} from "@/notifications/reminder-schedule";

export type NativeReminderState = {
  permission: "granted" | "denied" | "undetermined" | "unavailable";
  deliveryMode: "apns" | "local" | "none";
  scheduledCount: number;
};

type AuthenticatedRequest = <T>(path: string, init?: RequestInit) => Promise<T>;
export type NativeReminderSyncOptions = { requestPermission?: boolean };

let nativeSyncQueue: Promise<void> = Promise.resolve();

function serializeNativeSync<T>(work: () => Promise<T>): Promise<T> {
  const result = nativeSyncQueue.then(work, work);
  nativeSyncQueue = result.then(() => undefined, () => undefined);
  return result;
}

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

function permissionState(status: Notifications.NotificationPermissionsStatus): NativeReminderState["permission"] {
  const iosStatus = status.ios?.status;
  if (
    iosStatus === Notifications.IosAuthorizationStatus.AUTHORIZED
    || iosStatus === Notifications.IosAuthorizationStatus.PROVISIONAL
    || iosStatus === Notifications.IosAuthorizationStatus.EPHEMERAL
  ) return "granted";
  if (iosStatus === Notifications.IosAuthorizationStatus.NOT_DETERMINED) return "undetermined";
  if (iosStatus === Notifications.IosAuthorizationStatus.DENIED) return "denied";
  if (status.granted) return "granted";
  if (status.canAskAgain) return "undetermined";
  return "denied";
}

async function cancelOwnedNotifications(): Promise<void> {
  const scheduled = await Notifications.getAllScheduledNotificationsAsync();
  await Promise.all(
    scheduled
      .filter((notification) => notification.content.data?.owner === LOCAL_REMINDER_OWNER)
      .map((notification) => Notifications.cancelScheduledNotificationAsync(notification.identifier)),
  );
}

async function scheduleLocally(reminders: ReminderSettings): Promise<number> {
  await cancelOwnedNotifications();
  let scheduledCount = 0;
  for (const event of localReminderEvents(reminders)) {
    await Notifications.scheduleNotificationAsync({
      identifier: localReminderIdentifier(event.event_key),
      content: {
        title: "My Scoope",
        body: event.event_type === "daily_plan" ? "Tu plan diario está listo" : "Es hora de tu comida planificada",
        data: { owner: LOCAL_REMINDER_OWNER, eventKey: event.event_key, target: "/today" },
        sound: "default",
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.DATE,
        date: event.scheduledAt,
      },
    });
    scheduledCount += 1;
  }
  return scheduledCount;
}

async function registerWithApns(apiRequest: AuthenticatedRequest): Promise<ApplePushRegistration | null> {
  if (Platform.OS !== "ios" || !Device.isDevice) return null;
  const nativeToken = await Notifications.getDevicePushTokenAsync();
  if (nativeToken.type !== "ios" || typeof nativeToken.data !== "string") return null;
  return apiRequest<ApplePushRegistration>("/api/v1/notifications/apple/device", {
    method: "PUT",
    body: JSON.stringify({
      device_token: nativeToken.data,
      environment: appConfig.apnsEnvironment,
    }),
  });
}

async function performNativeReminderSync(
  reminders: ReminderSettings,
  apiRequest: AuthenticatedRequest,
  { requestPermission = false }: NativeReminderSyncOptions = {},
): Promise<NativeReminderState> {
  if (Platform.OS !== "ios") {
    return { permission: "unavailable", deliveryMode: "none", scheduledCount: 0 };
  }

  let permissions = await Notifications.getPermissionsAsync();
  if (requestPermission && permissionState(permissions) === "undetermined") {
    permissions = await Notifications.requestPermissionsAsync({
      ios: { allowAlert: true, allowBadge: false, allowSound: true },
    });
  }
  const permission = permissionState(permissions);
  if (permission !== "granted") {
    await cancelOwnedNotifications();
    return { permission, deliveryMode: "none", scheduledCount: 0 };
  }

  try {
    const registration = await registerWithApns(apiRequest);
    if (registration?.delivery_mode === "apns") {
      await cancelOwnedNotifications();
      return { permission, deliveryMode: "apns", scheduledCount: 0 };
    }
  } catch {
    // A server or token-registration failure must not remove offline reminders.
  }

  const scheduledCount = await scheduleLocally(reminders);
  return { permission, deliveryMode: "local", scheduledCount };
}

export function syncNativeReminders(
  reminders: ReminderSettings,
  apiRequest: AuthenticatedRequest,
  options: NativeReminderSyncOptions = {},
): Promise<NativeReminderState> {
  return serializeNativeSync(() => performNativeReminderSync(reminders, apiRequest, options));
}

export function clearNativeReminders(): Promise<NativeReminderState> {
  return serializeNativeSync(async () => {
    if (Platform.OS !== "ios") {
      return { permission: "unavailable", deliveryMode: "none", scheduledCount: 0 };
    }
    const permission = permissionState(await Notifications.getPermissionsAsync());
    await cancelOwnedNotifications();
    return { permission, deliveryMode: "none", scheduledCount: 0 };
  });
}

export function syncNativeRemindersForProgram(
  reminders: ReminderSettings | null,
  status: CalendarizationStatus | null,
  apiRequest: AuthenticatedRequest,
  options: NativeReminderSyncOptions = {},
): Promise<NativeReminderState> {
  if (!reminders || !shouldScheduleNativeReminders(status)) return clearNativeReminders();
  return syncNativeReminders(reminders, apiRequest, options);
}

export async function refreshNativeReminders(
  apiRequest: AuthenticatedRequest,
  options: NativeReminderSyncOptions = {},
): Promise<NativeReminderState> {
  const today = await apiRequest<TodayData>("/api/v1/today");
  return syncNativeRemindersForProgram(today.reminders, today.calendarization?.status ?? null, apiRequest, options);
}
