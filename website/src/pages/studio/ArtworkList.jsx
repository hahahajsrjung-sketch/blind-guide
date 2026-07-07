import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listArtworks } from '../../lib/api.js'

// 작품 목록: 등록된 작품 확인.
export default function ArtworkList() {
  const [items, setItems] = useState([])
  const [status, setStatus] = useState('loading') // loading | ok | error
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    listArtworks()
      .then((data) => {
        if (!alive) return
        // 백엔드가 배열 또는 { artworks: [...] } 로 줄 수 있어 둘 다 받는다.
        const list = Array.isArray(data) ? data : data.artworks || []
        setItems(list)
        setStatus('ok')
      })
      .catch((err) => {
        if (!alive) return
        setError(err.message)
        setStatus('error')
      })
    return () => {
      alive = false
    }
  }, [])

  return (
    <section>
      <h1>작품 목록</h1>
      <p>
        <Link className="btn" to="/studio/artworks/new">새 작품 등록</Link>
      </p>

      {status === 'loading' && <p>불러오는 중…</p>}
      {status === 'error' && (
        <p className="msg-err">목록을 불러오지 못했습니다: {error}</p>
      )}
      {status === 'ok' && items.length === 0 && (
        <p className="hint">아직 등록된 작품이 없습니다.</p>
      )}

      <div className="card-grid">
        {items.map((a) => (
          <div className="card" key={a.id ?? a.image_url}>
            <img src={a.image_url} alt={a.title || '작품 이미지'} />
            <div className="body">
              <h3>{a.title || '(제목 없음)'}</h3>
              <p>{a.artist || '작가 미상'}</p>
              <p>{[a.material, a.size, a.year].filter(Boolean).join(' · ')}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
