// 앱 설정값. 백엔드 주소 등은 여기 한 곳에서만 읽는다.
// 규칙: 주소·비밀값은 하드코딩하지 않고 환경변수(.env)에서 가져온다.

// Expo 는 EXPO_PUBLIC_ 접두사 변수만 번들에 넣어준다.
// .env 가 없을 때를 대비한 기본값은 로컬 백엔드로 둔다.
const DEFAULT_BACKEND_URL = "http://localhost:8000";

export const BACKEND_URL =
  process.env.EXPO_PUBLIC_BACKEND_URL ?? DEFAULT_BACKEND_URL;

// 백엔드 설명 요청 엔드포인트. (PROJECT_OVERVIEW / APP_SPEC 기준: POST /describe)
export const DESCRIBE_PATH = "/describe";

// ── 안경(웨어러블) 이미지 소스 설정 ─────────────────────────────
// 어떤 이미지 소스를 쓸지 고른다.
//   "mock" — 하드웨어 없이 가짜 이미지 (Expo Go/개발 기본값). 앱 흐름 확인용.
//   "meta" — Meta Wearables Device Access Toolkit(실제 안경). dev build 필요.
// 실물 안경 연동은 네이티브 SDK라 Expo Go 로는 안 되고 dev build 가 필요하다.
// 자세한 등록/빌드 절차는 app/SETUP.md 참고.
export type GlassesProviderKind = "mock" | "meta";

export const GLASSES_PROVIDER: GlassesProviderKind =
  process.env.EXPO_PUBLIC_GLASSES_PROVIDER === "meta" ? "meta" : "mock";

// Meta Wearables 앱 등록값. Wearables Developer Center 에서 발급.
// APP_ID 는 JS 에서 참고용으로만 두고, 실제 SDK 인증에 쓰는 APPLICATION_ID /
// CLIENT_TOKEN 은 안드로이드 매니페스트(네이티브)에 넣는다 (SETUP.md 참고).
// 개발자 모드(Developer Mode)면 비워두거나 0 으로 둬도 된다.
export const META_WEARABLES_APP_ID =
  process.env.EXPO_PUBLIC_META_WEARABLES_APP_ID ?? "";
