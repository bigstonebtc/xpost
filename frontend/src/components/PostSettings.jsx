import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'

const styles = {
  section: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '20px', marginBottom: '20px' },
  sectionTitle: { fontSize: '16px', fontWeight: 'bold', marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid #eee' },
  saveBtn: { marginTop: '14px', padding: '8px 20px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  radioRow: { display: 'flex', flexDirection: 'column', gap: '10px', padding: '12px 0' },
  radioLabel: { display: 'flex', alignItems: 'flex-start', gap: '8px', cursor: 'pointer', fontSize: '14px' },
  radioDesc: { fontSize: '12px', color: '#888', marginTop: '2px' },
  errMsg: { color: '#dc3545', fontSize: '13px', marginTop: '8px' },
  successMsg: { color: '#198754', fontSize: '13px', marginTop: '8px' },
  statusRow: { display: 'flex', gap: '8px', fontSize: '14px', marginBottom: '6px' },
  statusLabel: { color: '#888', minWidth: '110px' },
  badgeOk: { color: '#198754', fontWeight: 'bold' },
  badgeErr: { color: '#dc3545', fontWeight: 'bold' },
  btnRow: { display: 'flex', gap: '8px', marginTop: '14px' },
  secondaryBtn: { padding: '8px 16px', background: '#fff', color: '#1a1a2e', border: '1px solid #ccc', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  note: { fontSize: '12px', color: '#888', marginTop: '10px', lineHeight: '1.6' },
  warnBadge: { color: '#dd8800', fontWeight: 'bold' },
}

const SCHEDULE_HOURS_MIN = 24
const SCHEDULE_HOURS_MAX = 720

export default function PostSettings() {
  const [scheduleHours, setScheduleHours] = useState(24)
  const [dailyLimit, setDailyLimit] = useState(10)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savingLimit, setSavingLimit] = useState(false)
  const [msg, setMsg] = useState({ type: '', text: '' })
  const [limitMsg, setLimitMsg] = useState({ type: '', text: '' })

  const [torStatus, setTorStatus] = useState(null)
  const [torChecking, setTorChecking] = useState(false)
  const [torRestarting, setTorRestarting] = useState(false)
  const [torMsg, setTorMsg] = useState({ type: '', text: '' })

  const [postingMode, setPostingMode] = useState('tor')
  const [defaultMode, setDefaultMode] = useState('tor')
  const [modeNote, setModeNote] = useState('')
  const [savingMode, setSavingMode] = useState(false)
  const [modeMsg, setModeMsg] = useState({ type: '', text: '' })

  const load = useCallback(async () => {
    try {
      const postingData = await api.getPostingSettings()
      setDailyLimit(postingData.daily_schedule_limit ?? 10)
      setScheduleHours(postingData.schedule_hours ?? 24)
      setPostingMode(postingData.posting_mode || 'tor')
      setDefaultMode(postingData.default_mode || 'tor')
      setModeNote(postingData.note || '')
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => { checkTorStatus() }, [])

  const checkTorStatus = async () => {
    setTorChecking(true)
    try {
      const s = await api.torStatus()
      setTorStatus(s)
    } catch (e) {
      setTorMsg({ type: 'err', text: e.message })
    } finally {
      setTorChecking(false)
    }
  }

  const restartTor = async () => {
    if (!confirm('Torコンテナを再起動しますか？（数十秒かかります）')) return
    setTorRestarting(true)
    setTorMsg({ type: '', text: '' })
    try {
      const s = await api.torRestart()
      setTorStatus(s)
      setTorMsg({ type: 'ok', text: '再起動しました ✓' })
    } catch (e) {
      setTorMsg({ type: 'err', text: e.message })
    } finally {
      setTorRestarting(false)
    }
  }

  const saveMode = async () => {
    setSavingMode(true)
    setModeMsg({ type: '', text: '' })
    try {
      const res = await api.updatePostingMode(postingMode)
      setDefaultMode(res.default_mode)
      setModeNote(res.note)
      setModeMsg({ type: 'ok', text: res.message })
    } catch (e) {
      setModeMsg({ type: 'err', text: e.message })
    } finally {
      setSavingMode(false)
    }
  }

  const flash = (type, text) => {
    setMsg({ type, text })
    setTimeout(() => setMsg({ type: '', text: '' }), 3000)
  }

  const flashLimit = (type, text) => {
    setLimitMsg({ type, text })
    setTimeout(() => setLimitMsg({ type: '', text: '' }), 3000)
  }

  const saveLimit = async () => {
    const val = Number(dailyLimit)
    if (!Number.isInteger(val) || val < 1) {
      flashLimit('err', '1以上の整数を入力してください')
      return
    }
    setSavingLimit(true)
    try {
      await api.updatePostingSettings(val)
      flashLimit('ok', '保存しました ✓')
    } catch (e) {
      flashLimit('err', e.message)
    } finally {
      setSavingLimit(false)
    }
  }

  const save = async () => {
    const val = Number(scheduleHours)
    if (!Number.isInteger(val) || val < SCHEDULE_HOURS_MIN || val > SCHEDULE_HOURS_MAX) {
      flash('err', `${SCHEDULE_HOURS_MIN}〜${SCHEDULE_HOURS_MAX}の整数で指定してください`)
      return
    }
    setSaving(true)
    try {
      await api.updateScheduleHours(val)
      flash('ok', '保存しました')
    } catch (e) {
      flash('err', e.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p style={{ color: '#888', textAlign: 'center', marginTop: '40px' }}>読み込み中...</p>

  return (
    <div>
      {msg.text && <p style={msg.type === 'ok' ? styles.successMsg : styles.errMsg}>{msg.text}</p>}

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Tor Service</div>
        <div style={styles.statusRow}>
          <span style={styles.statusLabel}>Status:</span>
          {torStatus
            ? <span style={torStatus.tor_connected ? styles.badgeOk : styles.badgeErr}>
                {torStatus.tor_connected ? 'Active' : 'Error'}
              </span>
            : <span style={{ color: '#888' }}>{torChecking ? '確認中...' : '未確認'}</span>}
        </div>
        <div style={styles.statusRow}>
          <span style={styles.statusLabel}>Exit IP:</span>
          <span>{torStatus?.exit_ip || '—'}</span>
        </div>
        <div style={styles.statusRow}>
          <span style={styles.statusLabel}>Last Checked:</span>
          <span>{torStatus?.last_verified_at ? new Date(torStatus.last_verified_at).toLocaleString('ja-JP') : '—'}</span>
        </div>
        {torStatus && !torStatus.tor_connected && torStatus.error && (
          <p style={styles.errMsg}>{torStatus.error}</p>
        )}
        {torMsg.text && <p style={torMsg.type === 'ok' ? styles.successMsg : styles.errMsg}>{torMsg.text}</p>}
        <div style={styles.btnRow}>
          <button style={styles.secondaryBtn} onClick={checkTorStatus} disabled={torChecking || torRestarting}>
            {torChecking ? '確認中...' : 'Check Status'}
          </button>
          <button style={styles.secondaryBtn} onClick={restartTor} disabled={torChecking || torRestarting}>
            {torRestarting ? '再起動中...' : 'Restart'}
          </button>
        </div>
        <p style={styles.note}>Torが起動していない・出口IPを確認できない場合、投稿は一切実行されません。</p>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Posting Mode</div>
        <p style={{ fontSize: '13px', color: '#555', marginBottom: '4px' }}>
          現在の設定：{postingMode === 'tor' ? 'Tor Mode' : 'Direct Mode'}
        </p>
        <div style={styles.radioRow}>
          <label style={styles.radioLabel}>
            <input type="radio" name="postingMode" value="tor" checked={postingMode === 'tor'} onChange={() => setPostingMode('tor')} />
            <div>
              <div>Tor Mode（推奨）</div>
              <div style={styles.radioDesc}>Tor ネットワーク経由で投稿します</div>
            </div>
          </label>
          <label style={styles.radioLabel}>
            <input type="radio" name="postingMode" value="direct" checked={postingMode === 'direct'} onChange={() => setPostingMode('direct')} />
            <div>
              <div>Direct Mode（緊急用） <span style={styles.warnBadge}>⚠️</span></div>
              <div style={styles.radioDesc}>Tor を経由せず直接投稿します。VPS の IP が X に記録されます。</div>
            </div>
          </label>
        </div>
        {modeMsg.text && <p style={modeMsg.type === 'ok' ? styles.successMsg : styles.errMsg}>{modeMsg.text}</p>}
        <button style={styles.saveBtn} onClick={saveMode} disabled={savingMode}>
          {savingMode ? '保存中...' : '保存'}
        </button>
        <p style={styles.note}>
          デフォルト：{defaultMode === 'tor' ? 'Tor Mode' : 'Direct Mode'}（.env の POSTING_MODE）<br />
          {modeNote || 'Docker 再起動でデフォルト値に戻ります'}
        </p>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>キュー設定</div>
        <div style={{ padding: '12px 0', borderBottom: '1px solid #f0f0f0', marginBottom: '4px' }}>
          <div style={{ fontSize: '14px', marginBottom: '10px', fontWeight: '500' }}>1日のSchedule投稿上限</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <input
              type="number"
              min="1"
              step="1"
              value={dailyLimit}
              onChange={e => setDailyLimit(e.target.value)}
              style={{ width: '80px', padding: '7px 10px', border: '1px solid #aaa', borderRadius: '4px', fontSize: '14px' }}
            />
            <span style={{ fontSize: '13px', color: '#555' }}>件</span>
          </div>
          <p style={{ fontSize: '12px', color: '#888', marginTop: '6px', marginBottom: '0' }}>
            ※ Post nowでの投稿はカウントされません
          </p>
          {limitMsg.text && <p style={limitMsg.type === 'ok' ? styles.successMsg : styles.errMsg}>{limitMsg.text}</p>}
          <button style={styles.saveBtn} onClick={saveLimit} disabled={savingLimit}>
            {savingLimit ? '保存中...' : '保存'}
          </button>
        </div>
        <div style={{ padding: '12px 0' }}>
          <div style={{ fontSize: '14px', marginBottom: '10px', fontWeight: '500' }}>投稿タイミング</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <input
              type="number"
              min={SCHEDULE_HOURS_MIN}
              max={SCHEDULE_HOURS_MAX}
              step="1"
              value={scheduleHours}
              onChange={e => setScheduleHours(e.target.value)}
              style={{ width: '80px', padding: '7px 10px', border: '1px solid #aaa', borderRadius: '4px', fontSize: '14px' }}
            />
            <span style={{ fontSize: '13px', color: '#555' }}>時間以内にランダム投稿</span>
          </div>
          <p style={styles.note}>
            指定した時間内で、日中（JST 7:00〜20:00）のランダムなタイミングに投稿します（{SCHEDULE_HOURS_MIN}〜{SCHEDULE_HOURS_MAX}時間で指定）。
          </p>
        </div>
        <button style={styles.saveBtn} onClick={save} disabled={saving}>
          {saving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  )
}
