import { useLocalSearchParams } from "expo-router";
import { useState } from "react";

import { AssistantChatScreen } from "@/components/assistant/assistant-chat-screen";
import { consumeAssistantQuickChatMessage } from "@/components/assistant/assistant-quick-chat-draft";

export default function NewAssistantChatRoute() {
  const { comparisonId } = useLocalSearchParams<{ comparisonId?: string }>();
  const [initialMessage] = useState(consumeAssistantQuickChatMessage);
  return <AssistantChatScreen chatId={null} comparisonId={Number(comparisonId || 0) || null} initialMessage={initialMessage} />;
}
