import assert from "node:assert/strict";
import test from "node:test";

import { consumeAssistantQuickChatMessage, stageAssistantQuickChatMessage } from "../src/components/assistant/assistant-quick-chat-draft";
import { nearestQuickChatHorizontalEdge, quickChatHorizontalEdgeForRelease } from "../src/components/assistant/assistant-quick-chat-position";

test("quick-chat drafts stay in memory and are consumed only once", () => {
  stageAssistantQuickChatMessage("  Ayúdame con mi desayuno  ");
  assert.equal(consumeAssistantQuickChatMessage(), "Ayúdame con mi desayuno");
  assert.equal(consumeAssistantQuickChatMessage(), null);
  stageAssistantQuickChatMessage("   ");
  assert.equal(consumeAssistantQuickChatMessage(), null);
});

test("the floating assistant button snaps to the nearest horizontal edge", () => {
  assert.equal(nearestQuickChatHorizontalEdge(-240, -300, 8), -300);
  assert.equal(nearestQuickChatHorizontalEdge(-40, -300, 8), 8);
  assert.equal(nearestQuickChatHorizontalEdge(-500, -300, 8), -300);
  assert.equal(nearestQuickChatHorizontalEdge(100, -300, 8), 8);
  assert.equal(quickChatHorizontalEdgeForRelease(120, 390, -300, 8), -300);
  assert.equal(quickChatHorizontalEdgeForRelease(270, 390, -300, 8), 8);
});
