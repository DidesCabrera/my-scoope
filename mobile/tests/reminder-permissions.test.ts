import assert from "node:assert/strict";
import test from "node:test";
import { activateReminderPermission, type ReminderPermission } from "../src/notifications/reminder-permissions";

test("denied notifications open app settings rather than requesting a permission iOS will not show", async () => {
  const calls: string[] = [];
  await activateReminderPermission("denied", {
    openSettings: async () => { calls.push("settings"); },
    synchronize: async () => { calls.push("sync"); },
  });
  assert.deepEqual(calls, ["settings"]);
});

test("new permissions are requested once; granted permissions only synchronize", async () => {
  for (const permission of ["undetermined", "granted", "unavailable"] as ReminderPermission[]) {
    const calls: boolean[] = [];
    await activateReminderPermission(permission, {
      openSettings: async () => { assert.fail("Settings must not open"); },
      synchronize: async (requestPermission) => { calls.push(requestPermission); },
    });
    assert.deepEqual(calls, permission === "unavailable" ? [] : [permission === "undetermined"]);
  }
});
