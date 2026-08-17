import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

// ツイート生成用ではないシステムプロンプトはここでは表示しない（プロンプト管理画面では表示・編集可能）
const NON_GENERATION_PROMPTS = ['news_search.prompt']

const s = {
  page: { paddingBottom: '40px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', marginTop: '20px' },
  title: { fontSize: '18px', fontWeight: 'bold' },
  manageLink: { padding: '8px 16px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px', textDecoration: 'none', display: 'inline-block' },
  card: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '16px', marginBottom: '12px' },
  usage: { fontSize: '12px', color: '#888', marginBottom: '16px' },
  cardHeader: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' },
  cardTitle: { fontSize: '16px', fontWeight: 'bold', flex: 1 },
  docList: { fontSize: '12px', color: '#888', marginBottom: '12px' },
  genBtn: { padding: '7px 14px', background: '#38a169', color: '#fff', border: 'none', borderRadius: '20px', cursor: 'pointer', fontSize: '13px', fontWeight: 'bold' },
  genResult: { fontSize: '13px', color: '#38a169', marginTop: '8px' },
  genError: { fontSize: '13px', color: '#e53e3e', marginTop: '8px' },
  empty: { color: '#999', textAlign: 'center', marginTop: '40px' },
}

function PromptCard({ prompt }) {
  const [generating, setGenerating] = useState(false)
  const [genMsg, setGenMsg] = useState(null)

  const handleGenerate = async () => {
    setGenerating(true)
    setGenMsg(null)
    try {
      const res = await api.generateWithPrompt(prompt.filename)
      setGenMsg({ ok: true, text: `${res.generated}件をキューに追加しました` })
    } catch (e) {
      setGenMsg({ ok: false, text: e.message })
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div style={s.card}>
      <div style={s.cardHeader}>
        <span style={{ fontSize: '18px' }}>📝</span>
        <span style={s.cardTitle}>{prompt.name}</span>
      </div>
      <div style={s.docList}>
        {prompt.documents.length > 0
          ? `参照資料: ${prompt.documents.join(' / ')}`
          : '参照資料: なし'}
      </div>
      <button style={s.genBtn} onClick={handleGenerate} disabled={generating}>
        {generating ? '生成中...' : '＋10件生成してキューへ'}
      </button>
      {genMsg && <div style={genMsg.ok ? s.genResult : s.genError}>{genMsg.text}</div>}
    </div>
  )
}

export default function TweetCreate() {
  const [prompts, setPrompts] = useState([])
  const [loading, setLoading] = useState(true)
  const [usage, setUsage] = useState(null)

  const load = useCallback(async () => {
    try {
      const ps = await api.listPrompts()
      setPrompts(ps.filter(p => !NON_GENERATION_PROMPTS.includes(p.filename)))
    } catch (e) {
      alert(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    const loadUsage = () => api.rateLimitUsage().then(setUsage).catch(() => {})
    loadUsage()
    const interval = setInterval(loadUsage, 60000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <p style={{ color: '#888', textAlign: 'center', marginTop: '40px' }}>読み込み中...</p>

  return (
    <div style={s.page}>
      <div style={s.header}>
        <h2 style={s.title}>ツイート作成</h2>
        <Link to="/prompts" style={s.manageLink}>プロンプト管理へ →</Link>
      </div>

      {usage && (
        <div style={s.usage}>
          API使用状況（1時間）— Anthropic: {usage.anthropic.used}/{usage.anthropic.limit} ／ X API: {usage.x_api.used}/{usage.x_api.limit}
        </div>
      )}

      {prompts.length === 0 && (
        <p style={s.empty}>プロンプトがありません。「プロンプト管理」から作成してください。</p>
      )}

      {prompts.map(p => (
        <PromptCard key={p.filename} prompt={p} />
      ))}
    </div>
  )
}
