import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Home from './pages/public/Home.jsx'
import Service from './pages/public/Service.jsx'
import ArtworkNew from './pages/studio/ArtworkNew.jsx'
import ArtworkList from './pages/studio/ArtworkList.jsx'

// 공개 영역(/)과 입력 영역(/studio)을 분리한다.
// 나중에 /studio/* 만 로그인 가드로 감싸면 된다 (아래 주석 자리).
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        {/* 공개 영역 */}
        <Route path="/" element={<Home />} />
        <Route path="/service" element={<Service />} />

        {/* 입력 영역 — 나중에 여기를 <RequireLogin> 로 감싼다 */}
        <Route path="/studio/artworks/new" element={<ArtworkNew />} />
        <Route path="/studio/artworks" element={<ArtworkList />} />
      </Route>
    </Routes>
  )
}
