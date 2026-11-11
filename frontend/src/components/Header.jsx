import { NavLink, useNavigate } from 'react-router'
import { removeToken } from '../api'

function Header() {
  const navigate = useNavigate()

  function handleLogout() {
    removeToken()
    navigate('/login')
  }

  return (
    <header className="header">
      <NavLink to="/" className="logo">
        NARO
      </NavLink>

      <nav className="navigation">
        <NavLink to="/" end>홈</NavLink>
        <NavLink to="/camera">영상 분석</NavLink>
        <NavLink to="/materials">자료 관리</NavLink>
        <NavLink to="/interview/setup">모의면접</NavLink>
        <NavLink to="/history">면접 기록</NavLink>
        <NavLink to="/growth">성장 분석</NavLink>
        <button type="button" className="logout-button" onClick={handleLogout}>
          로그아웃
        </button>
      </nav>
    </header>
  )
}

export default Header
