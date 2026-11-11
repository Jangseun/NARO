
import { useState } from 'react'
import { useNavigate } from 'react-router'
import { apiRequest, saveToken } from '../api'
import './LoginPage.css'

function LoginPage() {
  const navigate = useNavigate()

  const [username, setUsername] = useState('')  // 아이디 상태관리.
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()        // 폼 제출 시 페이지 새로고침 방지.

    if (!username.trim() || !password) {
      setMessage('아이디와 비밀번호를 모두 입력해 주세요.')
      return
    }

    // 백엔드에 아이디/비밀번호를 보내 확인받는다
    setMessage('로그인 중...')
    try {
      const data = await apiRequest('/api/login', 'POST', {
        username: username.trim(),
        password: password
      })
      saveToken(data.token)   // 받은 토큰을 저장해 두고 이후 요청마다 함께 보낸다
      navigate('/')
    } catch (error) {
      setMessage(error.message)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <div className="login-symbol">✦</div>
          <h1>NARO</h1>
          <p>가장 나다운 모습으로 나아가다.</p>
        </div>

        <div className="login-intro">
          <h2>다시 만나서 반가워요!</h2>
          <p>나만의 AI 모의면접 공간에 로그인하세요.</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="username">아이디</label>
            <input
              id="username"
              type="text"
              placeholder="아이디를 입력하세요"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </div>

          <div className="form-field">
            <label htmlFor="password">비밀번호</label>

            <div className="password-input-wrapper">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="비밀번호를 입력하세요"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />

              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? '숨기기' : '표시'}
              </button>
            </div>
          </div>

          {message && (
            <p className="login-message" role="status">
              {message}
            </p>
          )}

          <button type="submit" className="login-button">
            로그인
          </button>
        </form>

        <p className="login-footer">
          오늘도 한 걸음, 나다운 모습으로.
        </p>
      </div>
    </div>
  )
}

export default LoginPage
