import { Routes, Route } from 'react-router'

import MainLayout from './layouts/MainLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import MaterialsPage from './pages/MaterialsPage'
import CameraPage from './pages/CameraPage'
import InterviewSetupPage from './pages/InterviewSetupPage'
import InterviewPage from './pages/InterviewPage'
import HistoryPage from './pages/HistoryPage'
import ResultPage from './pages/ResultPage'
import GrowthPage from './pages/GrowthPage'

import './App.css'

function App() {
  return (
    <Routes>
      {/* 로그인 페이지는 공통 레이아웃을 사용하지 않음 */}
      <Route path="/login" element={<LoginPage />} />

      {/* 주요 페이지는 MainLayout을 공유 (로그인해야 볼 수 있음) */}
      <Route element={<MainLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/materials" element={<MaterialsPage />} />
        <Route path="/camera" element={<CameraPage />} />
        <Route path="/interview/setup" element={<InterviewSetupPage />} />
        {/* :id 자리에 면접 번호가 들어간다. 예) /interview/3 */}
        <Route path="/interview/:id" element={<InterviewPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/history/:id" element={<ResultPage />} />
        <Route path="/growth" element={<GrowthPage />} />
      </Route>
    </Routes>
  )
}

export default App
