// GrowthPage.jsx
// 성장 분석: 면접 횟수, 평균 점수, 면접별 점수 변화 그래프

import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts'
import { apiRequest } from '../api'
import './GrowthPage.css'

function GrowthPage() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    apiRequest('/api/stats')
      .then((data) => setStats(data))
      .catch((err) => setError(err.message))
  }, [])

  if (error) {
    return <p className="error-message">{error}</p>
  }
  if (!stats) {
    return <p>불러오는 중...</p>
  }

  // map으로 그래프에 넣을 데이터 모양으로 바꾼다
  const chartData = stats.history.map((item, index) => ({
    name: `${index + 1}회차`,
    답변점수: item.average_score,
    자세점수: item.posture_score
  }))

  return (
    <div>
      <div className="page-header">
        <h1>성장 분석</h1>
        <p>면접을 반복하면서 답변과 자세가 어떻게 달라졌는지 확인하세요.</p>
      </div>

      <section className="growth-cards">
        <div className="card">
          <p>총 면접 횟수</p>
          <h2>{stats.total_interviews}회</h2>
        </div>
        <div className="card">
          <p>평균 답변 점수</p>
          <h2>{stats.average_score !== null ? `${stats.average_score}점` : '-'}</h2>
        </div>
        <div className="card">
          <p>평균 자세 점수</p>
          <h2>{stats.average_posture !== null ? `${stats.average_posture}점` : '-'}</h2>
        </div>
        <div className="card">
          <p>최근 면접</p>
          {stats.recent ? (
            <Link to={`/history/${stats.recent.id}`}>
              <h2>{stats.recent.average_score}점</h2>
            </Link>
          ) : (
            <h2>-</h2>
          )}
        </div>
      </section>

      <section className="card">
        <h2>면접별 점수 변화</h2>
        {chartData.length === 0 ? (
          <div className="empty-state">
            <p>완료한 면접이 없습니다. 모의면접을 진행하면 점수 변화가 그래프로 표시됩니다.</p>
            <Link to="/interview/setup" className="button">모의면접 시작하기</Link>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 0, left: -10 }}>
              <CartesianGrid stroke="#edf0f5" vertical={false} />
              <XAxis dataKey="name" padding={{ left: 30, right: 30 }} tick={{ fill: '#697586', fontSize: 13 }} />
              <YAxis domain={[0, 100]} tick={{ fill: '#697586', fontSize: 13 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="답변점수" stroke="#4565b7" strokeWidth={2} dot={{ r: 4 }} isAnimationActive={false} />
              <Line type="monotone" dataKey="자세점수" stroke="#d97706" strokeWidth={2} dot={{ r: 4 }} connectNulls isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
        <p className="notice">※ 답변 점수는 AI, 자세 점수는 카메라 영상 분석으로 계산한 연습용 점수입니다.</p>
      </section>
    </div>
  )
}

export default GrowthPage
