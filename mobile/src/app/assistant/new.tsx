import { useLocalSearchParams } from "expo-router";

import { AssistantChatScreen } from "@/components/assistant/assistant-chat-screen";

export default function NewAssistantChatRoute() {
  const { comparisonId } = useLocalSearchParams<{ comparisonId?: string }>();
  return <AssistantChatScreen chatId={null} comparisonId={Number(comparisonId || 0) || null} />;
}
