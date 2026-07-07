import { Link, Outlet } from 'react-router-dom'

// 공통 헤더/네비 + 페이지 본문 자리(Outlet).
export default function Layout() {
  return (
    <div className="page">
      <header className="nav">
        <Link to="/" className="brand">Blind Guide</Link>
        <nav>
          <Link to="/">홈</Link>
          <Link to="/service">서비스</Link>
          <span className="sep">|</span>
          <Link to="/studio/artworks/new">작품 등록</Link>
          <Link to="/studio/artworks">작품 목록</Link>
        </nav>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <footer className="foot">시각장애인용 웨어러블 안내 AI · 뼈대 단계</footer>
    </div>
  )
}
