import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("the assistant surface resumes server-reported jobs without resubmitting turns", async () => {
  const screen = await readFile(path.resolve(process.cwd(), "src/components/assistant/assistant-chat-screen.tsx"), "utf8");
  assert.match(screen, /pending_turn/);
  assert.match(screen, /pending_new_turn/);
  assert.match(screen, /pollAsyncJob<AITurnResultData>/);
  assert.match(screen, /AbortController/);
  assert.match(screen, /if \(!normalized \|\| sending \|\| pending\) return/);
  assert.match(screen, /router\.replace\(`\/assistant\/\$\{result\.chat_id\}`/);
});

test("assistant conversations use the global back header with the chat list as fallback", async () => {
  const screen = await readFile(path.resolve(process.cwd(), "src/components/assistant/assistant-chat-screen.tsx"), "utf8");
  assert.match(screen, /useHeaderPresentation/);
  assert.match(screen, /fallback: "\/assistant",[\s\S]*mode: "back"/);
  assert.match(screen, /title: chat\?\.title \?\? \(chatId \? "Conversación" : "Nuevo chat"\)/);
  assert.match(screen, /<Screen contentStyle=\{styles\.screen\} headerMode="preserve" scroll=\{false\}>/);
});

test("assistant messages keep only user turns in bubbles and give assistant content full width", async () => {
  const conversation = await readFile(path.resolve(process.cwd(), "src/components/assistant/chat-conversation.tsx"), "utf8");
  assert.match(conversation, /message\.role === "user"/);
  assert.match(conversation, /message\.text/);
  assert.match(conversation, /isUser \? styles\.userBubble : styles\.assistantContent/);
  assert.match(conversation, /assistantContent: \{ gap: tokens\.spacing\.md, width: "100%" \}/);
  assert.match(conversation, /userBubble:[\s\S]*maxWidth: "86%"/);
  assert.doesNotMatch(conversation, /assistantBubble/);
  assert.doesNotMatch(conversation, /conversation_payload/);
});

test("the assistant composer stays compact and exposes an icon send action", async () => {
  const composer = await readFile(path.resolve(process.cwd(), "src/components/assistant/chat-composer.tsx"), "utf8");
  assert.match(composer, /placeholder="Pregunta lo que quieras"/);
  assert.match(composer, /<ArrowUp/);
  assert.match(composer, /accessibilityLabel="Enviar"/);
  assert.doesNotMatch(composer, /<Button/);
});

test("a new chat stays reachable without credits and offers the existing purchase flow", async () => {
  const list = await readFile(path.resolve(process.cwd(), "src/app/assistant/index.tsx"), "utf8");
  const screen = await readFile(path.resolve(process.cwd(), "src/components/assistant/assistant-chat-screen.tsx"), "utf8");
  assert.match(list, /action: \{ icon: "plus", label: "Nuevo chat"/);
  assert.doesNotMatch(list, /disabled: !page\.availability\.is_available/);
  assert.match(screen, /availability\?\.available_credits === 0/);
  assert.match(screen, /disabled=\{unavailable \|\| outOfCredits \|\| Boolean\(pending\)\}/);
  assert.match(screen, /label="Comprar créditos"/);
  assert.match(screen, /router\.push\("\/subscription" as Href\)/);
  assert.match(list, /page\?\.availability\.available_credits === 0/);
  assert.match(list, /label="Comprar créditos"/);
  assert.match(list, /router\.push\("\/subscription" as Href\)/);
});

test("typed assistant cards navigate to trusted product surfaces and gate mutations", async () => {
  const conversation = await readFile(path.resolve(process.cwd(), "src/components/assistant/chat-conversation.tsx"), "utf8");
  const screen = await readFile(path.resolve(process.cwd(), "src/components/assistant/assistant-chat-screen.tsx"), "utf8");
  assert.match(conversation, /card\.type === "proposal_review"/);
  assert.match(conversation, /card\.type === "saved_comparison"/);
  assert.match(conversation, /card\.type === "prepared_action"/);
  assert.match(conversation, /\/comparator\/saved\//);
  assert.match(conversation, /\/proposals\//);
  assert.match(screen, /Alert\.alert/);
  assert.match(screen, /\/ai\/prepared-actions\/\$\{actionId\}\/\$\{mode\}/);
  assert.doesNotMatch(conversation, /preview\.before|preview\.after|arguments/);
});
