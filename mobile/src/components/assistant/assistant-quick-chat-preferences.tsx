import * as SecureStore from "expo-secure-store";
import { createContext, type PropsWithChildren, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Platform } from "react-native";

const PREFERENCES_KEY = "myscoope.assistant.quick-chat.preferences.v1";

type AssistantQuickChatPreferences = {
  ready: boolean;
  setShowFloatingButton(value: boolean): Promise<void>;
  showFloatingButton: boolean;
};

const AssistantQuickChatPreferencesContext = createContext<AssistantQuickChatPreferences | null>(null);

async function loadShowFloatingButton() {
  if (Platform.OS === "web" || !(await SecureStore.isAvailableAsync())) return true;
  const raw = await SecureStore.getItemAsync(PREFERENCES_KEY);
  if (!raw) return true;
  try {
    const parsed = JSON.parse(raw) as { showFloatingButton?: unknown };
    return typeof parsed.showFloatingButton === "boolean" ? parsed.showFloatingButton : true;
  } catch {
    return true;
  }
}

async function saveShowFloatingButton(value: boolean) {
  if (Platform.OS === "web" || !(await SecureStore.isAvailableAsync())) return;
  await SecureStore.setItemAsync(
    PREFERENCES_KEY,
    JSON.stringify({ showFloatingButton: value }),
    { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY },
  );
}

export function AssistantQuickChatPreferencesProvider({ children }: PropsWithChildren) {
  const [ready, setReady] = useState(false);
  const [showFloatingButton, setShowFloatingButtonState] = useState(true);

  useEffect(() => {
    let active = true;
    void loadShowFloatingButton()
      .then((value) => { if (active) setShowFloatingButtonState(value); })
      .catch(() => undefined)
      .finally(() => { if (active) setReady(true); });
    return () => { active = false; };
  }, []);

  const setShowFloatingButton = useCallback(async (value: boolean) => {
    const previous = showFloatingButton;
    setShowFloatingButtonState(value);
    try {
      await saveShowFloatingButton(value);
    } catch (error) {
      setShowFloatingButtonState(previous);
      throw error;
    }
  }, [showFloatingButton]);

  const value = useMemo(() => ({ ready, setShowFloatingButton, showFloatingButton }), [ready, setShowFloatingButton, showFloatingButton]);
  return <AssistantQuickChatPreferencesContext.Provider value={value}>{children}</AssistantQuickChatPreferencesContext.Provider>;
}

export function useAssistantQuickChatPreferences() {
  const context = useContext(AssistantQuickChatPreferencesContext);
  if (!context) throw new Error("useAssistantQuickChatPreferences must be used inside AssistantQuickChatPreferencesProvider");
  return context;
}
