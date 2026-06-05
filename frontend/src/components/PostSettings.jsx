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
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState({ type: '', text: '' })

  const load = useCallback(async () => {
    try {
      const data = await api.newsSettings()
      if (data.general) {
        setScheduleMode(data.general.schedule_mode || '120min')
        setSavedSettings(data.general)
      }
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

  const save = async () => {
    if (!savedSettings) return
    setSaving(true)
    try {
      await api.newsUpdateGeneral(
        savedSettings.fetch_limit_per_run,
        savedSettings.relevance_prompt,
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
