import { useState, useEffect } from 'react'
import { api } from '../api'

const KEYS = [
  { key: 'X_CONSUMER_KEY',        label: 'X Consumer Key' },
  { key: 'X_CONSUMER_SECRET',     label: 'X Consumer Secret' },
  { key: 'X_ACCESS_TOKEN',        label: 'X Access Token' },
  { key: 'X_ACCESS_TOKEN_SECRET', label: 'X Access Token Secret' },
  { key: 'ANTHROPIC_API_KEY',     label: 'Anthropic API Key' },
]

const s = {
  section: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '20px', marginBottom: '20px' },
  title: { fontSize: '16px', fontWeight: 'bold', marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid #eee' },
  row: { display: 'flex', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid #f0f0f0', gap: '12px' },
  label: { fontSize: '13px', width: '180px', flexShrink: 0, color: '#555' },
  input: { flex: 1, padding: '7px 10px', border: '1px solid #aaa', borderRadius: '4px', fontSize: '13px', fontFamily: 'monospace', boxSizing: 'border-box' },
  masked: { flex: 1, padding: '7px 10px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '13px', fontFamily: 'monospace', background: '#f9f9f9', color: '#aaa', cursor: 'pointer', userSelect: 'none' },
  saveBtn: { marginTop: '16px', padding: '8px 20px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  restartBtn: { padding: '9px 22px', background: '#c53030', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  notice: { fontSize: '12px', color: '#c05621', marginTop: '10px' },
  okMsg: { color: '#198754', fontSize: '13px', marginTop: '8px' },
  errMsg: { color: '#dc3545', fontSize: '13px', marginTop: '8px' },
}

export default function ApiKeySettings() {
  const [masked, setMasked] = useState({})
  const [values, setValues] = useState({})
  const [rawLoaded, setRawLoaded] = useState(false)
  const [editing, setEditing] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [restarting, setRestarting] = useState(false)
  const [msg, setMsg] = useState({ type: '', text: '' })

  useEffect(() => {
    api.getApiKeys().then(data => {
      setMasked(data)
      setLoading(false)
    }).catch(e => {
      setMsg({ type: 'err', text: e.message })
      setLoading(false)
    })
  }, [])

  const flash = (type, text) => {
    setMsg({ type, text })
    setTimeout(() => setMsg({ type: '', text: '' }), 6000)
  }

  const handleClick = async (key) => {
    if (!rawLoaded) {
      try {
        const raw = await api.getApiKeysRaw()
        setValues(raw)
        setRawLoaded(true)
      } catch (e) {
        flash('err', e.message)
        return
      }
    }
    setEditing(prev => ({ ...prev, [key]: true }))
  }

  const handleBlur = (key) => {
    setEditing(prev => ({ ...prev, [key]: false }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.updateApiKeys(values)
      flash('ok', '保存しました ✓ 反映するには再起動してください')
    } catch {
      flash('err', '保存に失敗しました。ファイルの書き込み権限を確認してください')
    } finally {
      setSaving(false)
    }
  }

  const handleRestart = async () => {
    if (!confirm('アプリを再起動します。再起動中は数十秒アプリが利用できなくなります。よろしいですか？')) return
    setRestarting(true)
    try { await api.restartApp() } catch {}
    setTimeout(() => window.location.reload(), 30000)
  }

  if (loading) return <p style={{ color: '#888', textAlign: 'center', marginTop: '40px' }}>読み込み中...</p>

  return (
    <div>
      {msg.text && <p style={msg.type === 'ok' ? s.okMsg : s.errMsg}>{msg.text}</p>}

      <div style={s.section}>
        <div style={s.title}>APIキー設定</div>
        {KEYS.map(({ key, label }) => (
          <div key={key} style={s.row}>
            <span style={s.label}>{label}</span>
            {editing[key] ? (
              <input
                style={s.input}
                type="text"
                value={values[key] || ''}
                onChange={e => setValues(prev => ({ ...prev, [key]: e.target.value }))}
                onBlur={() => handleBlur(key)}
                autoFocus
              />
            ) : (
              <div style={s.masked} onClick={() => handleClick(key)}>
                {masked[key] || '（未設定）'}
              </div>
            )}
          </div>
        ))}
        <button style={s.saveBtn} onClick={handleSave} disabled={saving || !rawLoaded}>
          {saving ? '保存中...' : '保存'}
        </button>
        <p style={s.notice}>⚠️ 保存後、設定を反映するには再起動が必要です</p>
      </div>

      <div style={s.section}>
        <div style={s.title}>アプリ再起動</div>
        <button style={s.restartBtn} onClick={handleRestart} disabled={restarting}>
          {restarting ? '再起動中です。しばらくお待ちください...' : 'アプリを再起動する'}
        </button>
      </div>
    </div>
  )
}
