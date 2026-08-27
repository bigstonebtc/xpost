import { useState, useEffect, useCallback } from 'react'
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
  editBtn: { padding: '7px 14px', background: '#2b6cb0', color: '#fff', border: 'none', borderRadius: '20px', cursor: 'pointer', fontSize: '13px' },
  delBtn: { padding: '7px 14px', background: '#e53e3e', color: '#fff', border: 'none', borderRadius: '20px', cursor: 'pointer', fontSize: '13px' },
  // modal
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'stretch', justifyContent: 'center', zIndex: 1000 },
  modal: { background: '#fff', padding: '24px', width: '100%', maxWidth: '900px', display: 'flex', flexDirection: 'column', overflowY: 'auto' },
  modalTitle: { fontSize: '16px', fontWeight: 'bold', marginBottom: '16px' },
  label: { fontSize: '13px', color: '#555', marginBottom: '4px', display: 'block' },
  input: { width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '6px', fontSize: '14px', boxSizing: 'border-box', marginBottom: '12px' },
  textarea: { width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '6px', fontSize: '13px', fontFamily: 'monospace', lineHeight: '1.6', resize: 'vertical', minHeight: '400px', flex: 1, boxSizing: 'border-box', marginBottom: '12px' },
  checkboxList: { marginBottom: '12px', maxHeight: '160px', overflowY: 'auto', border: '1px solid #eee', borderRadius: '6px', padding: '8px', flexShrink: 0 },
  checkboxRow: { display: 'flex', alignItems: 'center', gap: '8px', padding: '3px 0', fontSize: '13px' },
  modalBtnRow: { display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '4px' },
  saveBtn: { padding: '8px 20px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  cancelBtn: { padding: '8px 16px', background: '#fff', color: '#718096', border: '1px solid #ccc', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  errMsg: { color: '#e53e3e', fontSize: '13px', marginBottom: '8px' },
  warnMsg: { color: '#dd8800', fontSize: '13px', marginBottom: '8px' },
  empty: { color: '#999', textAlign: 'center', marginTop: '40px' },
  hint: { color: '#aaa', marginLeft: '6px', fontWeight: 'normal' },
}

function PromptModal({ initial, documents, onSave, onClose }) {
  const [name, setName] = useState(initial?.name || '')
  const [selectedDocs, setSelectedDocs] = useState(initial?.documents || [])
  const [body, setBody] = useState(initial?.body || '')
  const [err, setErr] = useState('')
  const [saving, setSaving] = useState(false)

  const toggleDoc = (doc) => {
    setSelectedDocs(prev =>
      prev.includes(doc) ? prev.filter(d => d !== doc) : [...prev, doc]
    )
  }

  // ヒント表示のみの簡易チェック（保存データには影響しない）
  const topicWarning = body.includes('{topic}') && !/^\s*topics\s*=/m.test(body)
  const typeWarning = body.includes('{type}') && !/^\s*types\s*=/m.test(body)

  const handleSave = async () => {
    if (!name.trim()) { setErr('プロンプト名は必須です'); return }
    if (name.trim().length > 50) { setErr('プロンプト名は50文字以内です'); return }
    if (!body.trim()) { setErr('プロンプト本文は必須です'); return }
    setSaving(true)
    try {
      await onSave({ name: name.trim(), documents: selectedDocs, body })
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

        <label style={s.label}>プロンプト本文 <span style={{ color: '#e53e3e' }}>*</span><span style={s.hint}>入力した内容がそのまま保存されます（#コメント可）。論点リスト・型リストを使う場合は先頭に「topics =」「types =」（1行1項目、インデント）と「[prompt]」を書いてから本文を続けてください</span></label>
        {topicWarning && <p style={s.warnMsg}>⚠ 本文に {'{topic}'} がありますが、論点リストが空です</p>}
        {typeWarning && <p style={s.warnMsg}>⚠ 本文に {'{type}'} がありますが、型リストが空です</p>}
        <textarea style={s.textarea} value={body} onChange={e => setBody(e.target.value)} spellCheck={false} />

        <div style={s.modalBtnRow}>
          <button style={s.cancelBtn} onClick={onClose} disabled={saving}>キャンセル</button>
          <button style={s.saveBtn} onClick={handleSave} disabled={saving}>{saving ? '保存中...' : '保存'}</button>
        </div>
      </div>
    </div>
  )
}

function PromptRow({ prompt, documents, onRefresh }) {
  const [showEdit, setShowEdit] = useState(false)

  const handleDelete = async () => {
    if (!confirm(`「${prompt.name}」を削除しますか？`)) return
    try {
      await api.deletePrompt(prompt.filename)
      onRefresh()
    } catch (e) {
      alert(e.message)
    }
  }

  const handleEdit = async ({ name, documents: docs, body }) => {
    await api.updatePrompt(prompt.filename, { name, documents: docs, body })
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
          <button style={s.editBtn} onClick={() => setShowEdit(true)}>編集</button>
          <button style={s.delBtn} onClick={handleDelete}>削除</button>
        </div>
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

export default function PromptManage() {
  const [prompts, setPrompts] = useState([])
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [showNew, setShowNew] = useState(false)

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

  const handleCreate = async ({ name, documents: docs, body }) => {
    await api.createPrompt({ name, documents: docs, body })
    setShowNew(false)
    load()
  }

  if (loading) return <p style={{ color: '#888', textAlign: 'center', marginTop: '40px' }}>読み込み中...</p>

  return (
    <div style={s.page}>
      <div style={s.header}>
        <h2 style={s.title}>プロンプト管理</h2>
        <button style={s.newBtn} onClick={() => setShowNew(true)}>＋ 新規プロンプト作成</button>
      </div>

      {prompts.length === 0 && (
        <p style={s.empty}>プロンプトがありません。「＋ 新規プロンプト作成」から作成してください。</p>
      )}

      {prompts.map(p => (
        <PromptRow key={p.filename} prompt={p} documents={documents} onRefresh={load} />
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
