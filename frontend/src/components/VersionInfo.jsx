import { useState, useEffect } from 'react'
import { api } from '../api'

// 「v2.1.10 (2026.11.9)」形式。日付が取れない環境では番号のみ
export function formatVersion(v) {
  if (!v?.version) return ''
  return v.date ? `v${v.version} (${v.date})` : `v${v.version}`
}

const s = {
  card: { background: '#fff', borderRadius: '8px', padding: '16px', marginBottom: '16px', boxShadow: '0 1px 4px rgba(0,0,0,0.08)' },
  title: { fontSize: '15px', fontWeight: 'bold', marginBottom: '10px' },
  version: { fontSize: '22px', fontWeight: 'bold' },
  date: { fontSize: '13px', color: '#888', marginLeft: '8px' },
  item: { borderTop: '1px solid #eee', padding: '10px 0' },
  meta: { fontSize: '12px', color: '#888', marginBottom: '4px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' },
  tag: { fontSize: '11px', background: '#ebf4ff', color: '#2b6cb0', borderRadius: '4px', padding: '1px 6px', fontWeight: 'bold' },
  subject: { fontSize: '14px', lineHeight: '1.5', wordBreak: 'break-word' },
  body: { fontSize: '13px', color: '#555', lineHeight: '1.6', whiteSpace: 'pre-wrap', wordBreak: 'break-word', marginTop: '6px' },
  toggle: { fontSize: '12px', color: '#2b6cb0', background: 'none', border: 'none', padding: 0, cursor: 'pointer', marginTop: '4px' },
  muted: { fontSize: '13px', color: '#999' },
}

function HistoryItem({ item }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={s.item}>
      <div style={s.meta}>
        <span>{item.date}</span>
        <span>{item.hash}</span>
        {item.tags.map(t => <span key={t} style={s.tag}>{t}</span>)}
      </div>
      <div style={s.subject}>{item.subject}</div>
      {item.body && (
        <>
          <button style={s.toggle} onClick={() => setOpen(o => !o)}>{open ? '▲ 閉じる' : '▼ 詳細'}</button>
          {open && <div style={s.body}>{item.body}</div>}
        </>
      )}
    </div>
  )
}

export default function VersionInfo() {
  const [version, setVersion] = useState(null)
  const [history, setHistory] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.version().then(setVersion).catch(e => setErr(e.message))
    api.versionHistory().then(setHistory).catch(e => setErr(e.message))
  }, [])

  return (
    <div>
      {err && <p style={{ color: '#e53e3e', fontSize: '13px' }}>{err}</p>}
      <div style={s.card}>
        <div style={s.title}>Version</div>
        {version ? (
          <div>
            <span style={s.version}>{version.version ? `v${version.version}` : '不明'}</span>
            {version.date && <span style={s.date}>{version.date}</span>}
          </div>
        ) : <div style={s.muted}>読み込み中...</div>}
      </div>
      <div style={s.card}>
        <div style={s.title}>更新履歴</div>
        {history == null && <div style={s.muted}>読み込み中...</div>}
        {history && !history.available && <div style={s.muted}>この環境では更新履歴を取得できません（git の情報がありません）</div>}
        {history?.items.map(item => <HistoryItem key={item.hash} item={item} />)}
      </div>
    </div>
  )
}
