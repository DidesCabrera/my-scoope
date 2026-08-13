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

test("assistant messages render bounded roles instead of raw conversation payloads", async () => {
  const conversation = await readFile(path.resolve(process.cwd(), "src/components/assistant/chat-conversation.tsx"), "utf8");
  assert.match(conversation, /message\.role === "user"/);
  assert.match(conversation, /message\.text/);
  assert.doesNotMatch(conversation, /conversation_payload/);
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
