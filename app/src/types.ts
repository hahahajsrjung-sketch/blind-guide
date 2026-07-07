// 공유 데이터 구조를 앱 쪽에서 보는 타입 정의.
//
// 기준: shared/schema.json (+ PROJECT_OVERVIEW.md 4번 "공유 데이터 구조").
// 이 파일은 그 정의를 TS 로 옮긴 것 — shared 가 바뀌면 여기도 같이 바꾼다.

// 시각 상태. 문서 4번: congenital(선천맹) / acquired(중도실명) / unknown(불명)
export type Onset = "congenital" | "acquired" | "unknown";

// 설명 길이 취향.
export type DescriptionLength = "short" | "medium" | "long";

// 사용자 프로필 (UserProfile)
export interface UserProfile {
  user_id: string;
  onset: Onset;
  interest?: string; // 관심사. 없어도 됨.
  length: DescriptionLength;
}

// POST /describe 요청 본문.
// 실제 백엔드(backend/main.py DescribeRequest)에 맞춘 형태:
//   user_id(필수), image(선택·자리만), artwork_id(선택).
// 프로필은 요청에 넣지 않는다 — 백엔드가 user_id 로 store 에서 조회한다.
export interface DescribeRequest {
  user_id: string;
  image?: string; // 지금은 카메라 자리만 — 가짜 placeholder 문자열
  artwork_id?: string;
}

// POST /describe 응답. 백엔드(backend/main.py)가 돌려주는 형태.
// 화면에 쓰는 건 description 하나지만, 나머지도 참고용으로 둔다.
export interface DescribeResponse {
  description: string;
  user_id?: string;
  onset?: Onset;
  artwork_id?: string;
  raw_description?: string;
}
