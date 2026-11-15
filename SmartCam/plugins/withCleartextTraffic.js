const { withAndroidManifest, AndroidConfig } = require("@expo/config-plugins");

module.exports = function withCleartextTraffic(config) {
  return withAndroidManifest(config, (modConfig) => {
    const mainApplication = AndroidConfig.Manifest.getMainApplicationOrThrow(
      modConfig.modResults,
    );
    mainApplication.$["android:usesCleartextTraffic"] = "true";
    return modConfig;
  });
};
