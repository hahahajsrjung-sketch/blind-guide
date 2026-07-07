import {
  CapturedImage,
  GlassesConnectionState,
  GlassesProvider,
} from "./types";

// 하드웨어 없이 동작하는 가짜 안경 제공자.
//
// Meta SDK 의 MockDevice 개념과 같은 역할: 실물 안경 없이 앱 흐름(버튼→촬영→
// 백엔드→설명)을 끝까지 확인한다. Expo Go 에서도 그대로 돈다. 기본값.
export class MockGlassesProvider implements GlassesProvider {
  readonly name = "mock";
  private state: GlassesConnectionState = "registered";

  async initialize(): Promise<void> {
    // 가짜라 준비할 게 없다. 바로 등록된 것으로 둔다.
    this.state = "registered";
  }

  async startRegistration(): Promise<void> {
    // 실제 페어링 대신 즉시 등록 완료로 처리.
    this.state = "registered";
  }

  async getState(): Promise<GlassesConnectionState> {
    return this.state;
  }

  async captureImage(): Promise<CapturedImage> {
    // 실제 이미지 대신 자리표시자. 백엔드도 인식을 폴백 처리하므로 흐름 확인엔 충분.
    return { image: "PLACEHOLDER_IMAGE", source: "mock" };
  }

  async stop(): Promise<void> {
    this.state = "registered";
  }
}
