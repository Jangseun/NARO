
import { Routes, Route, Link } from 'react-router'

import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import MaterialsPage from './pages/MaterialsPage'
import InterviewSetupPage from './pages/InterviewSetupPage'
import HistoryPage from './pages/HistoryPage'
import GrowthPage from './pages/GrowthPage'

function App() {
  return (
    <div>
      <nav>
        <Link to="/">홈</Link> |{' '}
        <Link to="/login">로그인</Link> |{' '}
        <Link to="/materials">자료 관리</Link> |{' '}
        <Link to="/interview/setup">모의면접</Link> |{' '}
        <Link to="/history">면접 기록</Link> |{' '}
        <Link to="/growth">성장 분석</Link>
      </nav>

      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/materials" element={<MaterialsPage />} />
        <Route path="/interview/setup" element={<InterviewSetupPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/growth" element={<GrowthPage />} />
      </Routes>
    </div>
  )
}

export default App
