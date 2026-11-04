import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { consumeAssistantQuickChatMessage, stageAssistantQuickChatMessage } from "../src/components/assistant/assistant-quick-chat-draft";
import { nearestQuickChatHorizontalEdge, quickChatHorizontalEdgeForRelease } from "../src/components/assistant/assistant-quick-chat-position";

const source = (file: string) => readFile(path.resolve(process.cwd(), file), "utf8");

test("quick-chat drafts stay in memory and are consumed only once", () => {
  stageAssistantQuickChatMessage("  Ayúdame con mi desayuno  ");
  assert.equal(consumeAssistantQuickChatMessage(), "Ayúdame con mi desayuno");
  assert.equal(consumeAssistantQuickChatMessage(), null);
  stageAssistantQuickChatMessage("   ");
  assert.equal(consumeAssistantQuickChatMessage(), null);
});

test("the global assistant launcher focuses its input and submits with the keyboard", async () => {
  const [launcher, navigation] = await Promise.all([
    source("src/components/assistant/assistant-quick-chat-launcher.tsx"),
    source("src/components/navigation/app-navigation.tsx"),
  ]);
  assert.match(navigation, /<AssistantQuickChatLauncher \/>/);
  assert.match(launcher, /autoFocus/);
  assert.match(launcher, /onSubmitEditing=\{submit\}/);
  assert.match(launcher, /returnKeyType="send"/);
  assert.match(launcher, /stageAssistantQuickChatMessage\(normalized\)/);
  assert.match(launcher, /router\.push\("\/assistant\/new" as Href\)/);
});

test("the quick-chat button reuses the credit gradient and assistant sparkles", async () => {
  const launcher = await source("src/components/assistant/assistant-quick-chat-launcher.tsx");
  assert.match(launcher, /LinearGradient id="assistant-quick-chat-macros"/);
  assert.match(launcher, /LinearGradient id="assistant-quick-chat-header-macros"/);
  assert.match(launcher, /tokens\.color\.protein[\s\S]*tokens\.color\.carbs[\s\S]*tokens\.color\.fat/);
  assert.match(launcher, /<Sparkles color=\{tokens\.color\.surfaceApp\} size=\{25\}/);
});

test("the floating assistant button can be dragged without losing tap behavior", async () => {
  const launcher = await source("src/components/assistant/assistant-quick-chat-launcher.tsx");
  assert.match(launcher, /PanResponder\.create/);
  assert.match(launcher, /onMoveShouldSetPanResponder:[\s\S]*Math\.hypot\(gesture\.dx, gesture\.dy\) > 4/);
  assert.match(launcher, /onPress=\{open\}/);
  assert.match(launcher, /minimumX:/);
  assert.match(launcher, /maximumX:/);
  assert.match(launcher, /minimumY:/);
  assert.match(launcher, /maximumY:/);
  assert.match(launcher, /Animated\.spring\(buttonOffset/);
  assert.match(launcher, /buttonOffset\.stopAnimation\(\);[\s\S]*buttonOffset\.extractOffset\(\)/);
  assert.match(launcher, /quickChatHorizontalEdgeForRelease\(releaseX, width, dragBounds\.minimumX, dragBounds\.maximumX\)/);
});

test("the floating assistant button snaps to the nearest horizontal edge", () => {
  assert.equal(nearestQuickChatHorizontalEdge(-240, -300, 8), -300);
  assert.equal(nearestQuickChatHorizontalEdge(-40, -300, 8), 8);
  assert.equal(nearestQuickChatHorizontalEdge(-500, -300, 8), -300);
  assert.equal(nearestQuickChatHorizontalEdge(100, -300, 8), 8);
  assert.equal(quickChatHorizontalEdgeForRelease(120, 390, -300, 8), -300);
  assert.equal(quickChatHorizontalEdgeForRelease(270, 390, -300, 8), 8);
});

test("account settings control whether the floating assistant button is shown", async () => {
  const [layout, launcher, navigation, preferences, settings] = await Promise.all([
    source("src/app/_layout.tsx"),
    source("src/components/assistant/assistant-quick-chat-launcher.tsx"),
    source("src/components/navigation/app-navigation.tsx"),
    source("src/components/assistant/assistant-quick-chat-preferences.tsx"),
    source("src/app/settings.tsx"),
  ]);
  const personalRecordsEntry = navigation.indexOf("<PersonalRecordsSidebarEntry weightKg={currentWeightKg} />");
  const settingsEntry = navigation.indexOf('href: "/settings", icon: SettingsIcon, label: "Settings"');
  assert.ok(personalRecordsEntry >= 0 && settingsEntry > personalRecordsEntry);
  assert.match(layout, /<AssistantQuickChatPreferencesProvider><AppNavigationProvider>/);
  assert.match(preferences, /myscoope\.assistant\.quick-chat\.preferences\.v1/);
  assert.match(preferences, /showFloatingButton: value/);
  assert.match(launcher, /preferencesReady[\s\S]*showFloatingButton/);
  assert.match(settings, /Mostrar botón flotante de asistente/);
  assert.match(settings, /<SystemSwitch[\s\S]*value=\{showFloatingButton\}/);
});

test("the quick-chat prompt uses the standard action-sheet aesthetic without form buttons", async () => {
  const launcher = await source("src/components/assistant/assistant-quick-chat-launcher.tsx");
  assert.match(launcher, /<ActionSheetModal onRequestClose=\{close\} visible=\{visible\}>/);
  assert.match(launcher, /<ActionSheetHeader iconNode=\{<AssistantGradientIcon \/>\} onClose=\{close\} title="Pregunta al Asistente" \/>/);
  assert.match(launcher, /<Text style=\{styles\.inputLabel\}>Mensaje<\/Text>/);
  assert.match(launcher, /paddingBottom: 10, paddingTop: tokens\.spacing\.compact/);
  assert.doesNotMatch(launcher, /Guardar nombre|label="Volver"/);
});

test("a staged quick-chat message opens the conversation and sends once", async () => {
  const [route, screen] = await Promise.all([
    source("src/app/assistant/new.tsx"),
    source("src/components/assistant/assistant-chat-screen.tsx"),
  ]);
  assert.match(route, /useState\(consumeAssistantQuickChatMessage\)/);
  assert.match(route, /initialMessage=\{initialMessage\}/);
  assert.match(screen, /const initialMessageRef = useRef\(normalizedInitialMessage\)/);
  assert.match(screen, /initialMessageRef\.current = null;\s*void send\(initialDraft\)/);
});
