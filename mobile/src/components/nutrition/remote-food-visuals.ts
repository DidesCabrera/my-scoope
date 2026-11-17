import { useEffect, useSyncExternalStore } from "react";
import { File, Paths } from "expo-file-system";
import { Image, Platform } from "react-native";

import { appConfig } from "@/config/app-config";
import { normalizeFoodVisualName, parseFoodVisualManifest } from "./remote-food-visuals-core";

type Manifest = { images?: Record<string, string>; food_ids?: Record<string, string>; preparation_images?: Record<string, string>; preparation_ids?: Record<string, string> };

const MANIFEST_URL = `${appConfig.apiBaseUrl}/api/v1/catalog/visual-assets/manifest?layout=wide-v1`;
const REFRESH_MS = 60_000;

let images = new Map<string, string>();
let loadedAt = 0;
let pending: Promise<void> | null = null;
let hydration: Promise<void> | null = null;
let resolved = false;
let refreshTimer: ReturnType<typeof setInterval> | null = null;
const listeners = new Set<() => void>();
const readyImages = new Set<string>();
const failedImages = new Set<string>();
const pendingImages = new Set<string>();
const cacheFile = Platform.OS === "web" ? null : new File(Paths.document, "catalog-visual-manifest-wide-v2.json");

function notify() {
  listeners.forEach((listener) => listener());
}

function hydrateManifest(): Promise<void> {
  if (hydration) return hydration;
  hydration = (async () => {
    try {
      if (cacheFile?.exists) {
        const cached = JSON.parse(await cacheFile.text()) as { baseUrl?: string; manifest?: Manifest };
        if (cached.baseUrl === appConfig.apiBaseUrl && cached.manifest) {
          images = parseFoodVisualManifest(cached.manifest, appConfig.apiBaseUrl);
        }
      }
    } catch {
      // A corrupt or missing local copy must not block the live manifest.
    } finally {
      resolved = true;
      notify();
    }
  })();
  return hydration;
}

function prefetchImage(url: string) {
  if (readyImages.has(url) || failedImages.has(url) || pendingImages.has(url)) return;
  pendingImages.add(url);
  void Image.prefetch(url).then((loaded) => {
    if (loaded) readyImages.add(url);
    else failedImages.add(url);
  }).catch(() => {
    failedImages.add(url);
  }).finally(() => {
    pendingImages.delete(url);
    notify();
  });
}

export function refreshFoodVisualManifest(): Promise<void> {
  if (pending) return pending;
  if (loadedAt && Date.now() - loadedAt < REFRESH_MS) return Promise.resolve();
  pending = hydrateManifest().then(() => fetch(MANIFEST_URL))
    .then(async (response) => {
      if (!response.ok) throw new Error(`Food visuals manifest: ${response.status}`);
      const manifest = await response.json() as Manifest;
      images = parseFoodVisualManifest(manifest, appConfig.apiBaseUrl);
      loadedAt = Date.now();
      notify();
      try { cacheFile?.write(JSON.stringify({ baseUrl: appConfig.apiBaseUrl, manifest })); } catch {
        // Live images remain usable if local persistence is unavailable.
      }
    })
    .catch(() => { loadedAt = Date.now(); }) // Keep emoji or the last valid manifest on network failure.
    .finally(() => { pending = null; });
  return pending;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  if (!refreshTimer) refreshTimer = setInterval(() => { void refreshFoodVisualManifest(); }, REFRESH_MS);
  return () => {
    listeners.delete(listener);
    if (!listeners.size && refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  };
}

export function useRemoteFoodVisual(name: string, foodId?: number | string | null): string | undefined {
  const key = foodId == null ? `name:${normalizeFoodVisualName(name)}` : `id:${foodId}`;
  const url = useSyncExternalStore(subscribe, () => images.get(key), () => undefined);
  useEffect(() => { void refreshFoodVisualManifest(); }, []);
  return url;
}

export function useRemotePreparationVisual(name: string, preparationId?: number | string | null): string | undefined {
  const key = preparationId == null ? `preparation-name:${normalizeFoodVisualName(name)}` : `preparation-id:${preparationId}`;
  const url = useSyncExternalStore(subscribe, () => images.get(key), () => undefined);
  useEffect(() => { void refreshFoodVisualManifest(); }, []);
  return url;
}

export function useRemoteFoodVisualStatus(url: string | undefined): "pending" | "ready" | "failed" {
  const status = useSyncExternalStore<"pending" | "ready" | "failed">(subscribe, () => url && readyImages.has(url) ? "ready" : url && failedImages.has(url) ? "failed" : "pending", () => "pending");
  useEffect(() => { if (url) prefetchImage(url); }, [url]);
  return status;
}

export function useFoodVisualManifestResolved(): boolean {
  return useSyncExternalStore(subscribe, () => resolved, () => false);
}
