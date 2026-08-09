import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

const s = {
  card: { background: '#fff', borderRadius: '8px', padding: '16px', marginBottom: '10px', boxShadow: '0 1px 4px rgba(0,0,0,0.08)' },
  text: { fontSize: '15px', lineHeight: '1.6', marginBottom: '10px', whiteSpace: 'pre-wrap' },
  meta: { fontSize: '12px', color: '#999', marginBottom: '8px' },
  btnRow: { display: 'flex', gap: '8px' },
  btn: (color) => ({ padding: '6px 14px', border: 'none', borderRadius: '20px', cursor: 'pointer', fontSize: '13px', background: color, color: '#fff', fontWeight: 'bold' }),
  textarea: { width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px', fontSize: '15px', lineHeight: '1.6', resize: 'vertical', minHeight: '160px', fontFamily: 'inherit', boxSizing: 'border-box' },
  counter: (over) => ({ fontSize: '12px', textAlign: 'right', marginBottom: '8px', color: over ? '#e53e3e' : '#888' }),
  topBar: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', marginTop: '20px' },
  createLink: { padding: '10px 20px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px', textDecoration: 'none', display: 'inline-block' },
  clearBtn: { padding: '8px 14px', background: '#fff', color: '#e53e3e', border: '1px solid #e53e3e', borderRadius: '6px', cursor: 'pointer', fontSize: '13px' },
  scheduled: { fontSize: '12px', color: '#718096', marginTop: '6px' },
}

function TweetCard({ tweet, onRefresh, onUpdateContent }) {
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState(tweet.content)
  const [loading, setLoading] = useState(false)
  const [imagePreviewUrl, setImagePreviewUrl] = useState(() => {
    if (!tweet.image_path) return null
    const filename = tweet.image_path.split('/').pop()
    return `/xpost/api/images/preview/${filename}`
  })
  const fileInputRef = useRef(null)

  const isScheduled = tweet.status === 'scheduled'
  const charCount = editText.length
  const over = charCount > 280

  const formatScheduled = (iso) => {
    if (!iso) return ''
    const target = new Date(iso)
    const diffMs = target - Date.now()
    if (diffMs <= 0) return '投稿間近'
    const totalMin = Math.floor(diffMs / 60000)
    const days = Math.floor(totalMin / 1440)
    const hours = Math.floor((totalMin % 1440) / 60)
    const mins = totalMin % 60
    const dd = String(days).padStart(2, '0')
    const hh = String(hours).padStart(2, '0')
    const mm = String(mins).padStart(2, '0')
    const y = target.getFullYear()
    const mo = target.getMonth() + 1
    const d = target.getDate()
    const th = String(target.getHours()).padStart(2, '0')
    const tm = String(target.getMinutes()).padStart(2, '0')
    return `${y}-${mo}-${d} ${th}:${tm} (${dd} d ${hh} h ${mm} m) 投稿予定`
  }

  const handlePost = async () => {
    setLoading(true)
    try { await api.post(tweet.id); onRefresh() }
    catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }

  const handleSchedule = async () => {
    setLoading(true)
    try { await api.schedule(tweet.id); onRefresh() }
    catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }

  const handleDiscard = async () => {
    setLoading(true)
    try { await api.discard(tweet.id); onRefresh() }
    catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }

  const handleDone = async () => {
    if (over) return alert('280文字を超えています')
    setLoading(true)
    try {
      await api.edit(tweet.id, editText)
      onUpdateContent(tweet.id, editText)
      setEditing(false)
    }
    catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }

  const handleCancelEdit = () => {
    setEditText(tweet.content)
    setEditing(false)
  }

  const handlePicClick = () => fileInputRef.current.click()

  const handleFileSelect = async (e) => {
    const file = e.target.files[0]
    e.target.value = ''
    if (!file) return
    const ALLOWED = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if (!ALLOWED.includes(file.type)) {
      alert('JPEG / PNG / GIF / WEBP のみ対応しています')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      alert('ファイルサイズは5MB以内にしてください')
      return
    }
    setLoading(true)
    try {
      const result = await api.uploadImage(tweet.id, file)
      setImagePreviewUrl(result.preview_url)
    } catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }

  const handleDeleteImage = async () => {
    setLoading(true)
    try {
      await api.deleteImage(tweet.id)
      setImagePreviewUrl(null)
    } catch (e) { alert(e.message) }
    finally { setLoading(false) }
  }

  return (
    <div style={s.card}>
      <input
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp"
        style={{ display: 'none' }}
        ref={fileInputRef}
        onChange={handleFileSelect}
      />
      {editing ? (
        <>
          <textarea
            style={{ ...s.textarea, borderColor: over ? '#e53e3e' : '#ddd' }}
            value={editText}
            onChange={e => setEditText(e.target.value)}
            autoFocus
          />
          <div style={s.counter(over)}>{charCount}/280</div>
          <div style={s.btnRow}>
            <button style={s.btn('#2b6cb0')} onClick={handleDone} disabled={loading || over}>done</button>
            <button style={s.btn('#718096')} onClick={handleCancelEdit} disabled={loading}>cancel</button>
          </div>
        </>
      ) : (
        <>
          <div style={s.text}>{tweet.content}</div>
          <div style={s.meta}>{tweet.content.length}文字</div>
          {imagePreviewUrl && (
            <img
              src={imagePreviewUrl}
              alt="添付画像"
              style={{ width: '100%', maxHeight: '200px', objectFit: 'cover', borderRadius: '6px', marginBottom: '8px' }}
            />
          )}
          {isScheduled ? (
            <>
              <div style={s.scheduled}>{formatScheduled(tweet.scheduled_at)}</div>
              <div style={{ ...s.btnRow, marginTop: '8px' }}>
                <button style={s.btn('#e53e3e')} onClick={handleDiscard} disabled={loading}>キャンセル</button>
              </div>
            </>
          ) : (
            <div style={s.btnRow}>
              <button style={s.btn('#38a169')} onClick={handleSchedule} disabled={loading}>Schedule</button>
              <button style={s.btn('#2b6cb0')} onClick={handlePost} disabled={loading}>Post now</button>
              {imagePreviewUrl ? (
                <>
                  <button style={s.btn('#805ad5')} onClick={handlePicClick} disabled={loading}>pic差替</button>
                  <button style={s.btn('#e53e3e')} onClick={handleDeleteImage} disabled={loading}>pic削除</button>
                </>
              ) : (
                <button style={s.btn('#805ad5')} onClick={handlePicClick} disabled={loading}>pic</button>
              )}
              <button style={s.btn('#718096')} onClick={() => setEditing(true)} disabled={loading}>edit</button>
              <button style={s.btn('#e53e3e')} onClick={handleDiscard} disabled={loading}>discard</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default function Queue() {
  const [tweets, setTweets] = useState([])
  const [loading, setLoading] = useState(false)

  const load = () => api.queue().then(setTweets).catch(e => alert(e.message))

  useEffect(() => { load() }, [])

  const handleClear = async () => {
    if (!confirm('キューを全件削除しますか？')) return
    try { await api.clearQueue(); await load() }
    catch (e) { alert(e.message) }
  }

  const handleUpdateContent = (id, content) => {
    setTweets(prev => prev.map(t => t.id === id ? { ...t, content } : t))
  }

  return (
    <div>
      <div style={s.topBar}>
        <h2 style={{ fontSize: '18px' }}>キュー（{tweets.length}件）</h2>
        <div style={s.btnRow}>
          {tweets.length > 0 && <button style={s.clearBtn} onClick={handleClear}>全件削除</button>}
          <Link to="/create" style={s.createLink}>ツイート作成画面へ →</Link>
        </div>
      </div>
      {tweets.length === 0 && <p style={{ color: '#999', textAlign: 'center', marginTop: '40px' }}>キューが空です</p>}
      {tweets.map(t => <TweetCard key={t.id} tweet={t} onRefresh={load} onUpdateContent={handleUpdateContent} />)}
    </div>
  )
}
