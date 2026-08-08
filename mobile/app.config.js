const baseConfig = require("./app.json").expo;

module.exports = () => {
  const apnsMode = process.env.EXPO_PUBLIC_APNS_ENVIRONMENT === "production"
    ? "production"
    : "development";
  return {
    ...baseConfig,
    plugins: baseConfig.plugins.map((plugin) => {
      const pluginName = Array.isArray(plugin) ? plugin[0] : plugin;
      if (pluginName !== "expo-notifications") return plugin;
      return ["expo-notifications", { mode: apnsMode }];
    }),
  };
};
