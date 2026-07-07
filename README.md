# Blind Guide — 시각장애인 안내 AI

AI 안경 카메라로 눈앞의 작품을 보고, 사용자의 **시각 상태에 맞춰** 한국어로 설명해주는 웨어러블 AI.

> "같은 그림도 태어날 때부터 안 보였던 사람과 나중에 시력을 잃은 사람에게는 다르게 설명해야 한다. 특히 색."

## 무엇을 하나

앱(또는 안경)이 이미지를 보내면, 백엔드가 인식→식별→리라이팅을 거쳐 그 사람에게 맞는 설명을 돌려준다.

```
📱 app / 👓 안경
   │  이미지 + user_id
   ▼
┌─────────────────────── 🧠 backend (FastAPI) ───────────────────────┐
│                                                                     │
│  인식 (VLM)          식별                리라이터 (LLM)              │
│  이미지 → 밋밋한 묘사 → 어느 작품인지 대조 → 시각 상태별 맞춤 설명    │
│                          │                    │                     │
│                          ▼                    ▼                     │
│                    작품 저장소 ◄──── onset별 색 규칙 + 길이 규칙      │
└──────────────────────────▲──────────────────────────────────────────┘
                           │ 작품 등록 (POST /artworks)
                        🖥️ website (작가용)
```

핵심은 **리라이터**다. 인식이 뽑은 밋밋한 묘사를, 사용자 프로필의 `onset`(시각 상태)에 따라 다시 쓴다.

## 실제 출력 비교 (같은 작품, 다른 사용자)

작품: 「붉은 들판」 — 지평선까지 이어지는 붉은 양귀비 밭 유화. 실제 테스트 출력이다.

| onset | 색을 어떻게 다루나 | 실제 출력 (발췌) |
|---|---|---|
| `congenital` 선천맹 | 색 이름 대신 온도·질감·문화적 의미 | "…**따뜻한 기운의** 붉은 양귀비 꽃밭… 역사적으로 희생자들을 **기억하고 추모하는 의미**를 지닌 이 꽃들…" |
| `acquired` 중도실명 | 색·시각 표현 그대로 | "…지평선까지 이어지는 넓은 들판은 **온통 붉은색** 양귀비꽃으로 가득…" |
| `unknown` 불명 | 색 이름은 쓰되 해석 없이 중립 | "…**붉은** 양귀비 꽃이 지평선까지 가득 차 있습니다." (short: 2문장) |

작품 식별도 동작한다: 붉은 들판을 닮은 이미지를 `artwork_id` 없이 보내면 카탈로그와 대조해 `art-002`를 찾아내고(`identified: true`), 확신이 없으면 억지로 맞추지 않고 묘사만으로 설명한다.

## 빠른 시작

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # GEMINI_API_KEY 를 넣는다
uvicorn main:app --host 0.0.0.0 --port 8000
```

설명 요청:

```bash
curl -X POST http://localhost:8000/describe \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-blind", "artwork_id": "art-002"}'
```

```json
{
  "user_id": "user-blind",
  "onset": "congenital",
  "artwork_id": "art-002",
  "identified": false,
  "raw_description": "받침대 위에 선 남자 조각상. 대리석.",
  "description": "…선천맹 사용자에게 맞춘 설명…"
}
```

이미지로 식별까지: `"image": "https://…/photo.jpg"` 를 넣고 `artwork_id`를 빼면 된다. 데모 사용자는 `user-blind`(선천맹) / `user-low`(중도실명) / `user-unknown`(불명).

### 작가용 웹사이트

```bash
cd website && npm install && npm run dev   # localhost:5173
```

작품 등록 폼 → `POST /uploads`(사진) → `POST /artworks`(정보) → 앱이 같은 저장소에서 꺼내 쓴다.

### 폰 앱

```bash
cd app && npm install && npx expo start
```

`.env`의 `EXPO_PUBLIC_BACKEND_URL`을 PC의 LAN IP로 두면 실기기에서 붙는다. 버튼 하나 → 설명이 글자 + 한국어 음성(TTS)으로 나온다.

## 구현 현황

| 부분 | 상태 | 내용 |
|---|---|---|
| backend 파이프라인 | ✅ 지금 작동 | 인식(Gemini 비전)→식별→리라이터(Gemini), onset별 색 설명 차이 실측 검증 |
| 작품 등록 API | ✅ 지금 작동 | `/uploads` `/artworks` + CORS. website↔app이 같은 저장소 공유 |
| 작가 웹사이트 | ✅ 지금 작동 | Vite+React. 공개 페이지 + 작품 등록/목록 |
| 폰 앱 | ✅ 지금 작동 | Expo(RN)+TS. 프로필 토글, 설명 수신, TTS(ko-KR), EAS 안드로이드 빌드 준비 |
| 평가셋 인프라 | ✅ 지금 작동 | /describe마다 {profile, raw, output} JSONL 수집 + 재생성 러너 |
| 자체 리라이터 LLM | 🔬 실험 중 | Ollama+EXAONE 3.5 로컬 구동, 정량 평가기·baseline 확보, LoRA 파인튜닝 준비 (`llm/`) |
| AI 안경 (Meta Wearables) | 🔜 준비 중 | provider 구조·네이티브 브리지 골격까지. 실물 페어링은 다음 단계 |
| 실제 DB | 🔜 준비 중 | 지금은 메모리 저장소. 교체 지점만 분리해둠 |
| QR/NFC 태깅 보강 | 🔜 준비 중 | 이미지 식별의 정확도 한계 보완용 |

## 구조

```
blind-guide/
  backend/   FastAPI. 인식→식별→리라이터 + 작품 저장 API
  website/   Vite+React. 작가 작품 등록
  app/       Expo(RN)+TS. 시각장애인용 앱 (TTS, 안경 provider 구조)
  llm/       자체 리라이터 실험 — 로컬 LLM 평가·파인튜닝 파이프라인
  shared/    공유 데이터 구조 (Artwork / UserProfile) — 전 폴더의 기준
  docs/      스펙 문서 (PROJECT_OVERVIEW → TECH_PLAN → 각 SPEC)
```

모든 외부 의존(VLM·LLM·저장소)은 함수 하나로 격리돼 있다: `recognition._vlm_describe` / `recognition._match_llm` / `rewriter.call_llm` / `store`. 나중에 로컬 모델·임베딩·DB로 갈아탈 때 그 함수만 바꾼다.

개발 과정 상세: [DEVELOPMENT.md](DEVELOPMENT.md)

## 로드맵

- [x] 1단계 — 뼈대: 요청→리라이터→맞춤 설명 관통, onset별 차이 검증
- [x] 2단계 — 인식을 진짜로: VLM 묘사 + 작품 식별
- [x] 3단계 — 평가: 수집 훅·평가셋 형식·러너, 로컬 LLM baseline
- [ ] 4단계 — 자체 모델: 프롬프트 한계 확인됨(선천맹 색 규칙) → LoRA 파인튜닝으로 격차 해소
- [ ] 5단계 — 현장: 안경 SDK + 음성, 로컬 서버(젯슨), QR/NFC 태깅, 파일럿(맹학교)

## 왜 만들었나

전시 해설은 "보이는 사람" 기준으로 쓰여 있다. 시각장애인에게 그대로 읽어주면 절반은 닿지 않는다 — 특히 색은, 본 적이 있는 사람과 없는 사람에게 완전히 다른 언어다. 화면해설 작가들이 쌓아온 원칙(객관 묘사, 공간 순서, 지어내지 않기)을 AI에 넣고, 시각 상태별 색 규칙을 얹어, 한 사람 한 사람에게 맞는 해설을 실시간으로 만드는 것이 목표다.

---

🎓 홍익대학교 건축학과 · SightSpace 팀
