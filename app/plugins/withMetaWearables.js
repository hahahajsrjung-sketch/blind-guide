// Expo config plugin — Meta Wearables Device Access Toolkit(안드로이드) 네이티브 설정 자동화.
//
// `expo prebuild` 시 이 플러그인이 android/ 프로젝트에 아래를 주입한다:
//   1) 필요한 권한 (Bluetooth/Internet/Camera)
//   2) SDK 인증 메타데이터 (APPLICATION_ID / CLIENT_TOKEN / DAM_ENABLED)
//   3) 콜백 인텐트필터(scheme)
//   4) GitHub Packages maven 저장소 + mwdat 의존성
//
// 이렇게 하면 SETUP.md 의 매니페스트/gradle 손편집이 필요 없다.
// 값(appId/clientToken)은 app.config.js 가 환경변수에서 읽어 넘긴다.
//
// 주의: 이 플러그인은 prebuild 시점에만 적용된다. 실제 빌드에서 처음 돌릴 때
//       android 템플릿 버전에 따라 문자열 위치가 다를 수 있으니 결과를 확인한다.

const {
  withAndroidManifest,
  withProjectBuildGradle,
  withAppBuildGradle,
  AndroidConfig,
} = require("expo/config-plugins");

const SDK_VERSION = "0.8.0";
const MAVEN_URL =
  "https://maven.pkg.github.com/facebook/meta-wearables-dat-android";

const PERMISSIONS = [
  "android.permission.BLUETOOTH",
  "android.permission.BLUETOOTH_CONNECT",
  "android.permission.INTERNET",
  "android.permission.CAMERA",
];

function withPermissions(config) {
  return withAndroidManifest(config, (cfg) => {
    const manifest = cfg.modResults.manifest;
    manifest["uses-permission"] = manifest["uses-permission"] || [];
    for (const name of PERMISSIONS) {
      const exists = manifest["uses-permission"].some(
        (p) => p.$ && p.$["android:name"] === name
      );
      if (!exists) {
        manifest["uses-permission"].push({ $: { "android:name": name } });
      }
    }
    return cfg;
  });
}

function withMetadataAndScheme(config, props) {
  const appId = String(props.appId ?? "0");
  const clientToken = String(props.clientToken ?? "0");
  const scheme = String(props.scheme ?? "blindguide");

  return withAndroidManifest(config, (cfg) => {
    const app = AndroidConfig.Manifest.getMainApplicationOrThrow(
      cfg.modResults
    );

    // meta-data 주입 (중복 방지 후 추가)
    app["meta-data"] = app["meta-data"] || [];
    const setMeta = (name, value) => {
      app["meta-data"] = app["meta-data"].filter(
        (m) => !(m.$ && m.$["android:name"] === name)
      );
      app["meta-data"].push({
        $: { "android:name": name, "android:value": value },
      });
    };
    setMeta("com.meta.wearable.mwdat.APPLICATION_ID", appId);
    setMeta("com.meta.wearable.mwdat.CLIENT_TOKEN", clientToken);
    setMeta("com.meta.wearable.mwdat.DAM_ENABLED", "true");

    // 콜백 intent-filter 를 메인(런처) 액티비티에 추가
    const activity = AndroidConfig.Manifest.getMainActivityOrThrow(
      cfg.modResults
    );
    activity["intent-filter"] = activity["intent-filter"] || [];
    const hasScheme = activity["intent-filter"].some(
      (f) =>
        Array.isArray(f.data) &&
        f.data.some((d) => d.$ && d.$["android:scheme"] === scheme)
    );
    if (!hasScheme) {
      activity["intent-filter"].push({
        action: [{ $: { "android:name": "android.intent.action.VIEW" } }],
        category: [
          { $: { "android:name": "android.intent.category.DEFAULT" } },
          { $: { "android:name": "android.intent.category.BROWSABLE" } },
        ],
        data: [{ $: { "android:scheme": scheme } }],
      });
    }
    return cfg;
  });
}

function withMavenRepo(config) {
  return withProjectBuildGradle(config, (cfg) => {
    if (cfg.modResults.language !== "groovy") return cfg;
    let contents = cfg.modResults.contents;
    if (contents.includes(MAVEN_URL)) return cfg; // 이미 있음

    const mavenBlock = `
        maven {
            url = uri("${MAVEN_URL}")
            credentials {
                username = System.getenv("GITHUB_ACTOR")
                password = System.getenv("GITHUB_TOKEN")
            }
        }`;

    // allprojects { repositories { ... } } 안에 넣는다.
    const marker = /allprojects\s*\{[\s\S]*?repositories\s*\{/;
    if (marker.test(contents)) {
      contents = contents.replace(marker, (m) => m + mavenBlock);
    }
    cfg.modResults.contents = contents;
    return cfg;
  });
}

function withDependencies(config) {
  return withAppBuildGradle(config, (cfg) => {
    if (cfg.modResults.language !== "groovy") return cfg;
    let contents = cfg.modResults.contents;
    if (contents.includes("com.meta.wearable:mwdat-core")) return cfg;

    const deps = `
    implementation "com.meta.wearable:mwdat-core:${SDK_VERSION}"
    implementation "com.meta.wearable:mwdat-camera:${SDK_VERSION}"
    implementation "com.meta.wearable:mwdat-mockdevice:${SDK_VERSION}"`;

    contents = contents.replace(/dependencies\s*\{/, (m) => m + deps);
    cfg.modResults.contents = contents;
    return cfg;
  });
}

/**
 * @param {import('expo/config').ExpoConfig} config
 * @param {{ appId?: string, clientToken?: string, scheme?: string }} props
 */
module.exports = function withMetaWearables(config, props = {}) {
  config = withPermissions(config);
  config = withMetadataAndScheme(config, props);
  config = withMavenRepo(config);
  config = withDependencies(config);
  return config;
};
