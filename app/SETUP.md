# SETUP — Meta 안경 연동 준비

이 문서는 **당신이 직접 해야 하는 등록·입력·빌드 절차**를 정리한다. 코드 구조
(`src/features/glasses/`)는 이미 준비돼 있고, 실제 페어링과 실물 테스트는
개발자 계정·앱 ID·실물 안경이 필요하므로 여기 절차대로 당신이 진행한다.

> 표기: **[YOU]** = 당신이 계정/대시보드/실물에서 해야 하는 것,
> **[CODE]** = 이미 코드에 되어 있거나 값만 넣으면 되는 것.

대상 SDK: **Meta Wearables Device Access Toolkit (Android) v0.8.0**
문서: https://wearables.developer.meta.com/docs/build-integration-android/
저장소: https://github.com/facebook/meta-wearables-dat-android

---

## 0. 큰 그림: 왜 Expo Go 로 안 되나

이 앱은 Expo(React Native)다. 지금까지 뼈대는 **Expo Go**(폰에 설치하는 범용
실행기)로 QR 스캔만으로 돌았다. 하지만 Meta Wearables SDK 는 **네이티브 안드로이드
라이브러리**라 Expo Go 에 들어있지 않다. 그래서 안경을 실제로 붙이려면:

- **dev build(개발 빌드)** 를 만들어야 한다. 즉 `expo prebuild` 로 안드로이드
  네이티브 프로젝트를 생성하고, 거기에 SDK 와 네이티브 모듈(Kotlin)을 넣어
  빌드한 앱을 폰에 설치한다. (Expo Go 대신 "우리 앱"이 깔린다.)
- **안드로이드 전용**이다. iOS 는 별도 SDK(`facebook/meta-wearables-dat-ios`)가
  있으나 이 프로젝트에서는 안드로이드부터 간다.

지금 단계에서 코드는 `EXPO_PUBLIC_GLASSES_PROVIDER=mock` 이라 안경 없이 돌고,
아래 절차를 마치고 `meta` 로 바꾸면 실제 안경으로 전환된다.

---

## 1. [YOU] Meta 개발자 등록 & 프로젝트 생성

> 개인 페이스북 개발자 계정이 아니라 **Managed Meta Account(조직) + 개발자 모드**
> 방식이다. 아직 개발자 프리뷰라 지역/기기에 따라 접근 제한 가능 → 안 되면 지원 여부 먼저 확인.

### 준비물
- 지원 안경: Ray-Ban Meta (Gen 1/2), Ray-Ban Meta Optics, Meta Ray-Ban Display
- 폰: Android 10+ (또는 iOS 15.2+), **Meta AI 앱** 설치
- Android Studio

### 1-A. 계정·조직(MMA)
1. **Wearables Developer Center** (https://wearables.developer.meta.com) 에 관리자로 가입
   → 진행 중 **work.meta.com**(MMA 설정)으로 리다이렉트됨.
2. 회사/팀 이름으로 **조직 생성** (본인이 admin). 팀원은 **Invite Member** 로 초대,
   팀원은 발급된 MMA 계정으로 로그인. (혼자면 본인이 admin)

### 1-B. 개발자 모드 켜기 (심사 없이 테스트)
1. **Meta AI 앱 → Settings → App Info**
2. **App version 숫자를 5번 탭** → 개발자 모드 토글 등장 → **Enable**
3. 안경은 Meta AI 앱 **Devices 탭**에서 페어링 + 펌웨어 최신화
4. 등록 앱은 Meta AI → **App connections → Developer mode apps** 에 표시됨

### 1-C. 프로젝트 등록해서 값 받기
1. Wearables Developer Center → **New project** → 이름·설명 입력
2. 좌측 **Configuration** 에서 모바일 앱 정보 입력:
   - **Package name (Android)**: `com.blindguide.app` ← 그대로 (app.json 번들ID와 일치)
   - **App name / icon**: PNG·JPEG, **최대 200×200px**
   - 버전 정보
3. **Application ID** 를 Configuration 에서 복사 → 2단계 `.env` 에 넣는다.
   - 콜백 스킴은 `blindguide` (config plugin 이 매니페스트에 자동 주입)

> **개발자 모드로 먼저 테스트**하려면 CLIENT_TOKEN 없이(=`0`) 진행 가능. 정식 배포 전
> 단계에서 채운다. (CLIENT_TOKEN 의 대시보드 위치는 공식 문서에 명확치 않음 →
> Configuration 화면에서 Application ID 근처 확인.)

---

## 2. [MOSTLY CODE] 네이티브 설정 — 이미 자동화됨

**좋은 소식:** 매니페스트 권한/메타데이터/인텐트필터와 gradle 저장소/의존성은
**config plugin(`plugins/withMetaWearables.js`)이 `expo prebuild` 때 자동 주입**한다.
이 플러그인은 `EXPO_PUBLIC_GLASSES_PROVIDER=meta` 일 때만 켜진다(`app.config.js`).
그래서 당신은 **값만 환경변수로 넣으면** 되고, 생성된 파일을 손으로 고칠 필요가 없다.

### 2-1. GitHub Packages 인증 (SDK 다운로드용)
SDK 는 GitHub Packages 에 있어 `read:packages` 권한의 **GitHub 토큰**이 필요하다.
- **[YOU]** GitHub → Settings → Developer settings → Personal access tokens 에서
  `read:packages` 스코프 토큰 발급.
- 빌드 환경에 환경변수로 둔다 (플러그인이 gradle 에서 이 값을 읽는다):
  ```
  GITHUB_ACTOR=<your-github-username>
  GITHUB_TOKEN=<read:packages 토큰>
  ```

### 2-2. 인증값 환경변수 (`.env`)
1단계에서 발급받은 값을 넣는다. **개발자 모드면 비워둬도 됨(자동으로 `0` 주입).**
```
EXPO_PUBLIC_GLASSES_PROVIDER=meta
META_WEARABLES_APPLICATION_ID=<APPLICATION_ID>
META_WEARABLES_CLIENT_TOKEN=<CLIENT_TOKEN>
```
> `META_WEARABLES_*` 는 `EXPO_PUBLIC_` 이 아니라 **JS 번들에 노출되지 않고**
> 네이티브 매니페스트에만 들어간다. 콜백 스킴은 `blindguide` 로 자동 설정된다
> (1단계 5번 등록값과 일치시킬 것).

플러그인이 자동으로 넣는 것(확인용): 권한 4종, `mwdat.APPLICATION_ID/CLIENT_TOKEN/
DAM_ENABLED` 메타데이터, `blindguide` 인텐트필터, maven 저장소 + `mwdat-core/camera/
mockdevice:0.8.0` 의존성.

> **[YOU] 할 일은 위 환경변수 채우기뿐.** 나머지 매니페스트/gradle 편집은 플러그인이 한다.
> (첫 prebuild 후 android/ 결과가 맞는지 한 번 확인하면 좋다.)

---

## 3. [YOU] dev build 만들기 & 네이티브 모듈

JS 는 네이티브 SDK 를 직접 못 부른다. JS ↔ Kotlin 을 잇는 **네이티브 모듈**이
필요하다. 우리 JS 쪽은 이미 그 계약(브리지 인터페이스)을 정의해 뒀다:

- 파일: `src/features/glasses/metaWearablesProvider.ts`
- 기대하는 네이티브 모듈 이름: **`MetaWearables`**
- 네이티브가 구현해야 할 메서드(그리고 각기 대응하는 SDK 호출):
  | JS 브리지 메서드 | Kotlin SDK 호출 |
  |---|---|
  | `initialize()` | `Wearables.initialize(context)` |
  | `startRegistration()` | `Wearables.startRegistration(activity)` |
  | `getState()` | `Wearables.registrationState` / 세션 상태 → 문자열 반환 |
  | `capturePhoto()` | `createSession(AutoDeviceSelector())` → `session.start()` → `session.addStream(StreamConfiguration(VideoQuality.MEDIUM, frameRate=24))` → `stream.start()` → `stream.capturePhoto()` → `PhotoData` 를 **data URI(base64) 또는 업로드 URL** 로 변환해 반환 |
  | `stop()` | `stream.stop()`/`close()`, 세션 종료 |

**레퍼런스 코드는 이미 있다:** `native/android/MetaWearablesModule.kt`,
`native/android/MetaWearablesPackage.kt`. 문서 API 기반 골격이라, 실제 SDK 타입에
맞춰 `[TODO]` 부분(특히 권한 요청·PhotoData 바이트 추출)만 채우면 된다.

절차:
1. **[YOU]** `EXPO_PUBLIC_GLASSES_PROVIDER=meta` 로 두고 `npx expo prebuild -p android`
   → `android/` 생성 + config plugin 이 매니페스트/gradle 자동 설정.
2. **[YOU]** `native/android/*.kt` 두 파일을
   `android/app/src/main/java/com/blindguide/app/metawearables/` 로 복사.
3. **[YOU]** `android/app/.../MainApplication.kt` 의 `getPackages()` 에
   `add(MetaWearablesPackage())` 추가. (autolinking 자동등록은 템플릿차가 있어 수동 권장)
4. **[YOU]** `.kt` 의 `[TODO]` 를 실제 SDK 호출로 채운다 (문서 세션/스트림 예제 이식).
5. **[YOU]** 빌드·설치:
   - 로컬: `npx expo run:android` (Android Studio/SDK 필요)
   - 또는 클라우드: `eas build -p android --profile development`
6. **[YOU]** 앱 실행 후 등록 플로우를 태워 폰↔안경 페어링.

> **먼저 MockDevice 로**: 실물 안경 전에 `mwdat-mockdevice` 로 가짜 기기를 페어링해
> 촬영/스트림을 시뮬레이션할 수 있다. 네이티브 모듈이 붙었는지 이걸로 먼저 확인.

---

## 4. [CODE] 앱을 안경 모드로 전환

네이티브가 붙고 빌드가 되면, JS 쪽은 값만 바꾸면 된다:

- `.env`:
  ```
  EXPO_PUBLIC_GLASSES_PROVIDER=meta
  EXPO_PUBLIC_META_WEARABLES_APP_ID=<참고용, 1단계 APPLICATION_ID>
  ```
- 그러면 `getGlassesProvider()` 가 `MetaWearablesProvider` 를 쓰고,
  버튼을 누르면 **안경 카메라로 촬영 → 백엔드 POST /describe → 설명(글자+음성)**
  흐름이 실제 안경으로 돈다. 화면(MainScreen) 코드는 그대로다.

전환 전(mock)에는 지금처럼 하드웨어 없이 전체 흐름이 동작한다.

---

## 5. 당신이 입력/등록해야 할 값 — 체크리스트

- [ ] Meta 개발자 계정 (developers.meta.com)
- [ ] Wearables Developer Center 에서 앱 생성
- [ ] **APPLICATION_ID** 발급 → `.env` `META_WEARABLES_APPLICATION_ID`
- [ ] **CLIENT_TOKEN** 발급 → `.env` `META_WEARABLES_CLIENT_TOKEN`
- [ ] 콜백 스킴 `blindguide` 등록 (플러그인이 매니페스트에 자동 주입)
- [ ] GitHub `read:packages` 토큰 → 빌드 환경변수 `GITHUB_ACTOR`/`GITHUB_TOKEN`
- [ ] `.env` 에서 `EXPO_PUBLIC_GLASSES_PROVIDER=meta` 로 전환
- [ ] `expo prebuild` → `native/android/*.kt` 복사 + `MetaWearablesPackage` 등록 → `[TODO]` 채우기
- [ ] dev build 설치 (`expo run:android` 또는 `eas build --profile development`)
- [ ] (실물) Meta AI 앱으로 안경 페어링 + 개발자 모드 ON, 또는 MockDevice 로 먼저 테스트

---

## 참고 링크
- 안드로이드 통합 문서: https://wearables.developer.meta.com/docs/build-integration-android/
- SDK 저장소(예제 포함): https://github.com/facebook/meta-wearables-dat-android
- 소개 글: https://developers.meta.com/blog/introducing-meta-wearables-device-access-toolkit/
