
import { useEffect, useState } from 'react'
import { apiRequest, formatDate } from '../api'
import './MaterialsPage.css'

const MATERIAL_TYPES = ['자기소개서', '기업 정보', '직무 정보', '기타 면접 자료']

function MaterialsPage() {
  const [materials, setMaterials] = useState([])
  const [title, setTitle] = useState('')
  const [type, setType] = useState('자기소개서')
  const [content, setContent] = useState('')
  const [editingId, setEditingId] = useState(null)   // 수정 중인 자료 id (null이면 새 자료 등록)
  const [error, setError] = useState('')

  // 서버에서 자료 목록을 불러온다
  function loadMaterials() {
    apiRequest('/api/materials')
      .then((data) => setMaterials(data))
      .catch((err) => setError(err.message))
  }

  // 화면이 처음 나타날 때 목록을 불러온다
  useEffect(() => {
    loadMaterials()
  }, [])

  function resetForm() {
    setTitle('')
    setType('자기소개서')
    setContent('')
    setEditingId(null)
  }

  async function handleSubmit(event) {
    event.preventDefault()

    if (!title.trim() || !content.trim()) {
      setError('제목과 내용을 모두 입력해 주세요.')
      return
    }

    const body = { title: title, type: type, content: content }
    try {
      if (editingId) {
        await apiRequest(`/api/materials/${editingId}`, 'PUT', body)   // 수정
      } else {
        await apiRequest('/api/materials', 'POST', body)                // 새로 등록
      }
      setError('')
      resetForm()
      loadMaterials()
    } catch (err) {
      setError(err.message)
    }
  }

  // 수정 버튼: 선택한 자료의 내용을 입력창에 채운다
  function handleEdit(material) {
    setEditingId(material.id)
    setTitle(material.title)
    setType(material.type)
    setContent(material.content)
    window.scrollTo(0, 0)
  }

  async function handleDelete(id) {
    if (!window.confirm('이 자료를 삭제할까요?')) {
      return
    }
    try {
      await apiRequest(`/api/materials/${id}`, 'DELETE')
      // filter로 삭제한 자료만 빼고 목록을 다시 만든다
      setMaterials((prev) => prev.filter((material) => material.id !== id))
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="materials-page">
      <div className="page-header">
        <h1>자료 관리</h1>
        <p>AI가 면접 질문을 만들 때 참고할 자기소개서, 기업·직무 정보를 등록하세요.</p>
      </div>

      <form className="material-form card" onSubmit={handleSubmit}>
        <h2>{editingId ? '자료 수정' : '새 자료 등록'}</h2>

        <div className="material-form-row">
          <input
            type="text"
            placeholder="자료 제목 (예: 나로전자 자기소개서)"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />

          <select value={type} onChange={(event) => setType(event.target.value)}>
            {MATERIAL_TYPES.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </div>

        <textarea
          rows={8}
          placeholder="자료 내용을 붙여 넣으세요. 내용이 구체적일수록 맞춤형 질문이 만들어집니다."
          value={content}
          onChange={(event) => setContent(event.target.value)}
        />

        {error && <p className="error-message">{error}</p>}

        <div className="material-form-buttons">
          {editingId && (
            <button type="button" className="button secondary" onClick={resetForm}>
              취소
            </button>
          )}
          <button type="submit" className="button">
            {editingId ? '수정 저장' : '자료 등록'}
          </button>
        </div>
      </form>

      <div className="materials-list">
        {materials.length === 0 && (
          <p className="empty-state">아직 등록한 자료가 없습니다.</p>
        )}

        {materials.map((material) => (
          <div className="material-card card" key={material.id}>
            <div className="material-card-top">
              <div>
                <span className="material-type">{material.type}</span>
                <h3>{material.title}</h3>
                <p className="notice">{formatDate(material.created_at)}</p>
              </div>
              <div className="material-card-buttons">
                <button type="button" className="button secondary" onClick={() => handleEdit(material)}>
                  수정
                </button>
                <button type="button" className="button danger" onClick={() => handleDelete(material.id)}>
                  삭제
                </button>
              </div>
            </div>
            <p className="material-content">{material.content}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default MaterialsPage
