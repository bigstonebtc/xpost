import { useState, useEffect } from 'react'
import { api } from '../api'

const s = {
  card: { background: '#fff', borderRadius: '8px', padding: '16px', marginBottom: '10px', boxShadow: '0 1px 4px rgba(0,0,0,0.08)' },
  text: { fontSize: '15px', lineHeight: '1.6', marginBottom: '8px', whiteSpace: 'pre-wrap' },
  meta: { fontSize: '12px', color: '#999' },
}

const formatDate = (iso) =>
  new Date(iso).toLocaleString('ja-JP', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })

export default function History() {
  const [tweets, setTweets] = useState([])

  useEffect(() => {
    api.history().then(setTweets).catch(e => alert(e.message))
  }, [])

  return (
    <div>
      <h2 style={{ fontSize: '18px', margin: '20px 0 16px' }}>投稿履歴（{tweets.length}件）</h2>
      {tweets.length === 0 && <p style={{ color: '#999', textAlign: 'center', marginTop: '40px' }}>投稿履歴がありません</p>}
      {tweets.map(t => (
        <div key={t.id} style={s.card}>
          <div style={s.text}>{t.content}</div>
          <div style={s.meta}>{formatDate(t.posted_at)}</div>
        </div>
      ))}
    </div>
  )
}
