// HistoryPage.jsx
// 지금까지 진행한 면접 목록

import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { apiRequest, formatDate } from '../api'
import './HistoryPage.css'

function HistoryPage() {
  const [interviews, setInterviews] = useState([])
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    apiRequest('/api/interviews')
      .then((data) => {
        setInterviews(data)
        setLoaded(true)
      })
      .catch((err) => setError(err.message))
  }, [])

  async function handleDelete(id) {
    if (!window.confirm('이 면접 기록을 삭제할까요?')) {
      return
    }
    try {
      await apiRequest(`/api/interviews/${id}`, 'DELETE')
      setInterviews((prev) => prev.filter((item) => item.id !== id))
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>면접 기록</h1>
        <p>이전 면접을 선택하면 답변, AI 피드백, 영상 분석 결과를 다시 볼 수 있어요.</p>
      </div>

      {error && <p className="error-message">{error}</p>}

      {loaded && interviews.length === 0 && (
        <div className="empty-state">
          <p>아직 진행한 면접이 없습니다.</p>
          <Link to="/interview/setup" className="button">첫 모의면접 시작하기</Link>
        </div>
      )}

      <div className="history-list">
        {interviews.map((item) => (
          <div className="card history-item" key={item.id}>
            <Link
              to={item.status === 'completed' ? `/history/${item.id}` : `/interview/${item.id}`}
              className="history-link"
            >
              <h3>
                {item.company} · {item.position}
                {item.is_demo && <span className="demo-badge">데모</span>}
              </h3>
              <p className="notice">
                {item.interview_type} · {formatDate(item.created_at)}
              </p>
            </Link>

            <div className="history-scores">
              {item.status === 'completed' ? (
                <>
                  <span>답변 <strong>{item.average_score}점</strong></span>
                  <span>자세 <strong>{item.posture_score !== null ? `${item.posture_score}점` : '-'}</strong></span>
                </>
              ) : (
                <span className="notice">진행 중</span>
              )}
              <button type="button" className="button danger" onClick={() => handleDelete(item.id)}>
                삭제
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default HistoryPage
