import { useState } from 'react'
import { ARTWORK_FIELDS, emptyArtwork } from '../shared/artwork.js'

// 작품 등록 폼 UI. 사진(필수) + Artwork 필드.
// 제출 로직은 부모(ArtworkNew)가 onSubmit 으로 넘긴다.
export default function ArtworkForm({ onSubmit, submitting }) {
  const [values, setValues] = useState(emptyArtwork())
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')

  function update(key, v) {
    setValues((prev) => ({ ...prev, [key]: v }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    setError('')
    // 사진은 필수 (이미지 인식 기준이자 설명 재료).
    if (!file) {
      setError('작품 사진은 필수입니다.')
      return
    }
    onSubmit({ values, file })
  }

  return (
    <form className="form" onSubmit={handleSubmit}>
      <label>
        작품 사진 <span className="req">*</span>
      </label>
      <input
        type="file"
        accept="image/*"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <p className="hint">이미지 인식의 기준이자 설명 재료입니다. 필수.</p>

      {ARTWORK_FIELDS.map((f) => (
        <div key={f.key}>
          <label>{f.label}</label>
          {f.type === 'textarea' ? (
            <textarea
              value={values[f.key]}
              onChange={(e) => update(f.key, e.target.value)}
            />
          ) : (
            <input
              type="text"
              value={values[f.key]}
              onChange={(e) => update(f.key, e.target.value)}
            />
          )}
        </div>
      ))}

      {error && <p className="msg-err">{error}</p>}

      <p style={{ marginTop: 20 }}>
        <button className="btn" type="submit" disabled={submitting}>
          {submitting ? '저장 중…' : '작품 저장'}
        </button>
      </p>
    </form>
  )
}
