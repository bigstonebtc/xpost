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
}

export default function PostSettings() {
  const [scheduleMode, setScheduleMode] = useState('120min')
  const [savedSettings, setSavedSettings] = useState(null)
  const [dailyLimit, setDailyLimit] = useState(10)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savingLimit, setSavingLimit] = useState(false)
  const [msg, setMsg] = useState({ type: '', text: '' })
  const [limitMsg, setLimitMsg] = useState({ type: '', text: '' })

  const load = useCallback(async () => {
    try {
      const [newsData, postingData] = await Promise.all([api.newsSettings(), api.getPostingSettings()])
      if (newsData.general) {
        setScheduleMode(newsData.general.schedule_mode || '120min')
        setSavedSettings(newsData.general)
      }
      setDailyLimit(postingData.daily_schedule_limit ?? 10)
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

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
    if (!savedSettings) return
    setSaving(true)
    try {
      await api.newsUpdateGeneral(
        savedSettings.fetch_limit_per_run,
        null,
        scheduleMode,
        savedSettings.news_prompt_file,
      )
      setSavedSettings(prev => ({ ...prev, schedule_mode: scheduleMode }))
      flash('ok', '保存しました')
    } catch (e) {
      flash('err', e.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p style={{ color: '#888', textAlign: 'center', marginTop: '40px' }}>読み込み中...</p>

  const modes = [
    { value: '120min', label: '120分以内にランダム投稿', desc: 'Scheduleボタンを押してから最大120分以内にランダムなタイミングで投稿' },
    { value: '24h_daytime', label: '24時間以内・日中（JST 7:00〜20:00）にランダム投稿', desc: '向こう24時間以内の朝7時〜夜8時の範囲でランダムなタイミングで投稿' },
    { value: '72h', label: '72時間以内にランダム投稿', desc: 'Scheduleボタンを押してから最大72時間以内にランダムなタイミングで投稿' },
    { value: '120h', label: '120時間以内にランダム投稿', desc: 'Scheduleボタンを押してから最大120時間以内にランダムなタイミングで投稿' },
  ]

  return (
    <div>
      {msg.text && <p style={msg.type === 'ok' ? styles.successMsg : styles.errMsg}>{msg.text}</p>}

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
        <div style={styles.radioRow}>
          {modes.map(m => (
            <label key={m.value} style={styles.radioLabel}>
              <input
                type="radio"
                name="scheduleMode"
                value={m.value}
                checked={scheduleMode === m.value}
                onChange={() => setScheduleMode(m.value)}
              />
              <div>
                <div>{m.label}</div>
                <div style={styles.radioDesc}>{m.desc}</div>
              </div>
            </label>
          ))}
        </div>
        <button style={styles.saveBtn} onClick={save} disabled={saving || !savedSettings}>
          {saving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  )
}
