// 안경(웨어러블) 이미지 소스의 공통 인터페이스.
//
// 핵심 흐름: [안경 카메라] → captureImage() → 백엔드 POST /describe.
// 구현체는 두 가지:
//   - MockGlassesProvider   : 하드웨어 없이 가짜 이미지 (오늘 동작)
//   - MetaWearablesProvider : 실제 Meta 안경 (네이티브 SDK, dev build 필요)
// 화면(MainScreen)과 호출부(cameraStub)는 이 인터페이스만 알면 되고,
// 실제 SDK 교체 시 다른 코드는 안 건드린다.

// 안경 연결/세션 상태.
export type GlassesConnectionState =
  | "unregistered" // 아직 폰과 안경이 등록(페어링)되지 않음
  | "registering" // 등록 진행 중
  | "registered" // 등록됨, 세션은 아직 안 열림
  | "sessionActive" // 카메라 세션 활성 — 촬영 가능
  | "error";

// 촬영 결과. 백엔드로 보낼 수 있는 형태여야 한다.
export interface CapturedImage {
  // 백엔드로 보낼 이미지 값.
  //   mock  : 자리표시자 문자열
  //   meta  : data URI(base64) 또는 업로드 후 받은 http(s) URL
  // (backend recognition 은 http(s) URL / data URI 를 실제 인식, 그 외엔 폴백)
  image: string;
  source: "mock" | "meta-glasses";
}

// 안경 이미지 소스 제공자.
export interface GlassesProvider {
  // 사람이 읽는 이름 (로그/디버그용).
  readonly name: string;

  // SDK 초기화. 앱 시작 시 1회. (Meta: Wearables.initialize(context))
  initialize(): Promise<void>;

  // 폰↔안경 등록(페어링) 플로우 진입. 사용자 상호작용 필요.
  // (Meta: Wearables.startRegistration(activity))
  startRegistration(): Promise<void>;

  // 현재 상태 조회.
  getState(): Promise<GlassesConnectionState>;

  // 안경 카메라로 한 장 촬영해 백엔드로 보낼 이미지를 반환.
  // (Meta: createSession → addStream → stream.capturePhoto())
  captureImage(): Promise<CapturedImage>;

  // 세션/자원 정리.
  stop(): Promise<void>;
}
