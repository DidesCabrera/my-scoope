const DEPLOYMENT_TARGETS = Object.freeze({
  local: Object.freeze({
    apiBaseUrl: "http://127.0.0.1:8000",
    oauthClientId: "myscoope-ios",
    oauthRedirectUri: "myscoope://oauth/callback",
  }),
  staging: Object.freeze({
    apiBaseUrl: "https://myscoope-staging.onrender.com",
    oauthClientId: "myscoope-ios",
    oauthRedirectUri: "myscoope://oauth/callback",
  }),
  production: Object.freeze({
    apiBaseUrl: "https://www.myscoope.com",
    oauthClientId: "myscoope-ios",
    oauthRedirectUri: "myscoope://oauth/callback",
  }),
});

function withoutTrailingSlash(value) {
  return String(value ?? "").replace(/\/+$/, "");
}

function resolveDeploymentTarget(environment = process.env) {
  const privateTarget = environment.MYSCOOPE_BUILD_TARGET || "local";
  const publicTarget = environment.EXPO_PUBLIC_DEPLOYMENT_ENV || privateTarget;
  const expected = DEPLOYMENT_TARGETS[privateTarget];

  if (!expected) {
    throw new Error(`MYSCOOPE_BUILD_TARGET desconocido: ${privateTarget}`);
  }
  if (publicTarget !== privateTarget) {
    throw new Error(`Entornos incompatibles: MYSCOOPE_BUILD_TARGET=${privateTarget} y EXPO_PUBLIC_DEPLOYMENT_ENV=${publicTarget}`);
  }

  const apiBaseUrl = withoutTrailingSlash(environment.EXPO_PUBLIC_API_BASE_URL || expected.apiBaseUrl);
  const oauthClientId = environment.EXPO_PUBLIC_OAUTH_CLIENT_ID || expected.oauthClientId;
  const oauthRedirectUri = environment.EXPO_PUBLIC_OAUTH_REDIRECT_URI || expected.oauthRedirectUri;

  if (privateTarget !== "local" && apiBaseUrl !== expected.apiBaseUrl) {
    throw new Error(`La build ${privateTarget} debe usar ${expected.apiBaseUrl}; recibió ${apiBaseUrl || "una URL vacía"}`);
  }
  if (oauthClientId !== expected.oauthClientId) {
    throw new Error(`La build ${privateTarget} debe usar el cliente OAuth ${expected.oauthClientId}`);
  }
  if (oauthRedirectUri !== expected.oauthRedirectUri) {
    throw new Error(`La build ${privateTarget} debe usar el redirect OAuth ${expected.oauthRedirectUri}`);
  }

  return {
    apiBaseUrl,
    key: privateTarget,
    oauthClientId,
    oauthRedirectUri,
  };
}

module.exports = { DEPLOYMENT_TARGETS, resolveDeploymentTarget };
