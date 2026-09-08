import { makeRedirectUri } from "expo-auth-session";

function withoutTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

const apiBaseUrl = withoutTrailingSlash(
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000",
);
const deploymentEnvironment = process.env.EXPO_PUBLIC_DEPLOYMENT_ENV ?? "local";

if (!(["local", "staging", "production"] as const).includes(deploymentEnvironment as "local" | "staging" | "production")) {
  throw new Error(`Entorno móvil desconocido: ${deploymentEnvironment}`);
}
if (deploymentEnvironment === "staging" && apiBaseUrl !== "https://myscoope-staging.onrender.com") {
  throw new Error("La app de staging no está conectada al backend de staging esperado.");
}
if (deploymentEnvironment === "production" && apiBaseUrl !== "https://www.myscoope.com") {
  throw new Error("La app de producción no está conectada al backend de producción esperado.");
}

export const appConfig = {
  apiBaseUrl,
  deploymentEnvironment: deploymentEnvironment as "local" | "staging" | "production",
  oauthClientId: process.env.EXPO_PUBLIC_OAUTH_CLIENT_ID ?? "myscoope-ios",
  oauthRedirectUri:
    process.env.EXPO_PUBLIC_OAUTH_REDIRECT_URI ??
    makeRedirectUri({ scheme: "myscoope", path: "oauth/callback" }),
  oauthAuthorizationEndpoint: `${apiBaseUrl}/oauth/authorize`,
  oauthTokenEndpoint: `${apiBaseUrl}/oauth/token`,
  mobileScopes: ["mobile:read", "mobile:write", "mobile:account"],
  apnsEnvironment: process.env.EXPO_PUBLIC_APNS_ENVIRONMENT === "production" ? "production" : "sandbox",
} as const;
