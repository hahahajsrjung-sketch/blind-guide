import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ArtworkForm from '../../components/ArtworkForm.jsx'
import { uploadImage, saveArtwork } from '../../lib/api.js'

// 작품 등록 페이지 (v2 — docs/DATA_PIPELINE.md).
// 흐름: 사진들(+영상) 업로드 → images[{url,kind}] 구성 → Artwork v2로 저장
//       → 서버가 즉시 AI 정리(임베딩 + ai_profile) → 결과 미리보기 표시.
export default function ArtworkNew() {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(null) // 저장 결과 (ai_profile 미리보기용)
  const navigate = useNavigate()

  async function handleSubmit({ values, photos, video }) {
    setSubmitting(true)
    setError('')
    try {
      // 1) 사진을 종류 순서대로 업로드 → {url, kind} 목록.
      const images = []
      for (const kind of ['main', 'angle', 'detail', 'context']) {
        for (const file of photos[kind]) {
          const url = await uploadImage(file)
          images.push({ url, kind })
        }
      }
      // 2) 영상(있으면) 업로드 — 서버가 프레임을 뽑아 각도 사진처럼 쓴다.
      let video_url = ''
      if (video) video_url = await uploadImage(video)

      // 3) Artwork v2 구조로 저장 (image_url 은 대표컷 미러 — 하위호환).
      const result = await saveArtwork({
        ...values,
        images,
        image_url: images[0]?.url || '',
        video_url,
      })
      // 4) AI 정리 결과를 바로 보여준다 (목록 이동은 버튼으로).
      setSaved(result)
    } catch (err) {
      setError(err.message || '저장에 실패했습니다.')
    } finally {
      setSubmitting(false)
    }
  }

  // 저장 완료 화면: AI가 정리한 내용을 작가가 바로 확인.
  if (saved) {
    const ai = saved.ai_profile || {}
    const ing = saved._ingestion || {}
    return (
      <section>
        <h1>저장 완료 — AI가 이렇게 정리했어요</h1>
        <p className="hint">
          이 정리본이 시각장애인 관람객에게 들려줄 설명의 재료가 됩니다.
          사진 {ing.embedded_images ?? 0}장{ing.video_frames ? ` + 영상 장면 ${ing.video_frames}개` : ''}을
          인식용으로 학습해뒀어요.
        </p>

        {ai.safety_notes && (
          <div>
            <h2>⚠️ 안전 안내 (가장 먼저 읽힘)</h2>
            <p>{ai.safety_notes}</p>
          </div>
        )}
        {ai.visual_summary && (
          <div>
            <h2>시각 구성</h2>
            <p>{ai.visual_summary}</p>
          </div>
        )}
        {ai.tactile_summary && (
          <div>
            <h2>촉각·재질감 (색을 본 적 없는 관람객용)</h2>
            <p>{ai.tactile_summary}</p>
          </div>
        )}
        {(ai.key_features || []).length > 0 && (
          <div>
            <h2>구별되는 특징</h2>
            <ul>
              {ai.key_features.map((k, i) => (
                <li key={i}>{k}</li>
              ))}
            </ul>
          </div>
        )}
        {!ai.visual_summary && (
          <p className="msg-err">
            AI 정리를 만들지 못했어요 (저장은 됐습니다). 나중에 다시 시도할 수 있어요.
            {(ing.errors || []).length > 0 && ` — ${ing.errors[0]}`}
          </p>
        )}

        <p style={{ marginTop: 20 }}>
          <button className="btn" onClick={() => navigate('/studio/artworks')}>
            작품 목록 보기
          </button>{' '}
          <button className="btn" onClick={() => setSaved(null)}>
            작품 더 등록
          </button>
        </p>
      </section>
    )
  }

  return (
    <section>
      <h1>작품 등록</h1>
      <p className="hint">
        저장하면 AI가 사진을 학습하고 해설 재료를 정리합니다.
        (이 영역은 나중에 로그인으로 보호됩니다.)
      </p>
      {error && <p className="msg-err">{error}</p>}
      <ArtworkForm onSubmit={handleSubmit} submitting={submitting} />
    </section>
  )
}
