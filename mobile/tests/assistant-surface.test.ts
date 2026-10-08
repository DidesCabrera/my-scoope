import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const source = (file: string) => readFile(path.resolve(process.cwd(), file), "utf8");

test("the assistant surface resumes server-reported jobs without resubmitting turns", async () => {
  const screen = await source("src/components/assistant/assistant-chat-screen.tsx");
  assert.match(screen, /pending_turn/);
  assert.match(screen, /pending_new_turn/);
  assert.match(screen, /pollAsyncJob<AITurnResultData>/);
  assert.match(screen, /AbortController/);
  assert.match(screen, /if \(!normalized \|\| sending \|\| pending\) return/);
  assert.ok(screen.includes("setOptimisticMessage({"));
  assert.ok(screen.includes("visibleMessages"));
  assert.ok(screen.includes("setMessage(normalized)"));
  assert.match(screen, /router\.replace\(`\/assistant\/\$\{result\.chat_id\}`/);
});

test("long assistant conversations keep the message composer inside the viewport", async () => {
  const screen = await source("src/components/assistant/assistant-chat-screen.tsx");
  assert.ok(screen.includes("style={styles.conversationScroll}"));
  assert.ok(screen.includes("conversationScroll: { flex: 1 }"));
  assert.ok(screen.includes("paddingBottom: tokens.spacing.xxl * 4"));
  assert.ok(screen.includes("screen: { flex: 1,"));
});

test("the assistant composer centers available credits without moving for the character counter", async () => {
  const composer = await source("src/components/assistant/chat-composer.tsx");
  assert.ok(composer.includes('composer: { alignItems: "flex-end", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.card'));
  assert.ok(composer.includes('justifyContent: "center"'));
  assert.ok(composer.includes('textAlign: "center"'));
  assert.ok(composer.includes('position: "absolute", right: tokens.spacing.sm'));
});

test("the assistant composer vertically centers its resting message input", async () => {
  const composer = await source("src/components/assistant/chat-composer.tsx");
  assert.match(composer, /textAlignVertical="center"/);
  assert.match(composer, /input: \{[^}]*minHeight: 38[^}]*paddingVertical: 0/);
  assert.doesNotMatch(composer, /textAlignVertical="top"|paddingTop: 8|paddingBottom: 8/);
});

test("the assistant send button only looks disabled when there are no credits", async () => {
  const composer = await source("src/components/assistant/chat-composer.tsx");
  const screen = await source("src/components/assistant/assistant-chat-screen.tsx");
  assert.ok(composer.includes("outOfCredits && styles.sendButtonDisabled"));
  assert.ok(composer.includes("outOfCredits ? tokens.color.textSubtle : tokens.color.surfaceApp"));
  assert.ok(screen.includes("outOfCredits={outOfCredits}"));
  assert.ok(!composer.includes("sendDisabled && styles.sendButtonDisabled"));
});

test("assistant messages render bounded roles instead of raw conversation payloads", async () => {
  const conversation = await source("src/components/assistant/chat-conversation.tsx");
  assert.match(conversation, /message\.role === "user"/);
  assert.match(conversation, /message\.text/);
  assert.ok(conversation.includes("<AssistantMessageText>{message.text}</AssistantMessageText>"));
  assert.ok(conversation.includes("index === messages.length - 1 ? receivedTime(message.created_at) : null"));
  assert.ok(conversation.includes("Recibido a las ${time}"));
  assert.doesNotMatch(conversation, /conversation_payload/);
});

test("typed assistant cards navigate to trusted product surfaces and gate mutations", async () => {
  const conversation = await source("src/components/assistant/chat-conversation.tsx");
  const screen = await source("src/components/assistant/assistant-chat-screen.tsx");
  const comparator = await source("src/app/comparator/index.tsx");
  assert.match(conversation, /card\.type === "proposal_review"/);
  assert.ok(conversation.includes("<ProposalListCard"));
  assert.ok(conversation.includes("proposal={proposal}"));
  assert.ok(conversation.includes("apiRequest<ProposalDetail>(`/api/v1/proposals/${proposalId}`)"));
  assert.ok(conversation.includes("<LibraryCard apiRequest={apiRequest} interactive={false}"));
  assert.ok(conversation.includes("/api/v1/library/${librarySegments[card.resource]}/${card.item_id}"));
  assert.ok(conversation.includes("<SavedComparisonListCard item={item}"));
  assert.ok(comparator.includes("<SavedComparisonListCard item={item}"));
  assert.match(conversation, /card\.type === "saved_comparison"/);
  assert.match(conversation, /card\.type === "prepared_action"/);
  assert.ok(conversation.includes('<PersonalRecordCard'));
  assert.ok(conversation.includes('card.type === "profile_draft" || card.type === "preference_draft"'));
  assert.ok(conversation.includes('card.type === "preference_draft" && card.can_commit'));
  assert.match(conversation, /\/comparator\/saved\//);
  assert.match(conversation, /\/proposals\//);
  assert.match(screen, /Alert\.alert/);
  assert.match(screen, /\/ai\/prepared-actions\/\$\{actionId\}\/\$\{mode\}/);
  assert.match(screen, /\/ai\/chats\/\$\{chatId\}\/preferences\/commit/);
  assert.doesNotMatch(conversation, /preview\.before|preview\.after|arguments/);
});

test("personal record cards are registered in the UI gallery and reused by chat", async () => {
  const gallery = await source("src/app/dev/ui-gallery.tsx");
  const navigation = await source("src/components/dev/gallery-navigation.tsx");
  const recordGallery = await source("src/components/dev/personal-record-card-gallery.tsx");
  const conversation = await source("src/components/assistant/chat-conversation.tsx");

  assert.ok(navigation.includes('{ key: "personalRecords", label: "Fichas personales" }'));
  assert.ok(gallery.includes('<PersonalRecordCardGallery />'));
  for (const kind of ["body", "planning", "preferences", "metrics"]) {
    assert.ok(recordGallery.includes(`kind: "${kind}"`));
  }
  assert.ok(recordGallery.includes('<PersonalRecordCard'));
  assert.ok(conversation.includes('<PersonalRecordCard'));
  assert.ok(conversation.includes('profileRecordKinds'));
});

test("the UI gallery registers the same saved comparison card used by chat and comparisons", async () => {
  const gallery = await source("src/app/dev/ui-gallery.tsx");
  const comparisonGallery = await source("src/components/dev/saved-comparison-card-gallery.tsx");
  const conversation = await source("src/components/assistant/chat-conversation.tsx");
  const comparator = await source("src/app/comparator/index.tsx");

  assert.ok(gallery.includes("<SavedComparisonCardGallery"));
  assert.ok(comparisonGallery.includes("<SavedComparisonListCard"));
  assert.ok(comparisonGallery.includes("item={savedFoodComparison}"));
  assert.ok(conversation.includes("<SavedComparisonListCard item={item}"));
  assert.ok(comparator.includes("<SavedComparisonListCard item={item}"));
});
