import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

const s = {
  page: { paddingBottom: '40px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', marginTop: '20px' },
  title: { fontSize: '18px', fontWeight: 'bold' },
  newBtn: { padding: '8px 16px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  card: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '16px', marginBottom: '12px' },
  cardHeader: { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' },
  cardTitle: { fontSize: '16px', fontWeight: 'bold', flex: 1 },
  docList: { fontSize: '12px', color: '#888', marginBottom: '12px' },
  btnRow: { display: 'flex', gap: '8px', flexWrap: 'wrap' },
  genBtn: { padding: '7px 14px', background: '#38a169', color: '#fff', border: 'none', borderRadius: '20px', cursor: 'pointer', fontSize: '13px', fontWeight: 'bold' },
  editBtn: { padding: '7px 14px', background: '#2b6cb0', color: '#fff', border: 'none', borderRadius: '20px', cursor: 'pointer', fontSize: '13px' },
  delBtn: { padding: '7px 14px', background: '#e53e3e', color: '#fff', border: 'none', borderRadius: '20px', cursor: 'pointer', fontSize: '13px' },
  genResult: { fontSize: '13px', color: '#38a169', marginTop: '8px' },
  genError: { fontSize: '13px', color: '#e53e3e', marginTop: '8px' },
  // modal
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 },
  modal: { background: '#fff', borderRadius: '8px', padding: '24px', width: '90%', maxWidth: '540px', maxHeight: '90vh', overflowY: 'auto' },
  modalTitle: { fontSize: '16px', fontWeight: 'bold', marginBottom: '16px' },
  label: { fontSize: '13px', color: '#555', marginBottom: '4px', display: 'block' },
  input: { width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '6px', fontSize: '14px', boxSizing: 'border-box', marginBottom: '12px' },
  textarea: { width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '6px', fontSize: '13px', fontFamily: 'monospace', lineHeight: '1.6', resize: 'vertical', minHeight: '180px', boxSizing: 'border-box', marginBottom: '12px' },
  checkboxList: { marginBottom: '12px', maxHeight: '120px', overflowY: 'auto', border: '1px solid #eee', borderRadius: '6px', padding: '8px' },
  checkboxRow: { display: 'flex', alignItems: 'center', gap: '8px', padding: '3px 0', fontSize: '13px' },
  modalBtnRow: { display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '4px' },
  saveBtn: { padding: '8px 20px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  cancelBtn: { padding: '8px 16px', background: '#fff', color: '#718096', border: '1px solid #ccc', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  errMsg: { color: '#e53e3e', fontSize: '13px', marginBottom: '8px' },
  empty: { color: '#999', textAlign: 'center', marginTop: '40px' },
}

function PromptModal({ initial, documents, onSave, onClose }) {
  const [name, setName] = useState(initial?.name || '')
  const [selectedDocs, setSelectedDocs] = useState(initial?.documents || [])
  const [prompt, setPrompt] = useState(initial?.prompt || '')
  const [err, setErr] = useState('')
  const [saving, setSaving] = useState(false)

  const toggleDoc = (doc) => {
    setSelectedDocs(prev =>
      prev.includes(doc) ? prev.filter(d => d !== doc) : [...prev, doc]
    )
  }

  const handleSave = async () => {
    if (!name.trim()) { setErr('プロンプト名は必須です'); return }
    if (name.trim().length > 50) { setErr('プロンプト名は50文字以内です'); return }
    if (!prompt.trim()) { setErr('プロンプト本文は必須です'); return }
    setSaving(true)
    try {
      await onSave({ name: name.trim(), documents: selectedDocs, prompt: prompt.trim() })
    } catch (e) {
      setErr(e.message)
      setSaving(false)
    }
  }

  return (
    <div style={s.overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={s.modal}>
        <div style={s.modalTitle}>{initial ? 'プロンプトを編集' : '新規プロンプト作成'}</div>
        {err && <p style={s.errMsg}>{err}</p>}

        <label style={s.label}>プロンプト名 <span style={{ color: '#e53e3e' }}>*</span></label>
        <input style={s.input} value={name} onChange={e => setName(e.target.value)} placeholder="例：相続税・論点型" maxLength={50} />

        <label style={s.label}>参照資料（複数選択可）</label>
        <div style={s.checkboxList}>
          {documents.length === 0
            ? <span style={{ fontSize: '12px', color: '#aaa' }}>/app/documents/ に資料ファイルがありません</span>
            : documents.map(doc => (
              <label key={doc} style={s.checkboxRow}>
                <input type="checkbox" checked={selectedDocs.includes(doc)} onChange={() => toggleDoc(doc)} />
                {doc}
              </label>
            ))
          }
        </div>

        <label style={s.label}>プロンプト本文 <span style={{ color: '#e53e3e' }}>*</span></label>
        <textarea style={s.textarea} value={prompt} onChange={e => setPrompt(e.target.value)} spellCheck={false} />

        <div style={s.modalBtnRow}>
          <button style={s.cancelBtn} onClick={onClose} disabled={saving}>キャンセル</button>
          <button style={s.saveBtn} onClick={handleSave} disabled={saving}>{saving ? '保存中...' : '保存'}</button>
        </div>
      </div>
    </div>
  )
}

function PromptCard({ prompt, documents, onRefresh }) {
  const [generating, setGenerating] = useState(false)
  const [genMsg, setGenMsg] = useState(null)
  const [showEdit, setShowEdit] = useState(false)

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

  const handleDelete = async () => {
    if (!confirm(`「${prompt.name}」を削除しますか？`)) return
    try {
      await api.deletePrompt(prompt.filename)
      onRefresh()
    } catch (e) {
      alert(e.message)
    }
  }

  const handleEdit = async ({ name, documents: docs, prompt: body }) => {
    await api.updatePrompt(prompt.filename, { name, documents: docs, prompt: body })
    setShowEdit(false)
    onRefresh()
  }

  return (
    <>
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
        <div style={s.btnRow}>
          <button style={s.genBtn} onClick={handleGenerate} disabled={generating}>
            {generating ? '生成中...' : '＋10件生成してキューへ'}
          </button>
          <button style={s.editBtn} onClick={() => setShowEdit(true)}>編集</button>
          <button style={s.delBtn} onClick={handleDelete}>削除</button>
        </div>
        {genMsg && <div style={genMsg.ok ? s.genResult : s.genError}>{genMsg.text}</div>}
      </div>
      {showEdit && (
        <PromptModal
          initial={prompt}
          documents={documents}
          onSave={handleEdit}
          onClose={() => setShowEdit(false)}
        />
      )}
    </>
  )
}

export default function TweetCreate() {
  const [prompts, setPrompts] = useState([])
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [showNew, setShowNew] = useState(false)
  const navigate = useNavigate()

  const load = useCallback(async () => {
    try {
      const [ps, ds] = await Promise.all([api.listPrompts(), api.listDocuments()])
      setPrompts(ps)
      setDocuments(ds.documents || [])
    } catch (e) {
      alert(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleCreate = async ({ name, documents: docs, prompt }) => {
    await api.createPrompt({ name, documents: docs, prompt })
    setShowNew(false)
    load()
  }

  if (loading) return <p style={{ color: '#888', textAlign: 'center', marginTop: '40px' }}>読み込み中...</p>

  return (
    <div style={s.page}>
      <div style={s.header}>
        <h2 style={s.title}>ツイート作成</h2>
        <button style={s.newBtn} onClick={() => setShowNew(true)}>＋ 新規プロンプト作成</button>
      </div>

      {prompts.length === 0 && (
        <p style={s.empty}>プロンプトがありません。「＋ 新規プロンプト作成」から作成してください。</p>
      )}

      {prompts.map(p => (
        <PromptCard key={p.filename} prompt={p} documents={documents} onRefresh={load} />
      ))}

      {showNew && (
        <PromptModal
          initial={null}
          documents={documents}
          onSave={handleCreate}
          onClose={() => setShowNew(false)}
        />
      )}
    </div>
  )
}
