# 백엔드 — 시각장애인 안내 AI

안경 앱에서 이미지와 사용자 정보가 오면, 이미지를 인식해 밋밋한 묘사를 얻고, 사용자의 시각 상태에 맞춰 다시 써서 설명을 돌려준다.

기준 문서: 상위 `docs/PROJECT_OVERVIEW.md`, `docs/BACKEND_SPEC.md`. 공유 데이터 구조: `../shared/`.

## 요청 흐름

```
앱      → POST /describe  → 프로필/작품 조회 → 인식(가짜) → 리라이터(Gemini) → JSON → 앱
웹사이트 → POST /uploads   → 이미지 저장 → image_url 반환
        → POST /artworks  → Artwork 저장 (앱이 나중에 같은 저장소에서 꺼내 씀)
        → GET  /artworks  → 작품 목록
```

## 파일

| 파일 | 역할 |
|------|------|
| `main.py` | API 입구(FastAPI). `POST /describe`, `GET /health`, 작품 CRUD. 파이프라인 조립. |
| `recognition.py` | 인식. VLM(Gemini 비전)으로 이미지→묘사 + 묘사→작품 식별(`identify`). `_vlm_describe`/`_match_llm`만 교체하면 로컬 VLM·임베딩·태그로 전환. |
| `rewriter.py` | 리라이터. 프롬프트 조립 + `call_llm`(Gemini). `call_llm`만 교체하면 모델 교체. |
| `prompts.py` | 시스템 프롬프트 + onset별 색 규칙 + 길이 규칙. |
| `store.py` | 작품/프로필 예시 데이터 + 조회/저장 함수. 나중에 DB로 교체. |
| `config.py` | API 키·모델명을 환경변수에서 읽음. `.env` 있으면 자동 로드. |
| `eval_log.py` | 평가셋 수집 로그 훅(best-effort). `eval/` 참고. |
| `eval/` | 평가셋 인프라(3단계). 형식·러너·로그. `eval/README.md` 참고. |

## 실행

```bash
pip install -r requirements.txt

# 키 설정: .env.example 을 복사해 .env 로 만들고 실제 키를 넣거나, 환경변수로 직접 지정.
cp .env.example .env   # 그다음 .env 안 GEMINI_API_KEY 를 실제 키로 수정

uvicorn main:app --reload
```

서버: `http://127.0.0.1:8000` · 자동 문서: `http://127.0.0.1:8000/docs`

## API

### `POST /describe`

요청 바디:

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `user_id` | string | ✅ | 사용자 프로필 키. |
| `image` | string | | 이미지 URL 또는 data URI(base64). 있으면 VLM으로 인식, 없으면 고정 묘사 폴백. |
| `artwork_id` | string | | 어느 작품인지 알 때. 없고 image가 실제 이미지면 묘사로 자동 식별 시도(확신 없으면 컨텍스트 없이 진행). |

응답 예:

```json
{
  "user_id": "user-blind",
  "onset": "congenital",
  "artwork_id": "art-002",
  "identified": false,
  "raw_description": "받침대 위에 선 남자 조각상. 대리석.",
  "description": "…시각 상태에 맞춰 다시 쓴 설명…"
}
```

`identified` — artwork_id를 요청이 준 게 아니라 이미지로 식별해 찾았으면 `true`.

에러: 없는 `user_id` → 404, LLM 호출 실패 → 502, 설정 문제(키 없음 등) → 500.

### `POST /uploads` (웹사이트)

이미지 파일 업로드. `multipart/form-data`, 필드명 `file`. 저장 후 `{ "image_url": "..." }` 반환. 저장 위치는 `backend/uploads/`, 같은 서버가 `/uploads/<파일명>`으로 제공.

### `POST /artworks` (웹사이트)

본문 JSON: `{ image_url(필수), title, artist, material, size, year, description }`. `id`는 백엔드가 자동 부여. 저장된 Artwork 반환.

### `GET /artworks` (웹사이트)

`{ "artworks": [ ...Artwork ] }` 반환.

> 주의: 지금 저장소는 메모리(`store.py`)라 서버를 재시작하면 새로 올린 작품은 사라지고 예시 데이터로 돌아간다. 나중에 DB로 교체하면 영속된다.

## 예시 데이터 (store.py)

작품: `art-001`(작가 설명 없음), `art-002`(작가 설명 있음).
사용자: `user-blind`(congenital), `user-low`(acquired), `user-unknown`(unknown).

같은 작품이라도 onset에 따라 색 설명이 달라지는 것이 이 프로젝트의 핵심이다.

## 교체 예정 자리

- `recognition._vlm_describe()` — Gemini 비전 → 로컬 오픈소스 VLM(Qwen2-VL 등). 다음: 묘사에서 작품 식별까지(이미지 우선, QR/NFC 태깅 보강).
- `store` — 코드 안 예시 데이터 → 실제 DB(웹사이트가 저장한 작품이 들어온다).
- `rewriter.call_llm()` — Gemini API → 로컬/파인튜닝 모델(EXAONE·HyperCLOVA·Qwen3·Gemma 후보).
