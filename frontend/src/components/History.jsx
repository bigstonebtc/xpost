import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api'

const s = {
  card: { background: '#fff', borderRadius: '8px', padding: '16px', marginBottom: '10px', boxShadow: '0 1px 4px rgba(0,0,0,0.08)' },
  text: { fontSize: '15px', lineHeight: '1.6', marginBottom: '8px', whiteSpace: 'pre-wrap' },
  meta: { fontSize: '12px', color: '#999' },
  topBar: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '20px 0 16px' },
  select: { padding: '6px 10px', border: '1px solid #ccc', borderRadius: '6px', fontSize: '14px' },
}

const FILTERS = [
  { value: 'today', label: '今日' },
  { value: 'yesterday', label: '昨日' },
  { value: 'month', label: '今月' },
  { value: 'all', label: 'すべて' },
]

const formatDate = (iso) =>
  new Date(iso).toLocaleString('ja-JP', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })

export default function History() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [tweets, setTweets] = useState([])
  const filter = searchParams.get('filter') || 'today'

  useEffect(() => {
    api.history(filter).then(setTweets).catch(e => alert(e.message))
  }, [filter])

  const handleFilterChange = (e) => {
    const val = e.target.value
    setSearchParams(val === 'today' ? {} : { filter: val })
  }

  return (
    <div>
      <div style={s.topBar}>
        <h2 style={{ fontSize: '18px' }}>投稿履歴（{tweets.length}件）</h2>
        <select style={s.select} value={filter} onChange={handleFilterChange}>
          {FILTERS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
        </select>
      </div>
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
