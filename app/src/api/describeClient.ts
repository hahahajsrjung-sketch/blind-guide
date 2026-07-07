import { BACKEND_URL, DESCRIBE_PATH } from "../config";
import { DescribeRequest, DescribeResponse } from "../types";

// 백엔드 POST /describe 호출을 담당하는 유일한 함수.
// 요청/응답 형식만 다루고, 화면 로직은 몰라야 한다.
export async function requestDescription(
  body: DescribeRequest
): Promise<DescribeResponse> {
  const url = `${BACKEND_URL}${DESCRIBE_PATH}`;

  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    // 네트워크 자체 실패 (백엔드 안 켜짐, 주소 틀림 등)
    throw new Error(
      `백엔드에 연결하지 못했습니다 (${url}). 백엔드가 켜져 있는지, 주소가 맞는지 확인하세요.`
    );
  }

  if (!res.ok) {
    throw new Error(`백엔드 오류: HTTP ${res.status}`);
  }

  const data: unknown = await res.json();

  // 응답의 설명 키 이름이 shared 확정 전이라 미정이다.
  // description / text / message 순으로 방어적으로 읽는다.
  const description = extractDescription(data);
  if (description == null) {
    throw new Error("백엔드 응답에서 설명 텍스트를 찾지 못했습니다.");
  }

  return { description };
}

function extractDescription(data: unknown): string | null {
  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>;
    for (const key of ["description", "text", "message"]) {
      if (typeof obj[key] === "string") {
        return obj[key] as string;
      }
    }
  }
  if (typeof data === "string") {
    return data;
  }
  return null;
}
