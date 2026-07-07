# 공유 데이터 구조

백엔드와 웹사이트가 **반드시 똑같이 봐야 하는** 데이터 구조다. 기계용 정의는 [`schema.json`](./schema.json)에 있고, 이 문서는 사람이 읽는 설명이다. 어느 쪽 창에서 작업하든 이 구조를 어기지 않는다.

기준 문서는 상위 폴더의 `docs/PROJECT_OVERVIEW.md` 4번이다. 충돌하면 그쪽이 우선.

## Artwork (작품)

작가가 웹사이트에서 저장하고, 백엔드가 인식·설명 재료로 쓴다.

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `id` | string | ✅ | 고유 번호. 시스템이 자동 부여. |
| `image_url` | string | ✅ | 작품 사진 URL. 이미지 인식의 기준이자 설명 재료. |
| `title` | string | | 제목. |
| `artist` | string | | 작가명. |
| `material` | string | | 재질. |
| `size` | string | | 크기. |
| `year` | string | | 제작연도. |
| `description` | string | | 작가가 직접 쓴 설명 글. 없으면 백엔드가 사진과 기본 정보로 생성. |

## UserProfile (사용자 프로필)

시각 상태(`onset`)에 따라 설명, 특히 색 설명이 달라진다. 이 프로젝트의 핵심 차별점.

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `user_id` | string | ✅ | 고유 번호. |
| `onset` | enum | ✅ | 시각 상태. `congenital` / `acquired` / `unknown` 중 하나. |
| `interest` | string | | 관심사. 없어도 됨. |
| `length` | enum | ✅ | 설명 길이 취향. `short` / `medium` / `long` 중 하나. |

### onset 값

- `congenital` — 선천맹. 색을 시각 기억으로 설명하지 않는다.
- `acquired` — 중도실명. 색과 시각적 표현을 그대로 써도 된다.
- `unknown` — 불명. 색 이름은 쓰되 해석은 얹지 않고 중립적으로.

### length 값

- `short` — 한두 문장.
- `medium` — 서너 문장.
- `long` — 네다섯 문장.

## 현재 단계 메모

이 두 구조는 지금 백엔드가 코드 안 예시 데이터(`backend/store.py`)로 갖고 있다. 나중에 실제 데이터베이스로 옮긴다. 웹사이트가 작품을 저장하면 이 `Artwork` 구조로 저장된다.
