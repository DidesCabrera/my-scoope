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
  assert.match(actions, /Editar nombre/);
  assert.match(actions, /Guardar nombre/);
  assert.match(chat, /`\/assistant\/\$\{chatId\}\/proposals`/);
  assert.match(chat, /`\/api\/v1\/ai\/chats\/\$\{chatId\}\/name`/);
  assert.match(chat, /method: "PATCH"/);
  assert.match(chat, /setChat\(renamed\)/);
  assert.match(proposals, /\/api\/v1\/ai\/chats\/\$\{chatId\}\/proposals\?limit=50/);
  assert.match(proposals, /<ProposalListCard/);
  assert.match(proposals, /fallback: `\/assistant\/\$\{chatId\}`/);
});

test("the assistant proposal list and chat proposal history share one card component", async () => {
  const assistant = await source("src/app/assistant/index.tsx");
  const conversation = await source("src/components/assistant/chat-conversation.tsx");
  const gallery = await source("src/components/dev/proposal-gallery.tsx");
  const card = await source("src/components/proposals/proposal-list-card.tsx");

  assert.match(assistant, /<ProposalListCard/);
  assert.ok(conversation.includes("<ProposalListCard"));
  assert.ok(gallery.includes("<ProposalListCard"));
  assert.match(card, /ProposalStatusBadge/);
  assert.match(card, /ProposalTypeBadge/);
  assert.match(card, /section="proposal"/);
});

test("assistant chat cards reuse the credit bag top accent", async () => {
  const assistant = await source("src/app/assistant/index.tsx");
  const subscription = await source("src/app/subscription.tsx");

  assert.match(assistant, /function ChatCard[\s\S]*<Card accent=\{tokens\.color\.carbs\} style=\{styles\.chatCard\}>/);
  assert.match(subscription, /<Card accent=\{tokens\.color\.carbs\} key=\{configured\.product_id\}>/);
});

test("assistant chat cards replace the message count with a bottom detail action", async () => {
  const assistant = await source("src/app/assistant/index.tsx");

  assert.doesNotMatch(assistant, /chat\.message_count|mensajes · Continuar/);
  assert.match(assistant, /<Pressable[\s\S]*accessibilityLabel=\{detailLabel\}[\s\S]*accessibilityRole="link"[\s\S]*<Text numberOfLines=\{3\}/);
  assert.match(assistant, /<EntityCardActions>[\s\S]*<EntityCardAction label=\{detailLabel\} onPress=\{onPress\} role="link">[\s\S]*<ChevronRight color=\{tokens\.color\.textMuted\} size=\{23\} strokeWidth=\{2\.2\} \/>[\s\S]*<\/EntityCardActions>/);
  assert.match(assistant, /chatCard: \{ paddingBottom: tokens\.card\.innerPadding \}/);
});
