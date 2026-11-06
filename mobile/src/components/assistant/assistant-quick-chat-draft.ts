let pendingMessage: string | null = null;

export function stageAssistantQuickChatMessage(value: string): void {
  const normalized = value.trim();
  pendingMessage = normalized || null;
}

export function consumeAssistantQuickChatMessage(): string | null {
  const message = pendingMessage;
  pendingMessage = null;
  return message;
}
