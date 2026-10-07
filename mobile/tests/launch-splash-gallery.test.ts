import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("the UI gallery previews the native launch splash from its production asset", async () => {
  const gallery = await fs.readFile(path.resolve(process.cwd(), "src/app/dev/ui-gallery.tsx"), "utf8");
  const iosStoryboard = await fs.readFile(path.resolve(process.cwd(), "ios/MyScoope/SplashScreen.storyboard"), "utf8");
  const appConfig = JSON.parse(await fs.readFile(path.resolve(process.cwd(), "app.json"), "utf8")) as {
    expo: { plugins: (string | [string, Record<string, unknown>])[] };
  };
  const splashPlugin = appConfig.expo.plugins.find((plugin) => Array.isArray(plugin) && plugin[0] === "expo-splash-screen");

  assert.deepEqual(splashPlugin, [
    "expo-splash-screen",
    {
      backgroundColor: "#000000",
      image: "./assets/images/launch-logo.png",
      imageWidth: 195,
    },
  ]);
  assert.match(gallery, /title="Inicio de la aplicación"/);
  assert.match(gallery, /source=\{require\("\.\.\/\.\.\/\.\.\/assets\/images\/launch-logo\.png"\)\}/);
  assert.match(gallery, /launchImageFrame: \{ aspectRatio: 1052 \/ 296, width: "50%" \}/);
  assert.match(gallery, /launchImage: \{ height: "100%", width: "100%" \}/);
  assert.match(gallery, /launchPreview: \{[^}]*backgroundColor: "#000000"/);
  assert.match(iosStoryboard, /<image name="SplashScreenLogo" width="195" height="55"\/>/);
  assert.match(iosStoryboard, /<color alpha="1\.000" blue="0\.00000000000000" green="0\.00000000000000" red="0\.00000000000000"/);
});
