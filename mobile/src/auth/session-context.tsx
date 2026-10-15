import { ResponseType, useAuthRequest } from "expo-auth-session";
import * as Crypto from "expo-crypto";
import * as Linking from "expo-linking";
import type { Href } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { MobileApiError, userFacingError } from "@/api/errors";
import type { ProfileData, SessionData } from "@/api/types";
import { appConfig } from "@/config/app-config";
import { recordMobileRequestMetric } from "@/observability/network-performance";

import { getDeviceIdentity, secureTokenStorage } from "./expo-adapters";
import { MobileSessionManager } from "./session-manager";
import { AuthorizationFlow } from "./authorization-flow";

type SessionStatus = "booting" | "anonymous" | "authenticated";

type SessionContextValue = {
  status: SessionStatus;
  session: SessionData | null;
  profile: ProfileData | null;
  authBusy: boolean;
  authError: string | null;
  authRestorePending: boolean;
  authReady: boolean;
  authReturnTo: Href | null;
  startSignIn(returnTo?: Href): Promise<void>;
  apiRequest<T>(path: string, init?: RequestInit): Promise<T>;
  refreshProfile(): Promise<ProfileData>;
  refreshSession(): Promise<SessionData>;
  signOut(): Promise<void>;
  retrySessionRestore(): void;
};

const SessionContext = createContext<SessionContextValue | null>(null);

// Keep the auth request mounted when Expo Router opens /oauth/callback.
WebBrowser.maybeCompleteAuthSession();

const discovery = {
  authorizationEndpoint: appConfig.oauthAuthorizationEndpoint,
  tokenEndpoint: appConfig.oauthTokenEndpoint,
};

export function SessionProvider({ children }: PropsWithChildren) {
  const manager = useMemo(() => {
    const nextManager = new MobileSessionManager(appConfig, secureTokenStorage, getDeviceIdentity);
    nextManager.setRequestMetricObserver(recordMobileRequestMetric);
    return nextManager;
  }, []);
  const [status, setStatus] = useState<SessionStatus>("booting");
  const [session, setSession] = useState<SessionData | null>(null);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authRestorePending, setAuthRestorePending] = useState(false);
  const [restoreAttempt, setRestoreAttempt] = useState(0);
  const [authReturnTo, setAuthReturnTo] = useState<Href | null>(null);
  const handledCode = useRef<string | null>(null);
  const authorizationFlow = useMemo(() => new AuthorizationFlow(), []);
  const [authorizationState, setAuthorizationState] = useState(() => Crypto.randomUUID());
  const resetAuthorization = useCallback(() => {
    authorizationFlow.invalidate();
    setAuthorizationState(Crypto.randomUUID());
    setAuthBusy(false);
  }, [authorizationFlow]);
  const [authRequest, authResponse, promptAsync] = useAuthRequest(
    {
      clientId: appConfig.oauthClientId,
      redirectUri: appConfig.oauthRedirectUri,
      responseType: ResponseType.Code,
      scopes: [...appConfig.mobileScopes],
      usePKCE: true,
      state: authorizationState,
    },
    discovery,
  );

  const loadProfile = useCallback(async () => {
    const version = authorizationFlow.version;
    const nextProfile = await manager.request<ProfileData>("/api/v1/me", { cache: "no-store" });
    if (version === authorizationFlow.version) setProfile(nextProfile);
    return nextProfile;
  }, [authorizationFlow, manager]);

  const loadSession = useCallback(async () => {
    const version = authorizationFlow.version;
    const nextSession = await manager.request<SessionData>("/api/v1/session");
    if (version === authorizationFlow.version) setSession(nextSession);
    return nextSession;
  }, [authorizationFlow, manager]);
  const apiRequest = useCallback(async <T,>(path: string, init?: RequestInit): Promise<T> => {
    const version = authorizationFlow.version;
    try { return await manager.request<T>(path, init); }
    catch (error) {
      if (version === authorizationFlow.version && !manager.hasCredentials
        && !(error instanceof MobileApiError && error.code === "mobile_session_changed")) {
        setSession(null);
        setProfile(null);
        setStatus("anonymous");
        setAuthRestorePending(false);
        setAuthError(userFacingError(error));
      }
      throw error;
    }
  }, [authorizationFlow, manager]);

  useEffect(() => {
    let active = true;
    void (async () => {
      setStatus("booting");
      setAuthRestorePending(false);
      setAuthError(null);
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
      } catch (error) {
        const invalidCredentials = error instanceof MobileApiError && [400, 401, 403].includes(error.status);
        if (invalidCredentials && active) await manager.clear();
        if (active) {
          setAuthError(userFacingError(error));
          setAuthRestorePending(!invalidCredentials);
          setSession(null);
          setProfile(null);
          setStatus("anonymous");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [loadProfile, manager, restoreAttempt]);

  const completeAuthorization = useCallback((code: string, codeVerifier: string, state: string | undefined) => {
    if (!authorizationFlow.accepts(state)) return;
    if (handledCode.current === code) return;
    handledCode.current = code;
    setAuthBusy(true);
    const version = authorizationFlow.version;
    void (async () => {
      try {
        const result = await authorizationFlow.complete(state, async () => ({
          session: await manager.exchangeAuthorizationCode(code, codeVerifier),
          profile: await manager.request<ProfileData>("/api/v1/me"),
        }));
        if (!result) return;
        setSession(result.session);
        setProfile(result.profile);
        setStatus("authenticated");
        setAuthBusy(false);
        authorizationFlow.invalidate();
      } catch (error) {
        if (version === authorizationFlow.version) {
          setAuthError(userFacingError(error));
          resetAuthorization();
        }
      } finally {
        if (version === authorizationFlow.version) setAuthBusy(false);
      }
    })();
  }, [authorizationFlow, manager, resetAuthorization]);

  useEffect(() => {
    if (authResponse?.type !== "success" || !authResponse.params.code || !authRequest?.codeVerifier) return;
    completeAuthorization(authResponse.params.code, authRequest.codeVerifier, authResponse.params.state);
  }, [authRequest?.codeVerifier, authResponse, completeAuthorization]);

  useEffect(() => {
    if (!authRequest) return;
    // Android can deliver the deep link before WebBrowser's promise settles.
    const subscription = Linking.addEventListener("url", ({ url }) => {
      if (!url.startsWith(`${appConfig.oauthRedirectUri}?`)) return;
      if (!authorizationFlow.accepts(new URL(url).searchParams.get("state"))) return;
      const result = authRequest.parseReturnUrl(url);
      if (result.type === "success" && result.params.code && authRequest.codeVerifier) {
        completeAuthorization(result.params.code, authRequest.codeVerifier, result.params.state);
      } else {
        setAuthError("No pudimos verificar el inicio de sesión. Inténtalo nuevamente.");
        resetAuthorization();
      }
    });
    return () => subscription.remove();
  }, [authRequest, authorizationFlow, completeAuthorization, resetAuthorization]);

  const value = useMemo<SessionContextValue>(
    () => ({
      status,
      session,
      profile,
      authBusy,
      authError,
      authRestorePending,
      authReady: Boolean(authRequest && authRequest.state === authorizationState),
      authReturnTo,
      async startSignIn(returnTo) {
        if (!authRequest || authRequest.state !== authorizationState) return;
        const version = authorizationFlow.start(authRequest.state);
        setAuthError(null);
        setAuthReturnTo(returnTo ?? null);
        setAuthBusy(true);
        try {
          const result = await promptAsync({ preferEphemeralSession: true });
          if (!authorizationFlow.isCurrent(version)) return;
          if (result.type === "success" && (!result.params.code || !authRequest.codeVerifier)) {
            setAuthError("No pudimos completar el inicio de sesión. Inténtalo nuevamente.");
            resetAuthorization();
          } else if (result.type !== "success") {
            if (result.type === "error") {
              setAuthError(userFacingError(result.error));
            }
            resetAuthorization();
          }
        } catch (error) {
          if (authorizationFlow.isCurrent(version)) {
            setAuthError(userFacingError(error));
            resetAuthorization();
          }
        }
      },
      apiRequest,
      retrySessionRestore: () => setRestoreAttempt((attempt) => attempt + 1),
      refreshProfile: loadProfile,
      refreshSession: loadSession,
      async signOut() {
        resetAuthorization();
        setAuthReturnTo(null);
        setAuthError(null);
        setSession(null);
        setProfile(null);
        setStatus("anonymous");
        await manager.signOut();
      },
    }),
    [apiRequest, authBusy, authError, authRequest, authRestorePending, authReturnTo, authorizationFlow, authorizationState, loadProfile, loadSession, manager, profile, promptAsync, resetAuthorization, session, status],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used inside SessionProvider");
  return context;
}
