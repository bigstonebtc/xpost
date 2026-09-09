import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'

const STORAGE_KEY = 'revision_last_prompt_id'

const s = {
  page: { paddingBottom: '40px' },
  header: { marginTop: '20px', marginBottom: '16px' },
  title: { fontSize: '18px', fontWeight: 'bold' },
  card: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '16px', marginBottom: '16px' },
  label: { fontSize: '13px', color: '#888', marginBottom: '6px' },
  textarea: { width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px', fontSize: '15px', lineHeight: '1.6', resize: 'vertical', minHeight: '140px', fontFamily: 'inherit', boxSizing: 'border-box', marginBottom: '12px' },
  select: { width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '6px', fontSize: '14px', marginBottom: '12px', boxSizing: 'border-box' },
  btn: (color) => ({ padding: '8px 18px', border: 'none', borderRadius: '20px', cursor: 'pointer', fontSize: '14px', fontWeight: 'bold', background: color, color: '#fff' }),
  btnDisabled: { opacity: 0.5, cursor: 'not-allowed' },
  resultTitle: { fontSize: '14px', fontWeight: 'bold', marginBottom: '8px' },
  error: { fontSize: '14px', color: '#e53e3e', marginBottom: '16px' },
  empty: { color: '#999', textAlign: 'center', marginTop: '40px' },
}

export default function Revision() {
  const [prompts, setPrompts] = useState([])
  const [loading, setLoading] = useState(true)
  const [text, setText] = useState('')
  const [promptId, setPromptId] = useState('')
  const [rewriting, setRewriting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [adding, setAdding] = useState(false)

  const load = useCallback(async () => {
    try {
      const ps = await api.listPrompts(true)
      setPrompts(ps)
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved && ps.some(p => p.filename === saved)) {
        setPromptId(saved)
      } else if (ps.length > 0) {
        setPromptId(ps[0].filename)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handlePromptChange = (e) => {
    const value = e.target.value
    setPromptId(value)
    localStorage.setItem(STORAGE_KEY, value)
  }

  const handleRewrite = async () => {
    if (!text.trim() || !promptId) return
    setRewriting(true)
    setError(null)
    setResult(null)
    try {
      const res = await api.rewrite(text, promptId)
      setResult(res.rewritten)
      localStorage.setItem(STORAGE_KEY, promptId)
    } catch (e) {
      setError(e.message)
    } finally {
      setRewriting(false)
    }
  }

  const handleAddToQueue = async () => {
    if (result == null) return
    setAdding(true)
    try {
      await api.addToQueue(result)
      setText('')
      setResult(null)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setAdding(false)
    }
  }

  if (loading) return <p style={s.empty}>読み込み中...</p>

  return (
    <div style={s.page}>
      <div style={s.header}>
        <h2 style={s.title}>推敲</h2>
      </div>

      {prompts.length === 0 ? (
        <p style={s.empty}>プロンプトがありません。「プロンプト管理」から作成してください。</p>
      ) : (
        <div style={s.card}>
          <div style={s.label}>推敲したいツイート</div>
          <textarea
            style={s.textarea}
            placeholder="推敲したいツイートを入力..."
            value={text}
            onChange={e => setText(e.target.value)}
          />

          <div style={s.label}>プロンプト</div>
          <select style={s.select} value={promptId} onChange={handlePromptChange}>
            {prompts.map(p => (
              <option key={p.filename} value={p.filename}>{p.name}</option>
            ))}
          </select>

          <button
            style={{ ...s.btn('#38a169'), ...((!text.trim() || rewriting) ? s.btnDisabled : {}) }}
            onClick={handleRewrite}
            disabled={!text.trim() || rewriting}
          >
            {rewriting ? 'リライト中...' : 'リライト'}
          </button>
        </div>
      )}

      {error && <div style={s.error}>{error}</div>}

      {result != null && (
        <div style={s.card}>
          <div style={s.resultTitle}>リライト結果（編集可能）</div>
          <textarea
            style={s.textarea}
            value={result}
            onChange={e => setResult(e.target.value)}
          />
          <button
            style={{ ...s.btn('#2b6cb0'), ...(adding ? s.btnDisabled : {}) }}
            onClick={handleAddToQueue}
            disabled={adding}
          >
            {adding ? '追加中...' : 'キューに追加'}
          </button>
        </div>
      )}
    </div>
  )
}
