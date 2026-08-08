import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useState } from "react";

import type { ProfileData, SessionData } from "@/api/types";
import { appConfig } from "@/config/app-config";

import { getDeviceIdentity, secureTokenStorage } from "./expo-adapters";
import { MobileSessionManager } from "./session-manager";

type SessionStatus = "booting" | "anonymous" | "authenticated";

type SessionContextValue = {
  status: SessionStatus;
  session: SessionData | null;
  profile: ProfileData | null;
  completeAuthorizationCode(code: string, codeVerifier: string): Promise<void>;
  apiRequest<T>(path: string, init?: RequestInit): Promise<T>;
  refreshProfile(): Promise<ProfileData>;
  signOut(): Promise<void>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: PropsWithChildren) {
  const manager = useMemo(
    () => new MobileSessionManager(appConfig, secureTokenStorage, getDeviceIdentity),
    [],
  );
  const [status, setStatus] = useState<SessionStatus>("booting");
  const [session, setSession] = useState<SessionData | null>(null);
  const [profile, setProfile] = useState<ProfileData | null>(null);

  const loadProfile = useCallback(async () => {
    const nextProfile = await manager.request<ProfileData>("/api/v1/me");
    setProfile(nextProfile);
    return nextProfile;
  }, [manager]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const restored = await manager.restore();
        if (!active) return;
        if (!restored) {
          setStatus("anonymous");
          return;
        }
        setSession(restored);
        await loadProfile();
        if (active) setStatus("authenticated");
      } catch {
        await manager.clear();
        if (active) {
          setSession(null);
          setProfile(null);
          setStatus("anonymous");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [loadProfile, manager]);

  const value = useMemo<SessionContextValue>(
    () => ({
      status,
      session,
      profile,
      async completeAuthorizationCode(code, codeVerifier) {
        const nextSession = await manager.exchangeAuthorizationCode(code, codeVerifier);
        setSession(nextSession);
        await loadProfile();
        setStatus("authenticated");
      },
      apiRequest: (path, init) => manager.request(path, init),
      refreshProfile: loadProfile,
      async signOut() {
        await manager.signOut();
        setSession(null);
        setProfile(null);
        setStatus("anonymous");
      },
    }),
    [loadProfile, manager, profile, session, status],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used inside SessionProvider");
  return context;
}
