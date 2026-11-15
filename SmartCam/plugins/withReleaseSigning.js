const { withAppBuildGradle } = require("@expo/config-plugins");

module.exports = function withReleaseSigning(config) {
  return withAppBuildGradle(config, (modConfig) => {
    let contents = modConfig.modResults.contents;

    if (contents.includes("SMARTCAM_KEYSTORE_PATH")) {
      return modConfig;
    }

    contents = contents.replace(
      /(signingConfigs\s*\{[\s\S]*?debug\s*\{[\s\S]*?\})/,
      `$1
        release {
            if (System.getenv("SMARTCAM_KEYSTORE_PATH")) {
                storeFile file(System.getenv("SMARTCAM_KEYSTORE_PATH"))
                storePassword System.getenv("SMARTCAM_KEYSTORE_PASSWORD")
                keyAlias System.getenv("SMARTCAM_KEY_ALIAS")
                keyPassword System.getenv("SMARTCAM_KEY_PASSWORD")
            }
        }`,
    );

    contents = contents.replace(
      /(buildTypes\s*\{[\s\S]*?release\s*\{[\s\S]*?)signingConfig\s+signingConfigs\.debug/,
      `$1signingConfig System.getenv("SMARTCAM_KEYSTORE_PATH") ? signingConfigs.release : signingConfigs.debug`,
    );

    modConfig.modResults.contents = contents;
    return modConfig;
  });
};
