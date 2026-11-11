// CameraPanel.jsx
// 카메라 영상과 실시간 영상 분석 결과를 보여 주는 컴포넌트
// 영상 촬영과 분석은 모두 백엔드(라즈베리파이)에서 하고, 이 컴포넌트는 결과만 받아서 보여 준다.
//
// Props
//   compact: true면 분석 수치를 간단하게만 보여 준다 (면접 진행 화면용)

import { useEffect, useState } from 'react'
import { API_URL, apiRequest, getToken } from '../api'
import './CameraPanel.css'

// 백엔드가 보내는 영어 값을 한국어로 바꾸는 표
const DIRECTION_TEXT = {
  front: '정면',
  side: '옆을 봄',
  up: '위를 봄',
  down: '아래를 봄'
}

const DISTANCE_TEXT = {
  good: '적당함',
  far: '너무 멂',
  close: '너무 가까움'
}

function CameraPanel({ compact = false }) {
  const [status, setStatus] = useState(null)       // 서버에서 받은 카메라 상태 + 분석 결과
  const [sources, setSources] = useState({ picamera: false, webcam: true })
  const [source, setSource] = useState('picamera')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [streamKey, setStreamKey] = useState(0)    // 카메라를 다시 켤 때 영상 주소를 새로 만들기 위한 값

  // 처음 화면에 나타날 때: 사용 가능한 카메라 종류 확인
  useEffect(() => {
    apiRequest('/api/camera/sources')
      .then((data) => {
        setSources(data)
        // 라즈베리파이 카메라가 없으면 웹캠을 기본으로 선택
        if (!data.picamera) {
          setSource('webcam')
        }
      })
      .catch((err) => setError(err.message))
  }, [])

  // 0.5초마다 서버에 최신 분석 결과를 요청한다
  useEffect(() => {
    function loadStatus() {
      apiRequest('/api/camera/status')
        .then((data) => setStatus(data))
        .catch(() => {})
    }
    loadStatus()
    const timer = setInterval(loadStatus, 500)

    // 컴포넌트가 사라질 때 타이머를 정리한다 (정리하지 않으면 계속 요청함)
    return () => clearInterval(timer)
  }, [])

  async function handleStart() {
    setLoading(true)
    setError('')
    try {
      const data = await apiRequest('/api/camera/start', 'POST', { source: source })
      setStatus(data)
      setStreamKey(Date.now())
    } catch (err) {
      setError(err.message)
    }
    setLoading(false)
  }

  async function handleStop() {
    const data = await apiRequest('/api/camera/stop', 'POST')
    setStatus(data)
  }

  const running = status && status.running
  const result = status && status.result

  return (
    <div className={compact ? 'camera-panel compact' : 'camera-panel'}>
      <div className="camera-controls">
        <select
          value={source}
          onChange={(event) => setSource(event.target.value)}
          disabled={running}
        >
          <option value="picamera" disabled={!sources.picamera}>
            Raspberry Pi Camera {sources.picamera ? '' : '(감지 안 됨)'}
          </option>
          <option value="webcam">USB 웹캠</option>
        </select>

        {running ? (
          <button type="button" className="button secondary" onClick={handleStop}>
            카메라 끄기
          </button>
        ) : (
          <button type="button" className="button" onClick={handleStart} disabled={loading}>
            {loading ? '켜는 중...' : '카메라 켜기'}
          </button>
        )}
      </div>

      {error && <p className="error-message">{error}</p>}
      {status && status.error && <p className="error-message">{status.error}</p>}

      <div className="camera-view">
        {running ? (
          // 백엔드가 보내는 MJPEG 영상. <img> 태그 하나로 연속된 사진(영상)을 보여 줄 수 있다
          <img
            src={`${API_URL}/api/camera/stream?token=${getToken()}&key=${streamKey}`}
            alt="카메라 영상"
          />
        ) : (
          <p className="camera-off">카메라가 꺼져 있습니다.</p>
        )}
      </div>

      {running && result && (
        <div className="camera-result">
          {result.face_detected ? (
            <>
              <div className={result.facing_front ? 'result-badge good' : 'result-badge warn'}>
                {DIRECTION_TEXT[result.direction]}
              </div>
              <ul className="result-list">
                <li>
                  <span>좌우 회전</span>
                  <strong>{result.yaw}°</strong>
                </li>
                <li>
                  <span>고개 기울기</span>
                  <strong className={result.head_tilted ? 'warn-text' : ''}>{result.roll}°</strong>
                </li>
                {!compact && (
                  <>
                    <li>
                      <span>상하 지수</span>
                      <strong>{result.pitch_ratio}</strong>
                    </li>
                    <li>
                      <span>화면 위치</span>
                      <strong>{result.centered ? '중앙' : '벗어남'}</strong>
                    </li>
                    <li>
                      <span>카메라 거리</span>
                      <strong>{DISTANCE_TEXT[result.distance]}</strong>
                    </li>
                    <li>
                      <span>검출 신뢰도</span>
                      <strong>{Math.round(result.confidence * 100)}%</strong>
                    </li>
                  </>
                )}
              </ul>
            </>
          ) : (
            <div className="result-badge warn">얼굴이 보이지 않음</div>
          )}
          <p className="camera-meta">
            {status.source === 'picamera' ? 'Raspberry Pi Camera' : 'USB 웹캠'} · {status.fps} FPS
            {status.collecting && ' · 면접 분석 기록 중'}
          </p>
        </div>
      )}
    </div>
  )
}

export default CameraPanel
