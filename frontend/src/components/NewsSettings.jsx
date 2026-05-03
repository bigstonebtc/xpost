import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'

const styles = {
  section: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '20px', marginBottom: '20px' },
  sectionTitle: { fontSize: '16px', fontWeight: 'bold', marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid #eee' },
  row: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f0f0f0' },
  rowLabel: { fontSize: '14px' },
  rowMeta: { fontSize: '12px', color: '#888', marginTop: '2px' },
  toggle: { cursor: 'pointer' },
  saveBtn: { marginTop: '14px', padding: '8px 20px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  slotRow: { display: 'flex', alignItems: 'center', gap: '12px', padding: '8px 0', borderBottom: '1px solid #f0f0f0' },
  slotLabel: { fontSize: '14px', width: '70px' },
  select: { padding: '4px 8px', border: '1px solid #ccc', borderRadius: '4px', fontSize: '14px' },
  limitRow: { display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 0', borderBottom: '1px solid #f0f0f0', marginBottom: '4px' },
  limitLabel: { fontSize: '14px', flex: 1 },
  promptArea: { width: '100%', minHeight: '200px', padding: '10px', border: '1px solid #ccc', borderRadius: '6px', fontSize: '13px', fontFamily: 'monospace', lineHeight: '1.6', resize: 'vertical', boxSizing: 'border-box' },
  promptHint: { fontSize: '12px', color: '#888', marginTop: '6px' },
  errMsg: { color: '#dc3545', fontSize: '13px', marginTop: '8px' },
  successMsg: { color: '#198754', fontSize: '13px', marginTop: '8px' },
}

const HOURS = Array.from({ length: 24 }, (_, i) => i)
const LIMIT_OPTIONS = [20, 50, 100]

export default function NewsSettings() {
  const [sources, setSources] = useState([])
  const [schedules, setSchedules] = useState([])
  const [fetchLimit, setFetchLimit] = useState(20)
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState({ type: '', text: '' })

  const load = useCallback(async () => {
    try {
      const data = await api.newsSettings()
      setSources(data.sources)
      setSchedules(data.schedules)
      if (data.general) {
        setFetchLimit(data.general.fetch_limit_per_run)
        setPrompt(data.general.relevance_prompt)
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

  const toggleSource = (id) => {
    setSources(prev => prev.map(s => s.id === id ? { ...s, is_enabled: !s.is_enabled } : s))
  }

  const saveSources = async () => {
    setSaving(true)
    try {
      await Promise.all(sources.map(s => api.newsUpdateSource(s.id, s.is_enabled)))
      flash('ok', 'ソース設定を保存しました')
    } catch (e) {
      flash('err', e.message)
    } finally {
      setSaving(false)
    }
  }

  const updateScheduleSlot = (slotNumber, field, value) => {
    setSchedules(prev => prev.map(s => s.slot_number === slotNumber ? { ...s, [field]: value } : s))
  }

  const saveSchedule = async () => {
    setSaving(true)
    try {
      await api.newsUpdateSchedule(schedules.map(s => ({
        slot_number: s.slot_number,
        hour: Number(s.hour),
        is_enabled: s.is_enabled,
      })))
      flash('ok', 'スケジュール・件数設定を保存しました')
    } catch (e) {
      flash('err', e.message)
    } finally {
      setSaving(false)
    }
  }

  const saveGeneral = async () => {
    if (!prompt.includes('{title}') || !prompt.includes('{summary}')) {
      flash('err', '{title} と {summary} のプレースホルダーが必要です')
      return
    }
    setSaving(true)
    try {
      await api.newsUpdateGeneral(fetchLimit, prompt)
      flash('ok', '保存しました ✓')
    } catch (e) {
      flash('err', e.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p style={{ color: '#888', textAlign: 'center', marginTop: '40px' }}>読み込み中...</p>

  return (
    <div>
      {msg.text && (
        <p style={msg.type === 'ok' ? styles.successMsg : styles.errMsg}>{msg.text}</p>
      )}

      {/* セクション1: RSSソース */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>RSSソース</div>
        {sources.map(s => (
          <div key={s.id} style={styles.row}>
            <div>
              <div style={styles.rowLabel}>{s.name}</div>
              <div style={styles.rowMeta}>{s.category}</div>
            </div>
            <label style={styles.toggle}>
              <input
                type="checkbox"
                checked={s.is_enabled}
                onChange={() => toggleSource(s.id)}
              />
            </label>
          </div>
        ))}
        <button style={styles.saveBtn} onClick={saveSources} disabled={saving}>保存</button>
      </div>

      {/* セクション2: スケジュール・件数 */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>取得スケジュール・件数</div>

        <div style={styles.limitRow}>
          <span style={styles.limitLabel}>1回あたりの取得件数上限</span>
          <select style={styles.select} value={fetchLimit} onChange={e => setFetchLimit(Number(e.target.value))}>
            {LIMIT_OPTIONS.map(n => <option key={n} value={n}>{n}件</option>)}
          </select>
        </div>

        {schedules.map(slot => (
          <div key={slot.slot_number} style={styles.slotRow}>
            <span style={styles.slotLabel}>スロット{slot.slot_number}</span>
            <select
              style={styles.select}
              value={slot.hour}
              onChange={e => updateScheduleSlot(slot.slot_number, 'hour', e.target.value)}
            >
              {HOURS.map(h => (
                <option key={h} value={h}>{String(h).padStart(2, '0')}:00</option>
              ))}
            </select>
            <label style={styles.toggle}>
              <input
                type="checkbox"
                checked={slot.is_enabled}
                onChange={() => updateScheduleSlot(slot.slot_number, 'is_enabled', !slot.is_enabled)}
              />
              <span style={{ marginLeft: '4px', fontSize: '13px' }}>有効</span>
            </label>
          </div>
        ))}
        <button style={styles.saveBtn} onClick={saveSchedule} disabled={saving}>保存</button>
      </div>

      {/* セクション3: AI関連度判定プロンプト */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>AI関連度判定プロンプト</div>
        <textarea
          style={styles.promptArea}
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          spellCheck={false}
        />
        <p style={styles.promptHint}>
          ※ {'{title}'} {'{summary}'} はシステムが自動で置換します。この2つのプレースホルダーは必ず残してください。
        </p>
        <button style={styles.saveBtn} onClick={saveGeneral} disabled={saving}>保存</button>
      </div>
    </div>
  )
}
