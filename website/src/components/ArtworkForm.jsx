import { useState } from 'react'
import { ARTWORK_FIELDS, ACCESS_FIELDS, PHOTO_KINDS, emptyArtwork } from '../shared/artwork.js'

// 작품 등록 폼 UI (v2 — docs/DATA_PIPELINE.md).
// 사진(대표 필수 + 각도/세부/전경 권장) + 영상(선택) + 기본 정보 + 접근성 정보.
// 제출 로직은 부모(ArtworkNew)가 onSubmit 으로 넘긴다.
export default function ArtworkForm({ onSubmit, submitting }) {
  const [values, setValues] = useState(emptyArtwork())
  // kind별 파일 목록: { main: [File], angle: [File, ...], detail: [...], context: [...] }
  const [photos, setPhotos] = useState({ main: [], angle: [], detail: [], context: [] })
  const [video, setVideo] = useState(null)
  const [error, setError] = useState('')

  function update(key, v) {
    setValues((prev) => ({ ...prev, [key]: v }))
  }

  function updatePhotos(kind, fileList, multiple) {
    const files = Array.from(fileList || [])
    setPhotos((prev) => ({ ...prev, [kind]: multiple ? files : files.slice(0, 1) }))
  }

  const photoCount = Object.values(photos).reduce((n, arr) => n + arr.length, 0)

  function handleSubmit(e) {
    e.preventDefault()
    setError('')
    // 대표 사진은 필수 (이미지 인식 기준이자 설명 재료).
    if (photos.main.length === 0) {
      setError('대표 사진은 필수입니다.')
      return
    }
    onSubmit({ values, photos, video })
  }

  return (
    <form className="form" onSubmit={handleSubmit}>
      <h2>1. 작품 사진</h2>
      <p className="hint">
        사진이 많을수록, 각도가 다양할수록 관람객의 카메라가 작품을 더 정확히 알아봅니다.
        폰 카메라면 충분해요. 유리 반사는 피해주세요.
      </p>

      {PHOTO_KINDS.map((pk) => (
        <div key={pk.kind}>
          <label>
            {pk.label} {pk.required && <span className="req">*</span>}
          </label>
          <input
            type="file"
            accept="image/*"
            multiple={pk.multiple}
            onChange={(e) => updatePhotos(pk.kind, e.target.files, pk.multiple)}
          />
          <p className="hint">
            {pk.hint}
            {photos[pk.kind].length > 0 && ` — ${photos[pk.kind].length}장 선택됨`}
          </p>
        </div>
      ))}

      <label>영상 (선택 — 사진 대신·추가로)</label>
      <input
        type="file"
        accept="video/*"
        onChange={(e) => setVideo(e.target.files?.[0] || null)}
      />
      <p className="hint">
        작품 주위를 10~20초 천천히 도는 영상 1개. 서버가 여러 장면을 뽑아 각도 사진처럼 씁니다.
        {video && ` — ${video.name}`}
      </p>

      <h2>2. 기본 정보</h2>
      {ARTWORK_FIELDS.map((f) => (
        <div key={f.key}>
          <label>{f.label}</label>
          {f.type === 'textarea' ? (
            <textarea value={values[f.key]} onChange={(e) => update(f.key, e.target.value)} />
          ) : (
            <input type="text" value={values[f.key]} onChange={(e) => update(f.key, e.target.value)} />
          )}
        </div>
      ))}

      <h2>3. 눈이 아닌 감각으로 — 시각장애인 관람객을 위한 정보</h2>
      <p className="hint">
        이 칸이 이 서비스의 심장입니다. 색을 본 적 없는 관람객에게는 촉감·온도·소리가 색의 언어가 됩니다.
      </p>
      {ACCESS_FIELDS.map((f) => (
        <div key={f.key}>
          <label>{f.label}</label>
          {f.type === 'textarea' ? (
            <textarea value={values[f.key]} onChange={(e) => update(f.key, e.target.value)} />
          ) : (
            <input type="text" value={values[f.key]} onChange={(e) => update(f.key, e.target.value)} />
          )}
          <p className="hint">{f.hint}</p>
        </div>
      ))}

      {error && <p className="msg-err">{error}</p>}

      <p style={{ marginTop: 20 }}>
        <button className="btn" type="submit" disabled={submitting}>
          {submitting
            ? '저장하고 AI가 정리하는 중… (사진이 많으면 잠시 걸려요)'
            : `작품 저장 (사진 ${photoCount}장${video ? ' + 영상' : ''})`}
        </button>
      </p>
    </form>
  )
}
