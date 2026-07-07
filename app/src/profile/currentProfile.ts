import { UserProfile } from "../types";

// 데모용 사용자 목록.
//
// 백엔드는 요청의 user_id 로 프로필(onset 등)을 store 에서 조회한다.
// 그래서 "시각 상태를 바꾸면 설명이 달라진다"를 확인하려면, store 에 실제로
// 들어 있는 user_id 로 바꿔가며 호출하면 된다.
// (backend/store.py 의 PROFILES 와 user_id 를 맞춘다.)
//
// 나중에 로그인/설정 화면으로 교체할 자리. 지금은 화면에서 토글해서 확인한다.
export interface DemoUser {
  label: string; // 화면 표시용
  profile: UserProfile;
}

export const DEMO_USERS: DemoUser[] = [
  {
    label: "선천맹",
    profile: {
      user_id: "user-blind",
      onset: "congenital",
      interest: "역사",
      length: "medium",
    },
  },
  {
    label: "중도실명",
    profile: {
      user_id: "user-low",
      onset: "acquired",
      interest: "회화",
      length: "medium",
    },
  },
];

// 데모로 비추는 작품. 지금은 카메라/인식이 가짜라, 어느 작품인지 직접 지정한다.
// (backend/store.py 의 ARTWORKS 에 있는 id. art-002 는 작가 설명이 있어 설명이 풍부하다.)
export const DEMO_ARTWORK_ID = "art-002";
