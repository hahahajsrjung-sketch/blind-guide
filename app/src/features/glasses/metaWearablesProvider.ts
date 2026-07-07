import { NativeModules } from "react-native";

import { META_WEARABLES_APP_ID } from "../../config";
import {
  CapturedImage,
  GlassesConnectionState,
  GlassesProvider,
} from "./types";

// 실제 Meta 안경(Ray-Ban Meta 등) 연동 제공자 — 골격.
//
// Meta Wearables Device Access Toolkit 은 "네이티브 안드로이드 SDK"(Kotlin,
// GitHub Packages)다. JS 에서 직접 못 부르고, 네이티브 모듈 브리지 + dev build
// 가 있어야 한다 (Expo Go 로는 불가). 그래서 이 파일은 JS 쪽 "구조"만 잡고,
// 실제 네이티브 구현(Kotlin)과 페어링·실물 테스트는 SETUP.md 절차대로 진행한다.
//
// 아래 각 메서드는 네이티브에서 불러야 할 SDK 호출을 주석으로 매핑해 둔다.
// (SDK v0.8.0 기준. 출처: wearables.developer.meta.com/docs/build-integration-android)

// 네이티브 모듈이 제공해야 하는 계약(브리지 인터페이스).
// 안드로이드 쪽에서 이 이름/시그니처로 NativeModule 을 구현한다 (SETUP.md 참고).
interface MetaWearablesNativeModule {
  initialize(): Promise<void>; // Wearables.initialize(context)
  startRegistration(): Promise<void>; // Wearables.startRegistration(activity)
  getState(): Promise<string>; // registrationState / session 상태 → 문자열
  // createSession(AutoDeviceSelector) → session.start()
  //   → session.addStream(StreamConfiguration(quality, frameRate))
  //   → stream.start() → stream.capturePhoto() → PhotoData
  // 네이티브가 PhotoData 를 data URI(base64) 또는 업로드 URL 로 변환해 돌려준다.
  capturePhoto(): Promise<string>;
  stop(): Promise<void>; // stream.stop()/close(), session 종료
}

// 네이티브 모듈이 링크돼 있으면 여기서 잡힌다. dev build 전(Expo Go)에는 undefined.
const Native: MetaWearablesNativeModule | undefined = (
  NativeModules as Record<string, unknown>
)["MetaWearables"] as MetaWearablesNativeModule | undefined;

const NOT_LINKED =
  "Meta Wearables 네이티브 모듈이 없습니다. Expo Go 가 아니라 dev build 가 " +
  "필요합니다. 등록/빌드 절차는 app/SETUP.md 를 따르세요.";

function requireNative(): MetaWearablesNativeModule {
  if (!Native) {
    throw new Error(NOT_LINKED);
  }
  return Native;
}

export class MetaWearablesProvider implements GlassesProvider {
  readonly name = "meta";

  async initialize(): Promise<void> {
    // 참고: APP_ID 는 로그/디버그용. 실제 인증값(APPLICATION_ID/CLIENT_TOKEN)은
    // 안드로이드 매니페스트에 있다 (SETUP.md 2단계).
    if (!META_WEARABLES_APP_ID) {
      // 개발자 모드면 비어 있어도 되므로 막지는 않고, 경고만.
      console.warn(
        "EXPO_PUBLIC_META_WEARABLES_APP_ID 가 비어 있습니다. 개발자 모드가 아니면 SETUP.md 참고."
      );
    }
    await requireNative().initialize();
  }

  async startRegistration(): Promise<void> {
    await requireNative().startRegistration();
  }

  async getState(): Promise<GlassesConnectionState> {
    const raw = await requireNative().getState();
    // 네이티브 문자열을 우리 상태값으로 정규화. 모르는 값은 error 로.
    const known: GlassesConnectionState[] = [
      "unregistered",
      "registering",
      "registered",
      "sessionActive",
      "error",
    ];
    return (known as string[]).includes(raw)
      ? (raw as GlassesConnectionState)
      : "error";
  }

  async captureImage(): Promise<CapturedImage> {
    const image = await requireNative().capturePhoto();
    return { image, source: "meta-glasses" };
  }

  async stop(): Promise<void> {
    await requireNative().stop();
  }
}
