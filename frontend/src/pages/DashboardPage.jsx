
import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { apiRequest, formatDate } from '../api'
import './DashboardPage.css'

function DashboardPage() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  // 화면이 처음 나타날 때 한 번만 통계를 불러온다
  useEffect(() => {
    apiRequest('/api/stats')
      .then((data) => setStats(data))
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div className="dashboard">
      <section className="dashboard-hero">
        <span className="dashboard-eyebrow">
          MY INTERVIEW SPACE
        </span>

        <h1>오늘도 나답게, 한 걸음 더.</h1>
        <p>
          라즈베리파이 카메라가 자세를, AI가 답변을 분석해 드려요.
        </p>

        <Link to="/interview/setup" className="start-button">
          모의면접 시작하기
        </Link>
      </section>

      {error && <p className="error-message">{error}</p>}

      <section className="dashboard-stats">
        <div className="stat-card">
          <p>누적 면접</p>
          <h2>{stats ? stats.total_interviews : '-'}회</h2>
        </div>

        <div className="stat-card">
          <p>저장한 자료</p>
          <h2>{stats ? stats.materials_count : '-'}개</h2>
        </div>

        <div className="stat-card">
          <p>최근 면접</p>
          {stats && stats.recent ? (
            <Link to={`/history/${stats.recent.id}`} className="recent-link">
              <h2>{stats.recent.average_score}점</h2>
              <span>
                {stats.recent.company} · {formatDate(stats.recent.created_at)}
              </span>
            </Link>
          ) : (
            <h2>없음</h2>
          )}
        </div>
      </section>

      <section className="dashboard-menu">
        <h2>빠른 메뉴</h2>

        <div className="menu-grid">
          <Link to="/camera" className="menu-card wide">
            <span className="menu-icon">📷</span>
            <h3>영상 분석</h3>
            <p>라즈베리파이 카메라로 고개 방향과 자세를 실시간 확인하기</p>
          </Link>

          <Link to="/interview/setup" className="menu-card">
            <span className="menu-icon">🎙️</span>
            <h3>모의면접</h3>
            <p>AI와 함께 실전처럼 연습하기</p>
          </Link>

          <Link to="/materials" className="menu-card">
            <span className="menu-icon">📁</span>
            <h3>자료 관리</h3>
            <p>자기소개서와 면접 자료 관리하기</p>
          </Link>

          <Link to="/history" className="menu-card">
            <span className="menu-icon">📋</span>
            <h3>면접 기록</h3>
            <p>이전 면접 결과 다시 확인하기</p>
          </Link>

          <Link to="/growth" className="menu-card">
            <span className="menu-icon">📈</span>
            <h3>성장 분석</h3>
            <p>면접 실력의 변화 확인하기</p>
          </Link>
        </div>
      </section>
    </div>
  )
}

export default DashboardPage
