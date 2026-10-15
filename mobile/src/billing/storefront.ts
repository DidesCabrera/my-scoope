import { requireOptionalNativeModule } from "expo";
import { Platform } from "react-native";

export type StorefrontContext = {
  id: string;
  countryCode: string;
  currency: string | null;
  environment: "sandbox" | "unknown";
  observedAt: number;
};
type StorefrontModule = {
  getMyScoopeStorefront?(): Promise<StorefrontContext>;
  addListener(event: "myscoopeStorefrontChanged", listener: (context: StorefrontContext) => void): { remove(): void };
};

const native = Platform.OS === "ios" ? requireOptionalNativeModule<StorefrontModule>("ExpoIap") : null;

export function readStorefront(): Promise<StorefrontContext> {
  if (Platform.OS !== "ios") return Promise.resolve({ id: "google_play", countryCode: "", currency: null, environment: "unknown", observedAt: Date.now() });
  if (!native?.getMyScoopeStorefront) return Promise.reject(new Error("storefront_probe_unavailable"));
  return native.getMyScoopeStorefront();
}

export function listenForStorefrontChange(listener: () => void): () => void {
  if (!native?.getMyScoopeStorefront) return () => undefined;
  const subscription = native.addListener("myscoopeStorefrontChanged", listener);
  return () => subscription.remove();
}
