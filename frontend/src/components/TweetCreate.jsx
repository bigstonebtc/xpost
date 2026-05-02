import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'

const s = {
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', marginTop: '20px' },
  newBtn: { padding: '8px 16px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  card: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '16px', marginBottom: '12px' },
  cardName: { fontWeight: 'bold', fontSize: '15px', marginBottom: '4px' },
  cardDocs: { fontSize: '12px', color: '#888', marginBottom: '12px' },
  btnRow: { display: 'flex', gap: '8px', flexWrap: 'wrap' },
  btnGenerate: { padding: '7px 14px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '13px' },
  btnEdit: { padding: '7px 14px', background: '#fff', color: '#333', border: '1px solid #ccc', borderRadius: '5px', cursor: 'pointer', fontSize: '13px' },
  btnDelete: { padding: '7px 14px', background: '#fff', color: '#dc3545', border: '1px solid #dc3545', borderRadius: '5px', cursor: 'pointer', fontSize: '13px' },
  successMsg: { fontSize: '13px', color: '#198754', marginTop: '8px' },
  errMsg: { fontSize: '13px', color: '#dc3545', marginTop: '8px' },
  // フォーム
  formOverlay: { background: '#f8f9fa', border: '1px solid #dee2e6', borderRadius: '8px', padding: '20px', marginBottom: '16px' },
  formTitle: { fontWeight: 'bold', fontSize: '15px', marginBottom: '16px' },
  label: { display: 'block', fontSize: '13px', fontWeight: 'bold', marginBottom: '4px', marginTop: '12px' },
  input: { width: '100%', padding: '8px 10px', border: '1px solid #ccc', borderRadius: '5px', fontSize: '14px', boxSizing: 'border-box' },
  textarea: { width: '100%', minHeight: '180px', padding: '10px', border: '1px solid #ccc', borderRadius: '5px', fontSize: '13px', fontFamily: 'monospace', lineHeight: '1.6', resize: 'vertical', boxSizing: 'border-box' },
  checkRow: { display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0', fontSize: '14px', cursor: 'pointer' },
  formBtnRow: { display: 'flex', gap: '8px', marginTop: '16px' },
  btnSave: { padding: '8px 20px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '14px' },
  btnCancel: { padding: '8px 14px', background: '#fff', color: '#666', border: '1px solid #ccc', borderRadius: '5px', cursor: 'pointer', fontSize: '14px' },
  hint: { fontSize: '12px', color: '#888', marginTop: '4px' },
  empty: { textAlign: 'center', color: '#888', padding: '40px 0', fontSize: '14px' },
}

const EMPTY_FORM = { name: '', documents: [], prompt: '' }

function PromptForm({ initial, documents, onSave, onCancel, saving }) {
  const [form, setForm] = useState(initial || EMPTY_FORM)

  const toggleDoc = (fname) => {
    setForm(prev => ({
      ...prev,
      documents: prev.documents.includes(fname)
        ? prev.documents.filter(d => d !== fname)
        : [...prev.documents, fname],
    }))
  }

  return (
    <div style={s.formOverlay}>
      <div style={s.formTitle}>{initial ? 'プロンプトを編集' : '新規プロンプト作成'}</div>

      <label style={s.label}>プロンプト名 <span style={{ color: '#dc3545' }}>*</span></label>
      <input
        style={s.input}
        value={form.name}
        maxLength={50}
        onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
        placeholder="例: 相続税・論点型"
      />

      <label style={s.label}>参照資料（複数選択可）</label>
      {documents.length === 0 ? (
        <p style={s.hint}>/app/documents/ に資料ファイルがありません</p>
      ) : (
        documents.map(fname => (
          <label key={fname} style={s.checkRow}>
            <input
              type="checkbox"
              checked={form.documents.includes(fname)}
              onChange={() => toggleDoc(fname)}
            />
            {fname}
          </label>
        ))
      )}

      <label style={s.label}>プロンプト本文 <span style={{ color: '#dc3545' }}>*</span></label>
      <textarea
        style={s.textarea}
        value={form.prompt}
        onChange={e => setForm(p => ({ ...p, prompt: e.target.value }))}
        spellCheck={false}
      />

      <div style={s.formBtnRow}>
        <button style={s.btnSave} onClick={() => onSave(form)} disabled={saving}>
          {saving ? '保存中...' : '保存'}
        </button>
        <button style={s.btnCancel} onClick={onCancel} disabled={saving}>キャンセル</button>
      </div>
    </div>
  )
}

export default function TweetCreate() {
  const [prompts, setPrompts] = useState([])
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editTarget, setEditTarget] = useState(null) // { filename, name, documents, prompt }
  const [saving, setSaving] = useState(false)
  const [generatingId, setGeneratingId] = useState(null)
  const [msgMap, setMsgMap] = useState({}) // { filename: { type, text } }
  const [formErr, setFormErr] = useState('')

  const load = useCallback(async () => {
    try {
      const [p, d] = await Promise.all([api.promptsList(), api.documentsList()])
      setPrompts(p)
      setDocuments(d)
    } catch (e) {
      // サイレントフェイル: 空配列のまま
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const flashMsg = (filename, type, text) => {
    setMsgMap(prev => ({ ...prev, [filename]: { type, text } }))
    setTimeout(() => setMsgMap(prev => { const n = { ...prev }; delete n[filename]; return n }), 3000)
  }

  const handleGenerate = async (filename) => {
    setGeneratingId(filename)
    try {
      const res = await api.generate(filename)
      flashMsg(filename, 'ok', `${res.generated}件をキューに追加しました`)
    } catch (e) {
      flashMsg(filename, 'err', e.message)
    } finally {
      setGeneratingId(null)
    }
  }

  const handleDelete = async (filename, name) => {
    if (!confirm(`「${name}」を削除しますか？`)) return
    try {
      await api.promptDelete(filename)
      setPrompts(prev => prev.filter(p => p.filename !== filename))
    } catch (e) {
      flashMsg(filename, 'err', e.message)
    }
  }

  const handleEditClick = async (filename) => {
    try {
      const detail = await api.promptGet(filename)
      setEditTarget(detail)
      setShowForm(false)
      setFormErr('')
    } catch (e) {
      flashMsg(filename, 'err', e.message)
    }
  }

  const handleSaveNew = async (form) => {
    if (!form.name.trim()) { setFormErr('プロンプト名は必須です'); return }
    if (!form.prompt.trim()) { setFormErr('プロンプト本文は必須です'); return }
    setSaving(true)
    setFormErr('')
    try {
      await api.promptCreate(form)
      setShowForm(false)
      await load()
    } catch (e) {
      setFormErr(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleSaveEdit = async (form) => {
    if (!form.name.trim()) { setFormErr('プロンプト名は必須です'); return }
    if (!form.prompt.trim()) { setFormErr('プロンプト本文は必須です'); return }
    setSaving(true)
    setFormErr('')
    try {
      await api.promptUpdate(editTarget.filename, form)
      setEditTarget(null)
      await load()
    } catch (e) {
      setFormErr(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p style={{ color: '#888', textAlign: 'center', marginTop: '40px' }}>読み込み中...</p>

  return (
    <div>
      <div style={s.header}>
        <h2 style={{ fontSize: '18px' }}>ツイート作成</h2>
        <button style={s.newBtn} onClick={() => { setShowForm(true); setEditTarget(null); setFormErr('') }}>
          ＋ 新規プロンプト作成
        </button>
      </div>

      {showForm && (
        <PromptForm
          documents={documents}
          onSave={handleSaveNew}
          onCancel={() => { setShowForm(false); setFormErr('') }}
          saving={saving}
        />
      )}
      {formErr && !editTarget && <p style={s.errMsg}>{formErr}</p>}

      {prompts.length === 0 && !showForm && (
        <div style={s.empty}>プロンプトがありません。「＋ 新規プロンプト作成」から作成してください。</div>
      )}

      {prompts.map(p => (
        <div key={p.filename}>
          {editTarget?.filename === p.filename ? (
            <>
              <PromptForm
                initial={editTarget}
                documents={documents}
                onSave={handleSaveEdit}
                onCancel={() => { setEditTarget(null); setFormErr('') }}
                saving={saving}
              />
              {formErr && <p style={s.errMsg}>{formErr}</p>}
            </>
          ) : (
            <div style={s.card}>
              <div style={s.cardName}>📝 {p.name}</div>
              <div style={s.cardDocs}>
                {p.documents.length > 0
                  ? `参照資料: ${p.documents.join(' / ')}`
                  : '参照資料: なし'}
              </div>
              <div style={s.btnRow}>
                <button
                  style={s.btnGenerate}
                  onClick={() => handleGenerate(p.filename)}
                  disabled={generatingId === p.filename}
                >
                  {generatingId === p.filename ? '生成中...' : '＋10件生成してキューへ'}
                </button>
                <button style={s.btnEdit} onClick={() => handleEditClick(p.filename)}>編集</button>
                <button style={s.btnDelete} onClick={() => handleDelete(p.filename, p.name)}>削除</button>
              </div>
              {msgMap[p.filename] && (
                <p style={msgMap[p.filename].type === 'ok' ? s.successMsg : s.errMsg}>
                  {msgMap[p.filename].text}
                </p>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
