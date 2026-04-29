import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'

const styles = {
  topBar: { display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' },
  fetchBtn: { padding: '8px 16px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  nextFetch: { fontSize: '13px', color: '#666' },
  card: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '16px', marginBottom: '16px' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' },
  cardTitle: { fontWeight: 'bold', fontSize: '15px', flex: 1, marginRight: '8px', lineHeight: '1.4' },
  cardMeta: { fontSize: '12px', color: '#888', whiteSpace: 'nowrap' },
  tweetBox: { background: '#f8f9fa', border: '1px solid #dee2e6', borderRadius: '6px', padding: '12px', marginTop: '10px', fontSize: '14px', lineHeight: '1.6', whiteSpace: 'pre-wrap', wordBreak: 'break-all' },
  charCount: { fontSize: '12px', textAlign: 'right', marginTop: '4px' },
  charCountOk: { color: '#888' },
  charCountOver: { color: '#dc3545', fontWeight: 'bold' },
  actions: { display: 'flex', gap: '8px', marginTop: '12px' },
  btnPrimary: { padding: '6px 14px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '13px' },
  btnSecondary: { padding: '6px 14px', background: '#fff', color: '#333', border: '1px solid #ccc', borderRadius: '5px', cursor: 'pointer', fontSize: '13px' },
  btnDanger: { padding: '6px 14px', background: '#fff', color: '#dc3545', border: '1px solid #dc3545', borderRadius: '5px', cursor: 'pointer', fontSize: '13px' },
  empty: { textAlign: 'center', color: '#888', padding: '40px 0', fontSize: '14px' },
  errMsg: { color: '#dc3545', fontSize: '13px', marginTop: '8px' },
}

const X_URL_CHARS = 23
const TWEET_LIMIT = 140

function timeAgo(isoStr) {
  if (!isoStr) return ''
  const diff = Date.now() - new Date(isoStr + 'Z').getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}分前`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}時間前`
  return `${Math.floor(hrs / 24)}日前`
}

function CharCounter({ text }) {
  const count = (text?.length || 0) + X_URL_CHARS
  const isOver = count > TWEET_LIMIT
  return (
    <div style={{ ...styles.charCount, ...(isOver ? styles.charCountOver : styles.charCountOk) }}>
      {count}/{TWEET_LIMIT}文字
    </div>
  )
}

export default function News() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [fetching, setFetching] = useState(false)
  const [loadingIds, setLoadingIds] = useState({})
  const [err, setErr] = useState('')

  const load = useCallback(async () => {
    try {
      const data = await api.newsList()
      setItems(data)
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleFetch = async () => {
    setFetching(true)
    setErr('')
    try {
      await api.newsFetch()
      // バックグラウンド処理のため30秒後に自動リロード
      setTimeout(async () => {
        await load()
        setFetching(false)
      }, 30000)
    } catch (e) {
      setErr(e.message)
      setFetching(false)
    }
  }

  const setItemLoading = (id, val) => setLoadingIds(prev => ({ ...prev, [id]: val }))

  const handleAddToQueue = async (id) => {
    setItemLoading(id, 'queue')
    setErr('')
    try {
      await api.newsAddToQueue(id)
      setItems(prev => prev.filter(i => i.id !== id))
    } catch (e) {
      setErr(e.message)
    } finally {
      setItemLoading(id, null)
    }
  }

  const handleSkip = async (id) => {
    setItemLoading(id, 'skip')
    setErr('')
    try {
      await api.newsSkip(id)
      setItems(prev => prev.filter(i => i.id !== id))
    } catch (e) {
      setErr(e.message)
    } finally {
      setItemLoading(id, null)
    }
  }

  const handleRegenerate = async (id) => {
    setItemLoading(id, 'regen')
    setErr('')
    try {
      const res = await api.newsRegenerate(id)
      setItems(prev => prev.map(i => i.id === id ? { ...i, tweet_text: res.tweet_text } : i))
    } catch (e) {
      setErr(e.message)
    } finally {
      setItemLoading(id, null)
    }
  }

  if (loading) return <p style={{ color: '#888', textAlign: 'center', marginTop: '40px' }}>読み込み中...</p>

  return (
    <div>
      <div style={styles.topBar}>
        <button style={styles.fetchBtn} onClick={handleFetch} disabled={fetching}>
          {fetching ? 'バックグラウンド取得中...' : '今すぐ取得'}
        </button>
        <span style={styles.nextFetch}>未確認: {items.length}件</span>
      </div>

      {err && <p style={styles.errMsg}>{err}</p>}

      {items.length === 0 && !err && (
        <div style={styles.empty}>未確認のニュース記事はありません</div>
      )}

      {items.map(item => {
        const busy = loadingIds[item.id]
        return (
          <div key={item.id} style={styles.card}>
            <div style={styles.cardHeader}>
              <div style={styles.cardTitle}>{item.title}</div>
              <div style={styles.cardMeta}>
                {item.source_name && `${item.source_name} | `}{timeAgo(item.fetched_at)}
              </div>
            </div>

            {item.tweet_text ? (
              <>
                <div style={styles.tweetBox}>
                  {item.tweet_text}
                  {'\n'}{item.url}
                </div>
                <CharCounter text={item.tweet_text} />
              </>
            ) : (
              <div style={{ color: '#888', fontSize: '13px', marginTop: '8px' }}>ツイート未生成</div>
            )}

            <div style={styles.actions}>
              <button style={styles.btnPrimary} onClick={() => handleAddToQueue(item.id)} disabled={!!busy}>
                {busy === 'queue' ? '処理中...' : 'キューに追加'}
              </button>
              <button style={styles.btnSecondary} onClick={() => handleRegenerate(item.id)} disabled={!!busy}>
                {busy === 'regen' ? '生成中...' : '再生成'}
              </button>
              <button style={styles.btnDanger} onClick={() => handleSkip(item.id)} disabled={!!busy}>
                {busy === 'skip' ? '処理中...' : 'スキップ'}
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
