import { ResponseType, useAuthRequest } from "expo-auth-session";
import * as Linking from "expo-linking";
import type { Href } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { userFacingError } from "@/api/errors";
import type { ProfileData, SessionData } from "@/api/types";
import { appConfig } from "@/config/app-config";

import { getDeviceIdentity, secureTokenStorage } from "./expo-adapters";
import { MobileSessionManager } from "./session-manager";

type SessionStatus = "booting" | "anonymous" | "authenticated";

type SessionContextValue = {
  status: SessionStatus;
  session: SessionData | null;
  profile: ProfileData | null;
  authBusy: boolean;
  authError: string | null;
  authReady: boolean;
  authReturnTo: Href | null;
  startSignIn(returnTo?: Href): Promise<void>;
  apiRequest<T>(path: string, init?: RequestInit): Promise<T>;
  refreshProfile(): Promise<ProfileData>;
  refreshSession(): Promise<SessionData>;
  signOut(): Promise<void>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

// Keep the auth request mounted when Expo Router opens /oauth/callback.
WebBrowser.maybeCompleteAuthSession();

const discovery = {
  authorizationEndpoint: appConfig.oauthAuthorizationEndpoint,
  tokenEndpoint: appConfig.oauthTokenEndpoint,
};

export function SessionProvider({ children }: PropsWithChildren) {
  const manager = useMemo(
    () => new MobileSessionManager(appConfig, secureTokenStorage, getDeviceIdentity),
    [],
  );
  const [status, setStatus] = useState<SessionStatus>("booting");
  const [session, setSession] = useState<SessionData | null>(null);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authReturnTo, setAuthReturnTo] = useState<Href | null>(null);
  const handledCode = useRef<string | null>(null);
  const [authRequest, authResponse, promptAsync] = useAuthRequest(
    {
      clientId: appConfig.oauthClientId,
      redirectUri: appConfig.oauthRedirectUri,
      responseType: ResponseType.Code,
      scopes: [...appConfig.mobileScopes],
      usePKCE: true,
    },
    discovery,
  );

  const loadProfile = useCallback(async () => {
    const nextProfile = await manager.request<ProfileData>("/api/v1/me");
    setProfile(nextProfile);
    return nextProfile;
  }, [manager]);

  const loadSession = useCallback(async () => {
    const nextSession = await manager.request<SessionData>("/api/v1/session");
    setSession(nextSession);
    return nextSession;
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

  const completeAuthorization = useCallback((code: string, codeVerifier: string) => {
    if (handledCode.current === code) return;
    handledCode.current = code;
    setAuthBusy(true);
    void (async () => {
      try {
        const nextSession = await manager.exchangeAuthorizationCode(code, codeVerifier);
        setSession(nextSession);
        await loadProfile();
        setStatus("authenticated");
      } catch (error) {
        setAuthError(userFacingError(error));
      } finally {
        setAuthBusy(false);
      }
    })();
  }, [loadProfile, manager]);

  useEffect(() => {
    if (authResponse?.type !== "success" || !authResponse.params.code || !authRequest?.codeVerifier) return;
    completeAuthorization(authResponse.params.code, authRequest.codeVerifier);
  }, [authRequest?.codeVerifier, authResponse, completeAuthorization]);

  useEffect(() => {
    if (!authRequest) return;
    // Android can deliver the deep link before WebBrowser's promise settles.
    const subscription = Linking.addEventListener("url", ({ url }) => {
      if (!url.startsWith(`${appConfig.oauthRedirectUri}?`)) return;
      const result = authRequest.parseReturnUrl(url);
      if (result.type === "success" && result.params.code && authRequest.codeVerifier) {
        completeAuthorization(result.params.code, authRequest.codeVerifier);
      } else {
        setAuthError("No pudimos verificar el inicio de sesión. Inténtalo nuevamente.");
        setAuthBusy(false);
      }
    });
    return () => subscription.remove();
  }, [authRequest, completeAuthorization]);

  const value = useMemo<SessionContextValue>(
    () => ({
      status,
      session,
      profile,
      authBusy,
      authError,
      authReady: Boolean(authRequest),
      authReturnTo,
      async startSignIn(returnTo) {
        if (!authRequest) return;
        setAuthError(null);
        setAuthReturnTo(returnTo ?? null);
        setAuthBusy(true);
        try {
          const result = await promptAsync();
          if (result.type === "success" && (!result.params.code || !authRequest.codeVerifier)) {
            setAuthError("No pudimos completar el inicio de sesión. Inténtalo nuevamente.");
            setAuthBusy(false);
          } else if (result.type !== "success") {
            if (result.type === "error") {
              setAuthError(userFacingError(result.error));
            }
            setAuthBusy(false);
          }
        } catch (error) {
          setAuthError(userFacingError(error));
          setAuthBusy(false);
        }
      },
      apiRequest: (path, init) => manager.request(path, init),
      refreshProfile: loadProfile,
      refreshSession: loadSession,
      async signOut() {
        await manager.signOut();
        setSession(null);
        setProfile(null);
        setStatus("anonymous");
      },
    }),
    [authBusy, authError, authRequest, authReturnTo, loadProfile, loadSession, manager, profile, promptAsync, session, status],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used inside SessionProvider");
  return context;
}
