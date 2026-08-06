import { makeRedirectUri } from "expo-auth-session";

function withoutTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

const apiBaseUrl = withoutTrailingSlash(
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000",
);

export const appConfig = {
  apiBaseUrl,
  oauthClientId: process.env.EXPO_PUBLIC_OAUTH_CLIENT_ID ?? "myscoope-ios",
  oauthRedirectUri:
    process.env.EXPO_PUBLIC_OAUTH_REDIRECT_URI ??
    makeRedirectUri({ scheme: "myscoope", path: "oauth/callback" }),
  oauthAuthorizationEndpoint: `${apiBaseUrl}/oauth/authorize`,
  oauthTokenEndpoint: `${apiBaseUrl}/oauth/token`,
  mobileScopes: ["mobile:read", "mobile:write", "mobile:account"],
} as const;
