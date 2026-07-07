import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ArtworkForm from '../../components/ArtworkForm.jsx'
import { uploadImage, saveArtwork } from '../../lib/api.js'

// 작품 등록 페이지.
// 흐름: 사진 업로드 → image_url 획득 → Artwork 구조로 백엔드에 저장.
export default function ArtworkNew() {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  async function handleSubmit({ values, file }) {
    setSubmitting(true)
    setError('')
    try {
      // 1) 사진을 백엔드로 보내 저장 위치를 받는다.
      const image_url = await uploadImage(file)
      // 2) Artwork 구조로 저장 요청 (id 는 백엔드가 부여).
      await saveArtwork({ ...values, image_url })
      // 3) 방금 넣은 작품을 목록에서 확인.
      navigate('/studio/artworks')
    } catch (err) {
      setError(err.message || '저장에 실패했습니다.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section>
      <h1>작품 등록</h1>
      <p className="hint">
        입력한 작품은 백엔드에 Artwork 구조로 저장됩니다.
        (이 영역은 나중에 로그인으로 보호됩니다.)
      </p>
      {error && <p className="msg-err">{error}</p>}
      <ArtworkForm onSubmit={handleSubmit} submitting={submitting} />
    </section>
  )
}
