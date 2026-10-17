const NAVIGATION_PRESS_LOCK_MS = 1000;

let navigationPressLocked = false;
let unlockTimer: ReturnType<typeof setTimeout> | null = null;

export function runGuardedNavigation(action: () => void): boolean {
  if (navigationPressLocked) return false;

  navigationPressLocked = true;
  try {
    action();
  } catch (error) {
    resetNavigationPressGuard();
    throw error;
  }

  unlockTimer = setTimeout(resetNavigationPressGuard, NAVIGATION_PRESS_LOCK_MS);
  return true;
}

export function resetNavigationPressGuard(): void {
  navigationPressLocked = false;
  if (unlockTimer) clearTimeout(unlockTimer);
  unlockTimer = null;
}
