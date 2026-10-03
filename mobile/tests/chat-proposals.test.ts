import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const source = (file: string) => readFile(path.resolve(process.cwd(), file), "utf8");

test("an existing chat exposes its proposal history from the header menu", async () => {
  const chat = await source("src/components/assistant/assistant-chat-screen.tsx");
  const actions = await source("src/components/assistant/assistant-chat-actions.tsx");
  const proposals = await source("src/app/assistant/[id]/proposals.tsx");

  assert.match(chat, /icon: "more"/);
  assert.match(chat, /Acciones del chat/);
  assert.match(actions, /Ver propuestas del chat/);
  assert.match(chat, /`\/assistant\/\$\{chatId\}\/proposals`/);
  assert.match(proposals, /\/api\/v1\/ai\/chats\/\$\{chatId\}\/proposals\?limit=50/);
  assert.match(proposals, /<ProposalListCard/);
  assert.match(proposals, /fallback: `\/assistant\/\$\{chatId\}`/);
});

test("the assistant proposal list and chat proposal history share one card component", async () => {
  const assistant = await source("src/app/assistant/index.tsx");
  const card = await source("src/components/proposals/proposal-list-card.tsx");

  assert.match(assistant, /<ProposalListCard/);
  assert.match(card, /ProposalStatusBadge/);
  assert.match(card, /ProposalTypeBadge/);
  assert.match(card, /section="proposal"/);
});
