import { Link } from 'react-router-dom'

// 서비스: 시각장애인을 위한 안내 AI가 무엇인지 설명.
export default function Service() {
  return (
    <section>
      <h1>서비스 소개</h1>

      <h2>시각 상태에 맞춘 설명</h2>
      <p>
        같은 장면도 사용자의 시각 경험에 따라 다르게 전달해야 합니다.
        Blind Guide 는 사용자의 시각 상태(선천맹·중도실명·불명)와
        관심사, 원하는 설명 길이를 프로필로 받아 설명을 맞춤 생성합니다.
      </p>

      <h2>작품 안내</h2>
      <p>
        작가나 전시 담당자가 작품 정보를 미리 등록하면, 사용자가 그 작품을
        비출 때 등록된 정보를 바탕으로 더 정확하게 설명합니다.
        설명 글을 비워 두면 AI 가 사진과 기본 정보로 설명을 만듭니다.
      </p>

      <h2>어떻게 동작하나</h2>
      <ol>
        <li>작가가 이 웹사이트에서 작품 정보를 등록합니다.</li>
        <li>사용자가 안경으로 작품을 비춥니다.</li>
        <li>AI 가 작품을 인식하고, 시각 상태에 맞는 설명을 들려줍니다.</li>
      </ol>

      <p>
        <Link className="btn" to="/studio/artworks/new">작가라면, 작품 등록하기</Link>
      </p>
    </section>
  )
}
