// InterviewSetupPage.jsx
// 모의면접 설정: 지원 기업, 직무, 면접 유형, 질문 개수, 참고 자료를 고르고 면접을 시작한다

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { apiRequest } from '../api'
import CameraPanel from '../components/CameraPanel'
import './InterviewSetupPage.css'

function InterviewSetupPage() {
  const navigate = useNavigate()

  const [company, setCompany] = useState('')
  const [position, setPosition] = useState('')
  const [interviewType, setInterviewType] = useState('종합 면접')
  const [questionCount, setQuestionCount] = useState(3)
  const [materials, setMaterials] = useState([])
  const [selectedIds, setSelectedIds] = useState([])   // 체크한 자료의 id 목록
  const [demoMode, setDemoMode] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    apiRequest('/api/materials')
      .then((data) => setMaterials(data))
      .catch((err) => setError(err.message))
    apiRequest('/api/me')
      .then((data) => setDemoMode(data.demo_mode))
      .catch(() => {})
  }, [])

  // 자료 체크박스를 누르면 선택 목록에 넣거나 뺀다
  function toggleMaterial(id) {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((selectedId) => selectedId !== id))
    } else {
      setSelectedIds([...selectedIds, id])
    }
  }

  async function handleStart(event) {
    event.preventDefault()
    if (!company.trim() || !position.trim()) {
      setError('지원 기업과 직무를 입력해 주세요.')
      return
    }

    setLoading(true)
    setError('')
    try {
      // 백엔드가 AI로 질문을 만들고, 새 면접 정보를 돌려준다
      const interview = await apiRequest('/api/interviews', 'POST', {
        company: company,
        position: position,
        interview_type: interviewType,
        question_count: Number(questionCount),
        material_ids: selectedIds
      })
      navigate(`/interview/${interview.id}`)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>모의면접 설정</h1>
        <p>지원 정보를 입력하면 AI가 맞춤형 면접 질문을 만들어 드려요.</p>
      </div>

      <div className="setup-layout">
        <form className="setup-form card" onSubmit={handleStart}>
          {demoMode && (
            <p className="demo-badge">
              데모 모드: OpenAI API 키가 없어 정해진 질문 틀로 질문을 만듭니다
            </p>
          )}

          <label>
            지원 기업
            <input
              type="text"
              placeholder="예: 나로전자"
              value={company}
              onChange={(event) => setCompany(event.target.value)}
            />
          </label>

          <label>
            지원 직무
            <input
              type="text"
              placeholder="예: 소프트웨어 개발"
              value={position}
              onChange={(event) => setPosition(event.target.value)}
            />
          </label>

          <div className="setup-row">
            <label>
              면접 유형
              <select value={interviewType} onChange={(event) => setInterviewType(event.target.value)}>
                <option value="인성 면접">인성 면접</option>
                <option value="직무 면접">직무 면접</option>
                <option value="종합 면접">종합 면접</option>
              </select>
            </label>

            <label>
              질문 개수
              <input
                type="number"
                min={1}
                max={10}
                value={questionCount}
                onChange={(event) => setQuestionCount(event.target.value)}
              />
            </label>
          </div>

          <div>
            <p className="setup-label">참고할 자료</p>
            {materials.length === 0 && (
              <p className="notice">등록한 자료가 없습니다. 자료 관리에서 자기소개서를 먼저 등록하면 더 맞춤형 질문이 만들어져요.</p>
            )}
            <div className="material-checks">
              {materials.map((material) => (
                <label key={material.id} className="material-check">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(material.id)}
                    onChange={() => toggleMaterial(material.id)}
                  />
                  <span>[{material.type}] {material.title}</span>
                </label>
              ))}
            </div>
          </div>

          {error && <p className="error-message">{error}</p>}

          <button type="submit" className="button" disabled={loading}>
            {loading ? 'AI가 질문을 만드는 중...' : '면접 시작하기'}
          </button>
        </form>

        <div>
          <CameraPanel compact />
          <p className="notice">
            카메라를 켜 두면 면접 중 고개 방향과 자세를 분석해 피드백에 반영합니다.
          </p>
        </div>
      </div>
    </div>
  )
}

export default InterviewSetupPage
