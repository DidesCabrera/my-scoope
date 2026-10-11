import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("program activation loads its dedicated lightweight projection", async () => {
  const screen = await readFile(path.resolve(process.cwd(), "src/app/program/activate.tsx"), "utf8");

  assert.match(screen, /apiRequest<CalendarizationProgramOptionsData>\("\/api\/v1\/library\/programs\/calendarization-options\?limit=100"\)/);
  assert.match(screen, /program\.weeks_count/);
  assert.match(screen, /program\.filled_days_count/);
  assert.match(screen, /program\.foods_count/);
  assert.match(screen, /programDailyMetricData\(program\.weeks\)/);
  assert.match(screen, /nextError instanceof MobileApiError[^\n]*!\[404, 422\]\.includes\(nextError\.status\)/);
  assert.match(screen, /legacyPage\.items\.filter\(\(program\) => program\.can_calendarize\)\.map\(legacyCalendarizationOption\)/);
  assert.doesNotMatch(screen, /metricData=\{program\.panel/);
});

test("program activation detects timezone and uses aligned consent-style notification toggles", async () => {
  const screen = await readFile(path.resolve(process.cwd(), "src/app/program/activate.tsx"), "utf8");

  assert.match(screen, /Intl\.DateTimeFormat\(\)\.resolvedOptions\(\)\.timeZone/);
  assert.match(screen, /setTimezoneName\(detectedTimezone\(profile\?\.timezone_name\)\)/);
  assert.doesNotMatch(screen, /Zona horaria automática|Zona horaria IANA|timezoneDetail/);
  assert.doesNotMatch(screen, /label="Zona horaria IANA"/);
  assert.match(screen, /function NotificationToggle/);
  assert.match(screen, /<Text style=\{styles\.notificationLabel\}>\{label\}<\/Text>[\s\S]*<SystemSwitch accessibilityLabel=\{label\}/);
  assert.doesNotMatch(screen, /notificationDetail|detail="Recibe un aviso/);
  assert.doesNotMatch(screen, /<Card accent=\{tokens\.color\.program\}>/);
  assert.match(screen, /const \[meals, setMeals\] = useState<Toggle>\("on"\)/);
  assert.match(screen, /style=\{styles\.dailyNotificationBlock\}[\s\S]*label="Aviso inicial del plan diario"[\s\S]*\{daily === "on" \? <NativeDateTimeField hideLabel label="Hora del aviso diario"/);
  assert.ok(screen.indexOf('label="Aviso inicial del plan diario"') < screen.indexOf('label="Hora del aviso diario"'));
});

test("program cards omit creator metadata and configuration card has no accent border", async () => {
  const screen = await readFile(path.resolve(process.cwd(), "src/app/program/activate.tsx"), "utf8");
  const programCard = await readFile(path.resolve(process.cwd(), "src/components/libraries/program-child-card.tsx"), "utf8");

  assert.doesNotMatch(screen, /<Card accent=\{tokens\.color\.program\}>/);
  assert.doesNotMatch(programCard, /CircleUserRound|Creado por|ownerText|owner:/);
  assert.match(programCard, /footer: \{[^}]*justifyContent: "flex-end"/);
});

test("program selection uses the shared white action chip and the selected card has no change action", async () => {
  const screen = await readFile(path.resolve(process.cwd(), "src/app/program/activate.tsx"), "utf8");
  const programCard = await readFile(path.resolve(process.cwd(), "src/components/libraries/program-child-card.tsx"), "utf8");

  assert.match(screen, /openActionLabel="Seleccionar"/);
  assert.doesNotMatch(screen, /Cambiar selección/);
  assert.match(programCard, /openActionLabel\s*\? <Text style=\{styles\.actionButtonLabel\}>\{openActionLabel\}<\/Text>[\s\S]*: <ChevronRight/);
  assert.match(programCard, /actionButtonLabeled: \{[^}]*backgroundColor: tokens\.color\.textMain[^}]*borderRadius: tokens\.radius\.pill[^}]*minHeight: 38[^}]*minWidth: 112/);
  assert.match(programCard, /actionButtonLabel: \{[^}]*color: tokens\.color\.surfaceApp[^}]*fontWeight: "800"/);
});
