// Artwork 공유 구조 (PROJECT_OVERVIEW.md 4번 기준).
//
// ⚠️ 임시 미러: 원래는 프로젝트 루트의 shared/ 폴더가 진짜 정의를 갖는다.
// 지금 shared/ 가 비어 있어(backend 창이 채울 예정) 여기 미러링해 둔다.
// shared/ 가 채워지면 이 파일을 지우고 그걸 import 하도록 교체한다.
//
// 필드:
//  - id: 시스템 자동 부여 (폼에는 없음)
//  - image_url: 작품 사진. 필수. 이미지 인식 기준이자 설명 재료.
//  - title, artist, material, size, year
//  - description: 작가가 직접 쓴 설명. 선택.

// 등록 폼에서 받는 필드 (id 제외).
export const ARTWORK_FIELDS = [
  { key: 'title', label: '제목', type: 'text', required: false },
  { key: 'artist', label: '작가명', type: 'text', required: false },
  { key: 'material', label: '재질', type: 'text', required: false },
  { key: 'size', label: '크기', type: 'text', required: false },
  { key: 'year', label: '제작연도', type: 'text', required: false },
  { key: 'description', label: '설명 글 (선택)', type: 'textarea', required: false },
]

// 폼 초기값.
export function emptyArtwork() {
  return {
    title: '',
    artist: '',
    material: '',
    size: '',
    year: '',
    description: '',
  }
}
