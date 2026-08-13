import { useLocalSearchParams } from "expo-router";

import { AssistantChatScreen } from "@/components/assistant/assistant-chat-screen";

export default function AssistantChatDetailRoute() {
  const { id, comparisonId } = useLocalSearchParams<{ id: string; comparisonId?: string }>();
  return <AssistantChatScreen chatId={Number(id)} comparisonId={Number(comparisonId || 0) || null} />;
}
