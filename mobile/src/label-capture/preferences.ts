import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

export type LabelCapturePreferences = {
  aiConsentGranted: boolean | null;
  validateBeforeSending: boolean;
  savePhotographs: boolean;
  shareForCuration: boolean;
};

function key(userId: number) {
  return `myscoope.label-capture.preferences.v1.${userId}`;
}

export async function loadLabelCapturePreferences(userId: number): Promise<LabelCapturePreferences> {
  const defaults = { aiConsentGranted: null, validateBeforeSending: true, savePhotographs: false, shareForCuration: false };
  if (Platform.OS === "web" || !(await SecureStore.isAvailableAsync())) return defaults;
  const raw = await SecureStore.getItemAsync(key(userId));
  if (!raw) return defaults;
  try {
    const parsed = JSON.parse(raw) as Partial<LabelCapturePreferences>;
    return {
      aiConsentGranted: typeof parsed.aiConsentGranted === "boolean" ? parsed.aiConsentGranted : null,
      validateBeforeSending: parsed.validateBeforeSending !== false,
      savePhotographs: parsed.savePhotographs === true,
      shareForCuration: parsed.shareForCuration === true,
    };
  } catch {
    return defaults;
  }
}

export async function saveLabelCapturePreferences(userId: number, preferences: LabelCapturePreferences): Promise<void> {
  if (Platform.OS === "web" || !(await SecureStore.isAvailableAsync())) return;
  await SecureStore.setItemAsync(key(userId), JSON.stringify(preferences), {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}
