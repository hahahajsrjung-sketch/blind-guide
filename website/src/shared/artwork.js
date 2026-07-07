// Artwork 공유 구조의 폼용 미러.
//
// 진짜 정의는 프로젝트 루트의 shared/schema.json (v2 확장: docs/DATA_PIPELINE.md).
// 이 파일은 등록 폼이 쓰는 표시용 미러 — shared 가 바뀌면 여기도 같이 바꾼다.
//
// v2 요약:
//  - images[{url, kind}]: 여러 각도 사진. kind = main/angle/detail/context. 임베딩 식별의 재료.
//  - video_url: 작품 주위를 도는 짧은 영상(선택). 서버가 프레임을 추출해 각도 컷처럼 씀.
//  - tactile/safety/location/intent: 시각장애인 해설에 꼭 필요한 작가 지식.
//  - ai_profile: 서버가 등록 시 자동 생성(폼에는 없음, 결과 미리보기로만 표시).

// 기본 정보 필드 (id 제외).
export const ARTWORK_FIELDS = [
  { key: 'title', label: '제목', type: 'text' },
  { key: 'artist', label: '작가명', type: 'text' },
  { key: 'material', label: '재질', type: 'text' },
  { key: 'size', label: '크기', type: 'text' },
  { key: 'year', label: '제작연도', type: 'text' },
  { key: 'description', label: '작품 설명 글 (선택)', type: 'textarea' },
]

// v2: 시각장애인 해설을 위한 추가 필드. hint 는 폼에 그대로 노출된다.
export const ACCESS_FIELDS = [
  {
    key: 'tactile',
    label: '촉각·재질감 (권장)',
    type: 'textarea',
    hint: '만졌을 때의 느낌을 적어주세요. 예: "차갑고 매끈한 대리석", "울퉁불퉁한 붓자국". 색을 본 적 없는 관람객에게 색 대신 전달되는 핵심 정보입니다.',
  },
  {
    key: 'safety',
    label: '안전·관람 규칙 (권장)',
    type: 'text',
    hint: '예: "만지면 안 됩니다", "받침대가 낮아 발에 걸릴 수 있어요". 설명에서 가장 먼저 안내됩니다.',
  },
  {
    key: 'location',
    label: '전시 위치 (권장)',
    type: 'text',
    hint: '예: "2전시실 입구 왼쪽 벽"',
  },
  {
    key: 'intent',
    label: '작가 의도 (선택)',
    type: 'textarea',
    hint: '한두 문장이면 충분해요. 해석을 강요하지 않고 맥락으로만 쓰입니다.',
  },
]

// 사진 종류 안내 (docs/DATA_PIPELINE.md 1.1 촬영 가이드).
export const PHOTO_KINDS = [
  { kind: 'main', label: '대표 사진', required: true, multiple: false,
    hint: '정면, 좋은 조명 1장. 작품이 화면의 60% 이상 차지하게.' },
  { kind: 'angle', label: '각도 사진', required: false, multiple: true,
    hint: '좌/우 30~45도에서 2~4장. 관람객은 정면에서 찍지 않아요 — 인식 정확도를 크게 올립니다.' },
  { kind: 'detail', label: '세부 사진', required: false, multiple: true,
    hint: '질감·붓터치·재질 근접 촬영 0~2장.' },
  { kind: 'context', label: '설치 전경', required: false, multiple: false,
    hint: '벽·받침대·주변이 함께 나오게 1장. 실제 관람 시야와 가장 비슷합니다.' },
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
    tactile: '',
    safety: '',
    location: '',
    intent: '',
  }
}
