const { resolveDeploymentTarget } = require("./config/deployment-targets");

module.exports = ({ config }) => {
  const deployment = resolveDeploymentTarget(process.env);
  const apnsMode = process.env.EXPO_PUBLIC_APNS_ENVIRONMENT === "production"
    ? "production"
    : "development";
  return {
    ...config,
    name: deployment.key === "staging" ? "My Scoope Staging" : config.name,
    extra: {
      ...config.extra,
      deploymentEnvironment: deployment.key,
    },
    plugins: config.plugins.map((plugin) => {
      const pluginName = Array.isArray(plugin) ? plugin[0] : plugin;
      if (pluginName !== "expo-notifications") return plugin;
      return ["expo-notifications", {
        color: "#0f172a",
        icon: "./assets/images/notification-icon.png",
        mode: apnsMode,
      }];
    }),
  };
};
