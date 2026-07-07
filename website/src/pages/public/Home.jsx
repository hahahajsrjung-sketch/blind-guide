import { Link } from 'react-router-dom'

// 홈: 회사 소개, 우리가 뭘 하는지 한눈에.
export default function Home() {
  return (
    <section>
      <h1>눈앞의 세상을, 당신의 시각에 맞춰 설명합니다</h1>
      <p className="lead">
        Blind Guide 는 시각장애인용 웨어러블 안내 AI 입니다.
        안경 카메라로 눈앞의 대상을 보고, 사용자의 시각 상태에 맞춰
        생생한 한국어로 설명해 줍니다.
      </p>

      <h2>우리가 하는 일</h2>
      <ul>
        <li>안경 카메라가 본 장면을 실시간으로 인식합니다.</li>
        <li>선천맹·중도실명·저시력 등 <strong>시각 상태에 따라 설명을 다르게</strong> 합니다. 특히 색 설명이 다릅니다.</li>
        <li>미술관·전시장의 작품 정보를 미리 등록해 두면, 더 정확하고 풍부하게 안내합니다.</li>
      </ul>

      <p>
        <Link className="btn" to="/service">서비스 자세히 보기</Link>
      </p>
    </section>
  )
}
