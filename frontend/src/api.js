// api.js
// 백엔드(FastAPI) 서버에 요청을 보내는 함수를 모아 둔 파일

// 백엔드 주소. 라즈베리파이에서 백엔드를 실행하면 frontend/.env 파일에
// VITE_API_URL=http://라즈베리파이IP:8000 처럼 적어 준다.
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// 로그인 토큰은 브라우저의 localStorage에 저장한다 (새로고침해도 유지됨)
export function getToken() {
  return localStorage.getItem('naro_token')
}

export function saveToken(token) {
  localStorage.setItem('naro_token', token)
}

export function removeToken() {
  localStorage.removeItem('naro_token')
}

// 서버에 요청을 보내고 JSON 응답을 돌려준다.
// 예) apiRequest('/api/materials')                       → GET 요청
//     apiRequest('/api/materials', 'POST', { title: ... }) → POST 요청
export async function apiRequest(path, method = 'GET', body = null) {
  const options = {
    method: method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`
    }
  }
  if (body) {
    options.body = JSON.stringify(body)
  }

  let response
  try {
    response = await fetch(API_URL + path, options)
  } catch {
    throw new Error('서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인해 주세요.')
  }

  // 토큰이 없거나 만료되었으면 로그인 페이지로 보낸다
  if (response.status === 401 && path !== '/api/login') {
    removeToken()
    window.location.href = '/login'
    throw new Error('로그인이 필요합니다.')
  }

  const data = await response.json()
  if (!response.ok) {
    // FastAPI는 오류 메시지를 detail에 담아 보낸다
    throw new Error(data.detail || '요청을 처리하지 못했습니다.')
  }
  return data
}

// 날짜 문자열을 "2026. 11. 11. 오후 9:30" 같은 한국어 형식으로 바꾼다
export function formatDate(dateText) {
  return new Date(dateText).toLocaleString('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short'
  })
}
