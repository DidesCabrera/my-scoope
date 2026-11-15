import { useEffect, useState } from "react";
import { Keyboard, Platform } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { screenBottomSpacing } from "./screen-bottom-spacing-values";

export function useScreenBottomSpacing(): number {
  const { bottom } = useSafeAreaInsets();
  const [keyboardVisible, setKeyboardVisible] = useState(() => Platform.OS !== "web" && Keyboard.isVisible());

  useEffect(() => {
    if (Platform.OS === "web") return;
    const show = Keyboard.addListener(Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow", () => setKeyboardVisible(true));
    const hide = Keyboard.addListener(Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide", () => setKeyboardVisible(false));
    return () => { show.remove(); hide.remove(); };
  }, []);

  return screenBottomSpacing(keyboardVisible, bottom);
}
