import { useState, useEffect } from 'react'
import { api } from '../api'

const styles = {
  card: { background: '#fff', borderRadius: '8px', padding: '20px', marginBottom: '12px', boxShadow: '0 1px 4px rgba(0,0,0,0.08)' },
  label: { fontSize: '13px', color: '#888', marginBottom: '6px' },
  value: { fontSize: '32px', fontWeight: 'bold', color: '#1a1a2e' },
  valueSmall: { fontSize: '18px', fontWeight: 'bold', color: '#1a1a2e' },
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.stats().then(setStats).catch(e => setErr(e.message))
  }, [])

  const formatTime = (iso) => {
    if (!iso) return 'なし'
    return new Date(iso).toLocaleString('ja-JP', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  if (err) return <p style={{ color: 'red', marginTop: '20px' }}>{err}</p>
  if (!stats) return <p style={{ marginTop: '20px' }}>読み込み中...</p>

  return (
    <div style={{ marginTop: '20px' }}>
      <h2 style={{ marginBottom: '16px', fontSize: '18px' }}>ダッシュボード</h2>
      <div style={styles.card}>
        <div style={styles.label}>キュー件数</div>
        <div style={styles.value}>{stats.queue_count}</div>
      </div>
      <div style={styles.card}>
        <div style={styles.label}>投稿予定件数</div>
        <div style={styles.value}>{stats.scheduled_count}</div>
      </div>
      <div style={styles.card}>
        <div style={styles.label}>今日の投稿件数</div>
        <div style={styles.value}>{stats.today_posted}</div>
      </div>
      <div style={styles.card}>
        <div style={styles.label}>次の投稿予定</div>
        <div style={styles.valueSmall}>{formatTime(stats.next_scheduled_at)}</div>
      </div>
    </div>
  )
}
