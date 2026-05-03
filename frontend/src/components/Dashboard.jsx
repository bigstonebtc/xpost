import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

const styles = {
  card: { background: '#fff', borderRadius: '8px', padding: '20px', marginBottom: '12px', boxShadow: '0 1px 4px rgba(0,0,0,0.08)' },
  clickableCard: { background: '#fff', borderRadius: '8px', padding: '20px', marginBottom: '12px', boxShadow: '0 1px 4px rgba(0,0,0,0.08)', textDecoration: 'none', display: 'block', color: 'inherit' },
  label: { fontSize: '13px', color: '#888', marginBottom: '6px' },
  value: { fontSize: '32px', fontWeight: 'bold', color: '#1a1a2e' },
  valueSmall: { fontSize: '18px', fontWeight: 'bold', color: '#1a1a2e' },
  subRows: { marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column', gap: '8px' },
  subRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', textDecoration: 'none', color: 'inherit', padding: '4px 0' },
  subLabel: { fontSize: '13px', color: '#666' },
  subValue: { fontSize: '15px', fontWeight: 'bold', color: '#1a1a2e' },
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
        <Link to="/history?filter=today" style={styles.subRow}>
          <span style={styles.label}>今日の投稿件数</span>
          <span style={styles.value}>{stats.today_posted}</span>
        </Link>
        <div style={styles.subRows}>
          <Link to="/history?filter=yesterday" style={styles.subRow}>
            <span style={styles.subLabel}>昨日</span>
            <span style={styles.subValue}>{stats.yesterday_posted ?? '—'}</span>
          </Link>
          <Link to="/history?filter=month" style={styles.subRow}>
            <span style={styles.subLabel}>今月</span>
            <span style={styles.subValue}>{stats.month_posted ?? '—'}</span>
          </Link>
          <Link to="/history?filter=all" style={styles.subRow}>
            <span style={styles.subLabel}>累計</span>
            <span style={styles.subValue}>{stats.total_posted ?? '—'}</span>
          </Link>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.label}>次の投稿予定</div>
        <div style={styles.valueSmall}>{formatTime(stats.next_scheduled_at)}</div>
      </div>
    </div>
  )
}
