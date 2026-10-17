export type ReminderPermission = "granted" | "denied" | "undetermined" | "unavailable";

export async function activateReminderPermission(permission: ReminderPermission, actions: {
  openSettings(): Promise<void>;
  synchronize(requestPermission: boolean): Promise<void>;
}): Promise<void> {
  if (permission === "unavailable") return;
  if (permission === "denied") await actions.openSettings();
  else await actions.synchronize(permission === "undetermined");
}
