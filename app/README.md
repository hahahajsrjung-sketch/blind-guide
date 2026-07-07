# app — 시각장애인 안내 앱

PROJECT_OVERVIEW.md, APP_SPEC.md 를 기준으로 만든 앱.
버튼을 누르면 백엔드 `POST /describe` 를 불러 맞춤 설명을 받아 **화면 글자 +
음성(TTS)** 으로 안내한다. 안경·카메라는 아직 자리(stub)만 두고, 폰만으로 동작한다.

## 기술

- Expo (React Native) + TypeScript — iOS / 안드로이드 공용 코드
- 화면 하나: 사용자(시각 상태) 토글 + 버튼 + 결과 표시 + 음성(다시 듣기/멈춤)
- 음성: expo-speech (기기 내장 TTS, 한국어)

## 폴더

```
App.tsx                     앱 루트. MainScreen 하나를 띄움
index.ts                    Expo 진입점
app.json                    Expo 기본 설정 (아이콘·스플래시·번들ID)
app.config.js               동적 설정 (meta 모드일 때 안경 네이티브 플러그인 적용)
eas.json                    EAS 빌드 프로파일 (preview=안드로이드 APK)
assets/                     아이콘·스플래시 (지금은 플레이스홀더)
plugins/withMetaWearables.js  안경 SDK 네이티브 설정 자동 주입 (prebuild 시)
native/android/*.kt         안경 네이티브 모듈 레퍼런스 (Kotlin, dev build 때 복사)
src/
  config.ts                 백엔드 주소 등 설정 (env 에서 읽음, 하드코딩 금지)
  types.ts                  공유 데이터 구조 타입 (shared 확정 시 동기화)
  api/describeClient.ts     POST /describe 호출 (요청/응답만 담당)
  profile/currentProfile.ts 데모 사용자·작품 (나중에 로그인/설정으로 교체)
  screens/MainScreen.tsx    안경 상태 + 사용자 토글 + 버튼 + 결과 + 음성
  features/
    glasses/                안경(웨어러블) 이미지 소스
      types.ts              GlassesProvider 인터페이스
      mockGlassesProvider   하드웨어 없이 가짜 이미지 (기본값)
      metaWearablesProvider Meta 안경 SDK 연동 골격 (네이티브 브리지)
      useGlasses.ts         안경 연결 상태 훅 (init/connect/state)
      index.ts              설정에 따라 provider 선택
    camera/cameraStub.ts    이미지 획득 진입점 (안경 provider로 위임)
    voice/voiceStub.ts      음성 출력 (expo-speech 로 한국어 낭독)
```

> **안경 연동:** 실제 Meta 안경(Ray-Ban Meta 등) 연결은 네이티브 SDK라
> dev build 가 필요하다. 등록·입력·빌드 절차는 [`SETUP.md`](./SETUP.md) 참고.
> 기본값(`EXPO_PUBLIC_GLASSES_PROVIDER=mock`)은 안경 없이 전체 흐름이 돈다.

## 실행

```bash
cd app
cp .env.example .env        # 필요하면 백엔드 주소 수정
npm install
npm start                   # Expo. w=웹, a=안드로이드, i=iOS
```

- 로컬 백엔드로 테스트: `.env` 의 `EXPO_PUBLIC_BACKEND_URL` 을 백엔드 주소로.
- 실제 폰(Expo Go)에서는 `localhost` 대신 PC 의 LAN IP 를 써야 한다 (.env.example 참고).

## 완료 확인

1. 옆 창에서 백엔드를 로컬로 띄운다 (`http://localhost:8000`, `/health` 가 ok).
2. 앱을 실행하고 버튼을 누른다 → 설명이 화면에 글자로 뜬다.
3. 화면 위 사용자 토글(선천맹 / 중도실명)을 바꿔가며 눌러 → 설명이 다르게
   오면 성공. (선천맹은 색을 의미로, 중도실명은 색을 시각 그대로 설명한다.)

## 백엔드 계약 (shared/schema.json, backend/main.py 기준)

- 요청: `POST /describe` 에 `{ user_id, image?, artwork_id? }`.
  프로필은 보내지 않는다 — 백엔드가 `user_id` 로 store 에서 조회한다.
- 데모 user_id: `user-blind`(congenital) / `user-low`(acquired) — store.py 의 PROFILES.
- 데모 artwork_id: `art-001` / `art-002` — store.py 의 ARTWORKS.
- 응답: `{ user_id, onset, artwork_id, raw_description, description }`.
  화면에는 `description` 을 쓴다. (`describeClient.ts` 는 키가 바뀌어도
  description/text/message 순으로 방어적으로 읽는다.)

## 폰에 넣어 빌드 (iOS / 안드로이드)

같은 코드가 두 OS에서 돈다. 방법은 세 가지.

### A. Expo Go — 빌드 없이 즉시 (iOS·안드로이드 둘 다, 가장 쉬움)
1. 폰에 **Expo Go** 설치, PC와 같은 Wi-Fi.
2. `npm start` → 터미널 QR 을 Expo Go(안드로이드) / 카메라(iOS)로 스캔.
3. `.env` 의 `EXPO_PUBLIC_BACKEND_URL` 을 PC LAN IP 로 (폰에선 localhost 불가).

### B. 안드로이드 독립 빌드 (.apk) — EAS 클라우드
```bash
npm i -g eas-cli
eas login
eas build -p android --profile preview   # 설치용 APK 생성 → 링크로 폰에 설치
```
Windows 에서 바로 된다. Android SDK 로 로컬 빌드하려면 `npx expo run:android`.

### C. iOS 독립 빌드 (.ipa) — **애플 환경 필요**
- Windows 에서는 iOS 실기기 빌드를 만들 수 없다 (애플 정책).
- 필요: **Mac + Xcode**, 또는 **EAS + Apple Developer 계정(연 $99)**.
  ```bash
  eas build -p ios --profile preview      # Apple 계정 로그인 요구
  ```
- 계정이 준비되기 전까지 iOS 는 위 A(Expo Go)로 확인한다.

> 아이콘·스플래시(assets/)는 지금 플레이스홀더다. 실제 출시 전 교체한다.
```
