import * as Crypto from "expo-crypto";
import * as Device from "expo-device";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

import type { DeviceIdentity, StoredTokenSet, TokenStorage } from "./session-manager";

const TOKEN_KEY = "myscoope.mobile.tokens.v1";
const DEVICE_ID_KEY = "myscoope.mobile.device-id.v1";
let webTokenSet: StoredTokenSet | null = null;
let webDeviceId: string | null = null;

export const secureTokenStorage: TokenStorage = {
  async get() {
    if (Platform.OS === "web") return webTokenSet;
    const raw = await SecureStore.getItemAsync(TOKEN_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as StoredTokenSet;
    } catch {
      await SecureStore.deleteItemAsync(TOKEN_KEY);
      return null;
    }
  },
  async set(tokens) {
    if (Platform.OS === "web") {
      webTokenSet = tokens;
      return;
    }
    await SecureStore.setItemAsync(TOKEN_KEY, JSON.stringify(tokens), {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
  },
  async clear() {
    if (Platform.OS === "web") {
      webTokenSet = null;
      return;
    }
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  },
};

export async function getDeviceIdentity(): Promise<DeviceIdentity> {
  let id = Platform.OS === "web" ? webDeviceId : await SecureStore.getItemAsync(DEVICE_ID_KEY);
  if (!id) {
    id = Crypto.randomUUID();
    if (Platform.OS === "web") {
      webDeviceId = id;
    } else {
      await SecureStore.setItemAsync(DEVICE_ID_KEY, id, {
        keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
      });
    }
  }
  const platform: DeviceIdentity["platform"] =
    Platform.OS === "ios" ? "ios" : Platform.OS === "android" ? "android" : "web";
  return {
    id,
    name: Device.modelName ?? (platform === "ios" ? "iPhone" : "My Scoope device"),
    platform,
  };
}
