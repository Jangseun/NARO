import { Navigate, Outlet } from 'react-router'
import Header from '../components/Header'
import { getToken } from '../api'

function MainLayout() {
  // 로그인 토큰이 없으면 주요 페이지 대신 로그인 페이지로 보낸다
  if (!getToken()) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="app-layout">
      <Header />

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}

export default MainLayout
