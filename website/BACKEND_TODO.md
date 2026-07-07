# 백엔드 창에 요청하는 것 (website → backend)

website 창은 backend 폴더를 직접 건드리지 않는다.
아래 엔드포인트가 backend 에 필요하다. WEBSITE_SPEC 5번 근거.
저장 형식은 PROJECT_OVERVIEW 4번의 **Artwork 공유 구조**를 따른다.

## 필요한 엔드포인트

### POST /uploads
- 이미지 파일 업로드 (multipart/form-data, 필드명 `file`).
- 저장 후 `{ "image_url": "..." }` 반환.
- 이번 단계엔 로컬 폴더 저장으로 충분 (WEBSITE_SPEC 6번).

### POST /artworks
- 본문(JSON): `{ image_url, title, artist, material, size, year, description }`
- `id` 는 백엔드가 자동 부여.
- Artwork 구조로 저장소에 저장. 저장된 작품(또는 id) 반환.

### GET /artworks
- 저장된 작품 목록 반환. 배열 또는 `{ "artworks": [...] }` 둘 다 허용됨(웹은 둘 다 처리).

## CORS
- 개발 중 `http://localhost:5173` (Vite dev 서버)에서의 요청을 허용해야 함.

## 연동 흐름
작가 폼 제출 → website 가 POST /uploads → POST /artworks 호출 →
backend 저장소에 Artwork 저장 → 나중에 app 요청 시 같은 저장소에서 꺼내 씀.
