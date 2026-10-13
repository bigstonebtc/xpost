import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'
import { formatJst } from '../utils/jst'

const s = {
  page: { paddingBottom: '40px' },
  header: { marginTop: '20px', marginBottom: '16px' },
  title: { fontSize: '18px', fontWeight: 'bold' },
  card: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '16px', marginBottom: '16px' },
  label: { fontSize: '13px', color: '#888', marginBottom: '6px' },
  textarea: { width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px', fontSize: '15px', lineHeight: '1.6', resize: 'vertical', minHeight: '100px', fontFamily: 'inherit', boxSizing: 'border-box', marginBottom: '12px' },
  btn: (color) => ({ padding: '8px 18px', border: 'none', borderRadius: '20px', cursor: 'pointer', fontSize: '14px', fontWeight: 'bold', background: color, color: '#fff' }),
  btnSmall: (color) => ({ padding: '6px 14px', border: 'none', borderRadius: '20px', cursor: 'pointer', fontSize: '13px', fontWeight: 'bold', background: color, color: '#fff' }),
  btnDisabled: { opacity: 0.5, cursor: 'not-allowed' },
  btnRow: { display: 'flex', gap: '8px' },
  itemCard: { background: '#fff', borderRadius: '8px', padding: '16px', marginBottom: '10px', boxShadow: '0 1px 4px rgba(0,0,0,0.08)' },
  itemText: { fontSize: '15px', lineHeight: '1.6', marginBottom: '10px', whiteSpace: 'pre-wrap' },
  itemMeta: { fontSize: '12px', color: '#888', marginBottom: '10px' },
  error: { fontSize: '14px', color: '#e53e3e', marginBottom: '16px' },
  msg: (ok) => ({ fontSize: '13px', color: ok ? '#38a169' : '#e53e3e', marginTop: '8px' }),
  empty: { color: '#999', textAlign: 'center', marginTop: '40px' },
}

function FixedTweetCard({ item, onRefresh }) {
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState(item.content)
  const [saving, setSaving] = useState(false)
  const [queueing, setQueueing] = useState(false)
  const [msg, setMsg] = useState(null)

  const handleSave = async () => {
    if (!editText.trim()) return
    setSaving(true)
    try {
      await api.updateFixedTweet(item.id, editText)
      setEditing(false)
      onRefresh()
    } catch (e) {
      alert(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setEditText(item.content)
    setEditing(false)
  }

  const handleDelete = async () => {
    if (!confirm('この固定文面を削除しますか？')) return
    try {
      await api.deleteFixedTweet(item.id)
      onRefresh()
    } catch (e) {
      alert(e.message)
    }
  }

  const handleQueue = async () => {
    setQueueing(true)
    setMsg(null)
    try {
      await api.queueFixedTweet(item.id)
      setMsg({ ok: true, text: 'キューに追加しました' })
      onRefresh()
    } catch (e) {
      setMsg({ ok: false, text: e.message })
    } finally {
      setQueueing(false)
    }
  }

  return (
    <div style={s.itemCard}>
      {editing ? (
        <>
          <textarea style={s.textarea} value={editText} onChange={e => setEditText(e.target.value)} autoFocus />
          <div style={s.btnRow}>
            <button style={s.btnSmall('#2b6cb0')} onClick={handleSave} disabled={saving || !editText.trim()}>done</button>
            <button style={s.btnSmall('#718096')} onClick={handleCancel} disabled={saving}>cancel</button>
          </div>
        </>
      ) : (
        <>
          <div style={s.itemText}>{item.content}</div>
          <div style={s.itemMeta}>
            最終投入日時：{item.last_used_at ? formatJst(item.last_used_at) : '未投入'} ／ 投入回数：{item.use_count}
          </div>
          <div style={s.btnRow}>
            <button style={s.btnSmall('#38a169')} onClick={handleQueue} disabled={queueing}>{queueing ? '追加中...' : 'キューへ'}</button>
            <button style={s.btnSmall('#718096')} onClick={() => setEditing(true)}>編集</button>
            <button style={s.btnSmall('#e53e3e')} onClick={handleDelete}>削除</button>
          </div>
          {msg && <div style={s.msg(msg.ok)}>{msg.text}</div>}
        </>
      )}
    </div>
  )
}

export default function FixedTweets() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [newContent, setNewContent] = useState('')
  const [registering, setRegistering] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await api.listFixedTweets()
      setItems(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleRegister = async () => {
    if (!newContent.trim()) return
    setRegistering(true)
    setError(null)
    try {
      await api.createFixedTweet(newContent)
      setNewContent('')
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setRegistering(false)
    }
  }

  if (loading) return <p style={s.empty}>読み込み中...</p>

  return (
    <div style={s.page}>
      <div style={s.header}>
        <h2 style={s.title}>正拳突き</h2>
      </div>

      <div style={s.card}>
        <div style={s.label}>本文</div>
        <textarea
          style={s.textarea}
          placeholder="固定で投入したいツイートを入力..."
          value={newContent}
          onChange={e => setNewContent(e.target.value)}
        />
        <button
          style={{ ...s.btn('#38a169'), ...((!newContent.trim() || registering) ? s.btnDisabled : {}) }}
          onClick={handleRegister}
          disabled={!newContent.trim() || registering}
        >
          {registering ? '登録中...' : '登録'}
        </button>
      </div>

      {error && <div style={s.error}>{error}</div>}

      {items.length === 0 ? (
        <p style={s.empty}>登録された固定文面はまだありません。</p>
      ) : (
        items.map(item => <FixedTweetCard key={item.id} item={item} onRefresh={load} />)
      )}
    </div>
  )
}
