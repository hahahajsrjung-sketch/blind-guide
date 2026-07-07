# DEVELOPMENT — 개발 기록

시각장애인용 웨어러블 안내 AI **blind-guide** 를 어떻게 만들었는지 정리한 문서.
무엇을 만드는지는 [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md), 각 부분의
작업 지시는 docs/ 의 SPEC 문서들이 기준이다.

## 1. 핵심 아이디어

안경 카메라로 눈앞의 대상(주로 전시 작품)을 보고, 사용자의 **시각 상태(onset)** 에
맞춰 한국어 설명을 다르게 만들어 음성으로 들려준다. 특히 **색 설명**이 갈린다:

- `congenital`(선천맹) — 색 이름 대신 온도·질감·문화적 의미 같은 교차감각으로.
- `acquired`(중도실명) — 색과 시각 표현을 그대로.
- `unknown`(불명) — 색 이름은 쓰되 해석은 얹지 않고 중립적으로.

## 2. 구조 — 네 개의 창(폴더)

각 창(Claude Code 세션)이 자기 폴더에만 코드를 넣는 규칙으로 병행 개발했다.
공유 데이터 구조(Artwork / UserProfile)는 `shared/schema.json` 하나가 기준이고,
모든 폴더가 이를 따른다.

```
blind-guide/
  docs/      스펙 문서 (PROJECT_OVERVIEW가 최상위 기준)
  shared/    공유 데이터 구조 (schema.json + README)
  backend/   1번 창 — FastAPI. 인식→식별→리라이터 파이프라인 + 작품 저장 API
  website/   2번 창 — Vite+React. 회사 소개 + 작가 작품 등록 페이지
  app/       3번 창 — Expo(React Native)+TS. 시각장애인용 폰 앱
  llm/       4번 창 — 자체 리라이터 LLM 실험·평가·파인튜닝 파이프라인
```

### 데이터 흐름

```
[작가] website 등록폼 → POST /uploads → POST /artworks → backend 메모리 저장
[사용자] app 버튼 → POST /describe {user_id, image?, artwork_id?}
         → backend: 프로필 조회 → 인식(VLM 묘사) → 작품 식별 → 리라이터(onset별 규칙)
         → app: 설명을 화면 글자 + 한국어 TTS 로 출력
```

## 3. 부분별 개발 내용

### backend (FastAPI + Gemini)
- `main.py` — `POST /describe`(핵심 파이프라인), `POST /uploads`(로컬 저장, 절대 URL 반환),
  `POST /artworks`·`GET /artworks`(웹사이트용), `GET /health`. CORS 전체 허용(뼈대 단계).
- 파이프라인을 교체 가능한 조각으로 분리:
  - `recognition.py` — 이미지→밋밋한 묘사. 지금은 **Gemini 비전** 재사용(`_vlm_describe`만
    나중에 로컬 VLM로 교체). 이미지가 없거나 자리표시자면 고정 묘사로 폴백.
    묘사→작품 식별(`identify`)도 여기 — 확신 없으면 None(억지로 안 맞춤, 나중 QR/NFC 보강).
  - `rewriter.py` + `prompts.py` — onset별 색 규칙·길이 규칙을 프롬프트로 조립,
    `call_llm`만 분리(지금 Gemini → 나중 자체 모델로 태그만 교체).
  - `store.py` — 예시 작품·프로필 메모리 저장소(나중 실제 DB 자리).
  - `eval_log.py` — /describe마다 (profile, raw, 출력) JSONL 기록. 평가셋 씨앗. best-effort.
- 비밀값(GEMINI_API_KEY)은 환경변수/.env로만. 코드 하드코딩 없음.

### website (Vite + React, JS)
- 공개 페이지(`/`, `/service`)와 작가 입력(`/studio/artworks/new`, `/studio/artworks`) 분리.
  `/studio/*`는 나중 로그인 가드 자리.
- 백엔드 호출은 `src/lib/api.js` 한 곳(uploadImage/saveArtwork/listArtworks).
  주소는 `VITE_BACKEND_URL` env. 업로드→저장→목록 순환이 backend와 실제로 도는 것 검증.

### app (Expo React Native + TypeScript)
- 화면 하나: 사용자(시각 상태) 토글 + "눈앞을 설명해줘" 버튼 + 결과 영역 + 음성 컨트롤.
- 설명 수신 시 **글자 + expo-speech 한국어 TTS** 동시 출력. 오류도 음성 안내.
  큰 버튼·accessibilityLabel 등 접근성 우선.
- 경계 분리: `api/describeClient.ts`(HTTP), `features/voice`(TTS),
  `features/glasses`(안경 이미지 소스 — `GlassesProvider` 인터페이스에 mock/meta 두 구현),
  `features/camera`(provider로 위임). 설정은 `EXPO_PUBLIC_*` env.
- **Meta 안경 연동 준비**: Meta Wearables Device Access Toolkit(안드로이드 v0.8.0)용
  네이티브 브리지 계약(`MetaWearablesProvider`), Expo config plugin
  (`plugins/withMetaWearables.js` — 권한/메타데이터/gradle 자동 주입, meta 모드에서만),
  Kotlin 모듈 레퍼런스(`native/android/`). 실물 페어링 전 절차는 `app/SETUP.md`.
  네이티브 SDK라 Expo Go 불가 → dev build 필요.
- **안드로이드 APK**: EAS 클라우드 빌드로 실기기 설치용 .apk 생성 완료
  (`eas build -p android --profile preview`). iOS 실기기 빌드는 Windows에서 불가
  (Mac 또는 Apple Developer 계정 필요) — 그전엔 Expo Go로 확인.

### llm (자체 리라이터 실험)
- 목표: 리라이터를 Gemini에서 **자체(로컬) 모델**로 교체. 데스크탑 RTX 5070 Ti 16GB로
  로컬 확정, Ollama + EXAONE 3.5 (7.8B 주, 2.4B 대조군).
- `scripts/try_local.py` — backend의 prompts를 그대로 import해 call_llm만 Ollama로 교체
  (전환 가능성 실증).
- **평가**: `data/evalset.jsonl` 15개(같은 raw에 onset만 다른 쌍 포함),
  `scripts/eval_local.py` 가 규칙 위반(선천맹 색누출·길이초과·안전문구 오적용·인사말투)을
  greedy(temp0) 재현 가능하게 채점. baseline 수치 기록(notes.md).
- **핵심 발견**: 프롬프트 개선(v2, few-shot+제약)으로 길이/안전/인사말은 거의 잡히지만
  (13→3, 7→1, 5→0 /15) **선천맹 색누출은 프롬프트로 안 잡힘(4/6 불변)** → 파인튜닝 정당화.
- **증류 파이프라인**: `rule_repair.py`(결정론 보정) → `gen_sft_data.py`(교사 생성,
  평가셋 겹침 제외) → 사람 감수 → `build_chat_dataset.py`(backend 원본 프롬프트로 채팅
  형식화 — 규칙을 가중치에 내재화해 backend 프롬프트 불변 목표) →
  `finetune/train_lora.py`(Unsloth+TRL, QLoRA, GPU 박스에서 실행).
- 발견한 함정 기록: v2 프롬프트를 Ollama Modelfile로 "구우면" 퇴화(few-shot 되뱉기) —
  호출 시 메시지로 전달이 정본.

## 4. 검증 방법

- **계약 검증**: 4개 폴더 전부 `shared/schema.json`과 대조(필드명·enum·필수여부 일치 확인).
- **완료 기준 검증**: 같은 작품에 onset만 바꿔 호출 → 색 설명이 실제로 다르게 오는 것 확인
  (선천맹=의미/온도로, 중도실명=색 그대로). 앱 클라이언트 코드로 라이브 백엔드 호출도 통과.
- **기계 검증**: backend/llm `py_compile`, website Vite 빌드, app `tsc`+안드로이드 번들,
  expo-doctor 18/18.
- **LLM 정량 평가**: greedy 고정 재현 가능한 규칙 채점기(eval_local)로 개선 전후 비교.

## 5. 전체 코드 리뷰와 수정 (2026-07-08)

병렬 리뷰(백엔드/웹사이트/llm/계약 일치) 후 실제 오류만 수정. 수정 후 컴파일·빌드·라이브
API 재검증 완료.

| 위치 | 문제 | 수정 |
|---|---|---|
| backend/recognition.py | 이미지 URL 읽기 실패 시 조용히 고정 묘사로 폴백 → 엉뚱한 설명·오식별(art-001로 오인) | 실제 이미지 입력인데 못 읽으면 명시적 오류(502)로 |
| backend/main.py | 없는 artwork_id 를 검증 없이 에코 | 프로필과 동일하게 404 |
| backend/recognition.py | 식별 LLM이 `art-002.` 처럼 부호 붙이면 매칭 실패 | 문장부호 정리 후 매칭 |
| backend/main.py | /uploads 가 async인데 블로킹 파일 I/O → 업로드 중 전체 요청 정지 | 동기 def(스레드풀) |
| backend/eval_log.py | 동시 요청 시 JSONL append 줄 섞임 가능 | 쓰기 락 |
| llm/build_chat_dataset.py | `--auto-only` 미리보기가 실제 학습 파일을 덮어씀 → 감수 안 된 데이터로 학습될 뻔 | 미리보기는 `*.preview.jsonl` 로 분리(기존 파일도 rename) |
| llm/train_lora.py | 신형 TRL에서 `tokenizer=` 인자명 변경으로 시작 실패 가능 | `processing_class` 폴백 |
| llm/eval_local.py | length 값 오타 시 출력부 KeyError | `.get` 으로 방어 |
| llm/eval_local.py ↔ rule_repair.py | 안전 단서 목록 불일치(생성기/채점기 판정 어긋남) | 목록 동기화(evalset 미등장 단어라 baseline 불변) |
| app/types.ts, website/artwork.js | "shared/ 비어 있음" 낡은 주석 | 실제 상태로 갱신 |

리뷰에서 확인만 하고 수정 안 한 것:
- `llm/train_lora.py` 마스킹 마커 — 리뷰 시점엔 ChatML 하드코딩(EXAONE와 불일치 = 학습 무효
  위험)이었으나 llm 창이 이미 config 기반 + 하드 검증으로 수정 완료.
- `docs/PROJECT_OVERVIEW.md` 1절 서술("선천맹, 중도실명, **저시력**")과 4절 enum
  (`congenital/acquired/unknown`) 불일치 — 스펙 문서라 코드에서 임의 수정하지 않음.
  **unknown(불명)이 구현 기준**이니 문서 서술을 맞추길 권장.
- website 작품 카드 `<img src={image_url}>` — 백엔드가 절대 URL을 반환해 현재는 문제
  없음. 백엔드가 상대 경로로 바뀌면 BASE 접두 방어가 필요.

## 6. 지금 상태와 남은 일

동작함 (뼈대 완성 + 일부 진짜):
- 업로드→작품 저장→목록→맞춤 설명의 전체 관이 실제로 돈다.
- 인식은 진짜 VLM(Gemini 비전), 식별은 LLM 대조(확신 없으면 안 맞춤), 리라이터는
  Gemini + onset 규칙. 앱은 APK로 실기기 설치 가능.

남은 일:
- [ ] Gemini 월 지출 한도 초과 상태(429) — AI Studio에서 한도 조정 또는 키 교체
- [ ] 실기기에서 앱 화면·음성 최종 확인 (APK 설치 후)
- [ ] 백엔드를 `--host 0.0.0.0` 으로 띄워 폰에서 접근 가능하게
- [ ] llm: `train.review.jsonl` 사람 감수 → train.jsonl 확정 → GPU 박스에서 LoRA 학습
- [ ] 실제 DB (지금은 메모리 — 재시작 시 초기화)
- [ ] Meta 안경 실물 페어링 (app/SETUP.md 절차)
- [ ] 로그인, 위치 태깅, CORS 좁히기 (배포 전)
