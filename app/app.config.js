// 동적 Expo 설정. app.json 을 기반으로, 안경(meta) 모드일 때만 Meta Wearables
// 네이티브 설정 플러그인을 붙인다. 인증값은 환경변수에서 읽어(커밋 안 함) 넘긴다.
//
// - EXPO_PUBLIC_GLASSES_PROVIDER=meta 일 때만 네이티브 플러그인 적용
// - META_WEARABLES_APPLICATION_ID / META_WEARABLES_CLIENT_TOKEN 은 네이티브
//   매니페스트에만 들어가고 JS 번들에는 노출되지 않는다(EXPO_PUBLIC_ 아님).
//   개발자 모드면 비워둬도 되며 그때는 "0" 으로 주입된다.
module.exports = ({ config }) => {
  const useMeta = process.env.EXPO_PUBLIC_GLASSES_PROVIDER === "meta";
  const plugins = [...(config.plugins || [])];

  if (useMeta) {
    plugins.push([
      "./plugins/withMetaWearables",
      {
        appId: process.env.META_WEARABLES_APPLICATION_ID || "0",
        clientToken: process.env.META_WEARABLES_CLIENT_TOKEN || "0",
        scheme: "blindguide",
      },
    ]);
  }

  return { ...config, plugins };
};
