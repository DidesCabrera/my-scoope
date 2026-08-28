module.exports = ({ config }) => {
  const apnsMode = process.env.EXPO_PUBLIC_APNS_ENVIRONMENT === "production"
    ? "production"
    : "development";
  return {
    ...config,
    plugins: config.plugins.map((plugin) => {
      const pluginName = Array.isArray(plugin) ? plugin[0] : plugin;
      if (pluginName !== "expo-notifications") return plugin;
      return ["expo-notifications", { mode: apnsMode }];
    }),
  };
};
