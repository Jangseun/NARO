// InterviewPage.jsx
// 모의면접 진행: 질문을 하나씩 보여 주고 답변을 저장한다.
// 답변을 저장할 때마다 백엔드는 그 질문에 답하는 동안의 카메라 분석 결과도 함께 저장한다.

import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { apiRequest } from '../api'
import CameraPanel from '../components/CameraPanel'
import './InterviewPage.css'

// 크롬 브라우저의 음성 인식 기능 (지원하지 않는 브라우저에서는 undefined)
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition

function InterviewPage() {
  const { id } = useParams()          // 주소 /interview/3 에서 3을 꺼낸다
  const navigate = useNavigate()

  const [interview, setInterview] = useState(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [lastVision, setLastVision] = useState(null)  // 방금 답한 질문의 자세 분석 요약
  const [saving, setSaving] = useState(false)
  const [finishing, setFinishing] = useState(false)
  const [listening, setListening] = useState(false)
  const [needRetry, setNeedRetry] = useState(false)   // 답변은 저장됐지만 AI 피드백 요청이 실패한 상태
  const [error, setError] = useState('')
  const recognitionRef = useRef(null)

  useEffect(() => {
    apiRequest(`/api/interviews/${id}`)
      .then((data) => {
        if (data.status === 'completed') {
          navigate(`/history/${id}`)
          return
        }
        setInterview(data)
        // 이미 답한 질문은 건너뛰고, 아직 답하지 않은 첫 질문부터 시작한다
        const firstEmpty = data.answers.findIndex((item) => item.answer === null)
        setCurrentIndex(firstEmpty === -1 ? data.answers.length - 1 : firstEmpty)
      })
      .catch((err) => setError(err.message))
  }, [id, navigate])

  // 음성 입력 시작/중지
  function toggleListening() {
    if (listening) {
      recognitionRef.current.stop()
      return
    }
    const recognition = new SpeechRecognition()
    recognition.lang = 'ko-KR'
    recognition.continuous = true       // 말을 멈춰도 계속 듣기
    recognition.interimResults = false  // 확정된 문장만 받기

    // 문장이 인식될 때마다 답변 입력창 뒤에 붙인다
    recognition.onresult = (event) => {
      const lastResult = event.results[event.results.length - 1]
      const text = lastResult[0].transcript
      setAnswer((prev) => (prev ? prev + ' ' : '') + text.trim())
    }
    recognition.onerror = (event) => setError(`음성 인식 오류: ${event.error}`)
    recognition.onend = () => setListening(false)

    recognition.start()
    recognitionRef.current = recognition
    setListening(true)
  }

  // 면접 종료: 백엔드가 AI 피드백 + 영상 분석 요약을 만든다
  async function finishInterview() {
    setFinishing(true)
    setError('')
    try {
      await apiRequest(`/api/interviews/${id}/complete`, 'POST')
      navigate(`/history/${id}`)
    } catch (err) {
      setError(err.message)
      setFinishing(false)
      setNeedRetry(true)
    }
  }

  async function handleNext() {
    if (listening) {
      recognitionRef.current.stop()
    }
    setSaving(true)
    setError('')
    try {
      const question = interview.answers[currentIndex]
      const data = await apiRequest(`/api/interviews/${id}/answers`, 'POST', {
        order: question.order,
        answer: answer
      })
      setLastVision(data.vision_stats)
      setAnswer('')
      setSaving(false)

      if (currentIndex === interview.answers.length - 1) {
        await finishInterview()     // 마지막 질문이면 면접 종료
      } else {
        setCurrentIndex(currentIndex + 1)
      }
    } catch (err) {
      setError(err.message)
      setSaving(false)
    }
  }

  if (!interview) {
    return error ? <p className="error-message">{error}</p> : <p>면접을 불러오는 중...</p>
  }

  const total = interview.answers.length
  const isLast = currentIndex === total - 1
  const question = interview.answers[currentIndex]

  return (
    <div>
      <div className="page-header">
        <h1>
          {interview.company} · {interview.position}
        </h1>
        <p>
          {interview.interview_type}
          {interview.is_demo && <span className="demo-badge"> 데모 모드 질문</span>}
        </p>
      </div>

      <div className="interview-layout">
        <div className="interview-main card">
          <div className="progress-bar">
            <div style={{ width: `${((currentIndex + 1) / total) * 100}%` }} />
          </div>
          <p className="question-number">
            질문 {currentIndex + 1} / {total}
          </p>
          <h2 className="question-text">{question.question}</h2>

          <textarea
            rows={9}
            placeholder="답변을 입력하거나 음성 입력 버튼을 눌러 말해 보세요."
            value={answer}
            onChange={(event) => setAnswer(event.target.value)}
            disabled={finishing || needRetry}
          />

          {error && <p className="error-message">{error}</p>}

          <div className="interview-buttons">
            {SpeechRecognition ? (
              <button
                type="button"
                className={listening ? 'button danger' : 'button secondary'}
                onClick={toggleListening}
                disabled={finishing}
              >
                {listening ? '■ 음성 입력 중지' : '🎤 음성 입력'}
              </button>
            ) : (
              <span className="notice">이 브라우저는 음성 입력을 지원하지 않습니다 (크롬 권장)</span>
            )}

            {finishing && (
              <button type="button" className="button" disabled>
                AI가 피드백을 만드는 중...
              </button>
            )}
            {/* AI 피드백 요청이 실패했을 때: 답변은 이미 저장됐으니 피드백만 다시 요청한다 */}
            {!finishing && needRetry && (
              <button type="button" className="button" onClick={finishInterview}>
                피드백 다시 요청하기
              </button>
            )}
            {!finishing && !needRetry && (
              <button type="button" className="button" onClick={handleNext} disabled={saving}>
                {isLast ? '답변 저장 후 면접 종료' : '다음 질문'}
              </button>
            )}
          </div>

          {lastVision && lastVision.front_ratio !== undefined && (
            <p className="last-vision">
              직전 답변 자세: 정면 {Math.round(lastVision.front_ratio * 100)}% · 자세 점수{' '}
              {lastVision.posture_score}점
            </p>
          )}
        </div>

        <CameraPanel compact />
      </div>
    </div>
  )
}

export default InterviewPage
