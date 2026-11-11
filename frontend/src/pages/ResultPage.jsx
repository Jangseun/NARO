// ResultPage.jsx
// 면접 결과 상세: 영상(자세) 분석 요약 + AI 답변 피드백을 보여 준다

import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { apiRequest, formatDate } from '../api'
import './ResultPage.css'

// 0.83 → "83%" 처럼 비율을 퍼센트 글자로 바꾼다
function percent(value) {
  return `${Math.round(value * 100)}%`
}

// 영상 분석 요약 수치를 카드 형태로 보여 주는 작은 컴포넌트
function VisionStats({ stats }) {
  if (!stats || stats.front_ratio === undefined) {
    return <p className="notice">카메라 분석 데이터가 없습니다.</p>
  }
  return (
    <ul className="vision-stats">
      <li><span>정면 응시</span><strong>{percent(stats.front_ratio)}</strong></li>
      <li><span>고개 숙임</span><strong>{percent(stats.down_ratio)}</strong></li>
      <li><span>옆을 봄</span><strong>{percent(stats.side_ratio)}</strong></li>
      <li><span>고개 기울어짐</span><strong>{percent(stats.tilt_ratio)}</strong></li>
      <li><span>얼굴 인식</span><strong>{percent(stats.face_detect_ratio)}</strong></li>
      <li><span>움직임 지수</span><strong>{stats.movement}</strong></li>
    </ul>
  )
}

function ResultPage() {
  const { id } = useParams()
  const [interview, setInterview] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    apiRequest(`/api/interviews/${id}`)
      .then((data) => setInterview(data))
      .catch((err) => setError(err.message))
  }, [id])

  if (error) {
    return <p className="error-message">{error}</p>
  }
  if (!interview) {
    return <p>결과를 불러오는 중...</p>
  }

  if (interview.status !== 'completed') {
    return (
      <div className="empty-state">
        <p>아직 끝나지 않은 면접입니다.</p>
        <Link to={`/interview/${id}`} className="button">이어서 진행하기</Link>
      </div>
    )
  }

  return (
    <div className="result-page">
      <div className="page-header">
        <h1>
          {interview.company} · {interview.position}
        </h1>
        <p>
          {interview.interview_type} · {formatDate(interview.created_at)}{' '}
          {interview.is_demo && <span className="demo-badge">데모 모드 결과 (실제 AI 평가 아님)</span>}
        </p>
      </div>

      <section className="score-cards">
        <div className="card score-card">
          <p>답변 점수 (AI)</p>
          <h2>{interview.average_score}점</h2>
        </div>
        <div className="card score-card">
          <p>자세 점수 (영상 분석)</p>
          <h2>{interview.posture_score !== null ? `${interview.posture_score}점` : '-'}</h2>
        </div>
      </section>
      <p className="notice">
        ※ 점수는 연습용 참고 지표이며, 실제 면접 합격 가능성을 나타내지 않습니다.
      </p>

      <section className="card">
        <h2>📷 영상 분석 결과</h2>
        <VisionStats stats={interview.vision_summary} />
        <ul className="tip-list">
          {interview.vision_feedback.map((tip) => (
            <li key={tip}>{tip}</li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>💬 종합 피드백</h2>
        <p className="feedback-text">{interview.overall_feedback}</p>
      </section>

      <h2 className="section-title">질문별 결과</h2>
      {interview.answers.map((item) => (
        <section className="card answer-card" key={item.order}>
          <div className="answer-top">
            <h3>Q{item.order}. {item.question}</h3>
            <span className="answer-score">{item.score}점</span>
          </div>

          <p className="answer-text">{item.answer || '(답변 없음)'}</p>

          {item.feedback && (
            <div className="feedback-grid">
              <div>
                <p className="criteria">
                  질문 의도 {item.feedback.relevance}/5 · 구체성 {item.feedback.specificity}/5 · 논리성{' '}
                  {item.feedback.logic}/5
                </p>
                <p><strong>잘한 점</strong> {item.feedback.good_points}</p>
                <p><strong>개선할 점</strong> {item.feedback.improvements}</p>
                <p><strong>개선 답변 예시</strong> {item.feedback.better_answer}</p>
              </div>
              <div>
                <p className="criteria">이 질문에 답하는 동안의 자세</p>
                <VisionStats stats={item.vision_stats} />
              </div>
            </div>
          )}
        </section>
      ))}

      <Link to="/history" className="button secondary">목록으로</Link>
    </div>
  )
}

export default ResultPage
