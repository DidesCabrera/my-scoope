import { useEffect, useSyncExternalStore } from "react";

import { appConfig } from "@/config/app-config";
import { normalizeFoodVisualName, parseFoodVisualManifest } from "./remote-food-visuals-core";

type Manifest = { images?: Record<string, string> };

const MANIFEST_URL = `${appConfig.apiBaseUrl}/api/v1/foods/visual-assets/manifest`;
const REFRESH_MS = 60_000;

let images = new Map<string, string>();
let loadedAt = 0;
let pending: Promise<void> | null = null;
let refreshTimer: ReturnType<typeof setInterval> | null = null;
const listeners = new Set<() => void>();

export function refreshFoodVisualManifest(): Promise<void> {
  if (pending) return pending;
  if (loadedAt && Date.now() - loadedAt < REFRESH_MS) return Promise.resolve();
  pending = fetch(MANIFEST_URL)
    .then(async (response) => {
      if (!response.ok) throw new Error(`Food visuals manifest: ${response.status}`);
      images = parseFoodVisualManifest(await response.json() as Manifest, appConfig.apiBaseUrl);
      loadedAt = Date.now();
      listeners.forEach((listener) => listener());
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
