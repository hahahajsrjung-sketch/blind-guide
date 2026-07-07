// 백엔드 호출을 이 파일 한 곳에 모은다 (WEBSITE_SPEC 4·5번).
// 웹사이트는 작품을 직접 저장하지 않고 백엔드에 요청만 한다.
//
// 백엔드 창에 필요한 엔드포인트 (BACKEND_TODO.md 참고):
//   POST /artworks            작품 저장 (Artwork 구조). id 는 백엔드가 부여.
//   GET  /artworks            저장된 작품 목록
//   POST /uploads             이미지 파일 업로드 → { image_url } 반환

const BASE = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

async function jsonOrThrow(res) {
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`백엔드 요청 실패 (${res.status}): ${text}`)
  }
  return res.json()
}

// 사진 업로드 → 저장된 위치(image_url)를 돌려받는다.
export async function uploadImage(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/uploads`, { method: 'POST', body: form })
  const data = await jsonOrThrow(res)
  return data.image_url
}

// 작품을 Artwork 구조로 저장 요청.
export async function saveArtwork(artwork) {
  const res = await fetch(`${BASE}/artworks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(artwork),
  })
  return jsonOrThrow(res)
}

// 저장된 작품 목록.
export async function listArtworks() {
  const res = await fetch(`${BASE}/artworks`)
  return jsonOrThrow(res)
}
