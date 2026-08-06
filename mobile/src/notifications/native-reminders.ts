import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

import type { ApplePushRegistration, ReminderSettings } from "@/api/types";
import { appConfig } from "@/config/app-config";

const OWNER_KEY = "myscoope-calendarization";

export type NativeReminderState = {
  permission: "granted" | "denied" | "undetermined" | "unavailable";
  deliveryMode: "apns" | "local" | "none";
  scheduledCount: number;
};

type AuthenticatedRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

function permissionState(status: Notifications.NotificationPermissionsStatus): NativeReminderState["permission"] {
  if (status.granted) return "granted";
  const iosStatus = status.ios?.status;
  if (
    iosStatus === Notifications.IosAuthorizationStatus.AUTHORIZED
    || iosStatus === Notifications.IosAuthorizationStatus.PROVISIONAL
    || iosStatus === Notifications.IosAuthorizationStatus.EPHEMERAL
  ) return "granted";
  if (status.canAskAgain) return "undetermined";
  return "denied";
}

async function cancelOwnedNotifications(): Promise<void> {
  const scheduled = await Notifications.getAllScheduledNotificationsAsync();
  await Promise.all(
    scheduled
      .filter((notification) => notification.content.data?.owner === OWNER_KEY)
      .map((notification) => Notifications.cancelScheduledNotificationAsync(notification.identifier)),
  );
}

async function scheduleLocally(reminders: ReminderSettings): Promise<number> {
  await cancelOwnedNotifications();
  const now = Date.now();
  let scheduledCount = 0;
  for (const event of reminders.upcoming) {
    const date = new Date(event.scheduled_for_utc);
    if (!Number.isFinite(date.getTime()) || date.getTime() <= now + 5_000) continue;
    await Notifications.scheduleNotificationAsync({
      content: {
        title: "My Scoope",
        body: event.event_type === "daily_plan" ? "Tu plan diario está listo" : "Es hora de tu comida planificada",
        data: { owner: OWNER_KEY, eventKey: event.event_key, target: "/today" },
        sound: "default",
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.DATE,
        date,
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

export async function syncNativeReminders(
  reminders: ReminderSettings,
  apiRequest: AuthenticatedRequest,
  { requestPermission = false } = {},
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
