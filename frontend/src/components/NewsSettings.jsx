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
  slotLabel: { fontSize: '14px', width: '60px' },
  select: { padding: '4px 8px', border: '1px solid #ccc', borderRadius: '4px', fontSize: '14px' },
  tagArea: { display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' },
  tag: { display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '4px 10px', borderRadius: '16px', fontSize: '13px' },
  tagInclude: { background: '#e8f4fd', color: '#0d6efd' },
  tagExclude: { background: '#fde8e8', color: '#dc3545' },
  tagDelete: { background: 'none', border: 'none', cursor: 'pointer', fontSize: '14px', lineHeight: 1, padding: '0 2px' },
  addRow: { display: 'flex', gap: '8px', marginTop: '6px' },
  input: { flex: 1, padding: '6px 10px', border: '1px solid #ccc', borderRadius: '5px', fontSize: '14px' },
  addBtn: { padding: '6px 14px', background: '#fff', border: '1px solid #ccc', borderRadius: '5px', cursor: 'pointer', fontSize: '13px' },
  typeToggle: { display: 'flex', border: '1px solid #ccc', borderRadius: '5px', overflow: 'hidden' },
  typeBtn: { padding: '6px 12px', border: 'none', cursor: 'pointer', fontSize: '13px' },
  typeBtnActive: { background: '#1a1a2e', color: '#fff' },
  typeBtnInactive: { background: '#fff', color: '#333' },
  errMsg: { color: '#dc3545', fontSize: '13px', marginTop: '8px' },
  successMsg: { color: '#198754', fontSize: '13px', marginTop: '8px' },
}

const HOURS = Array.from({ length: 24 }, (_, i) => i)

export default function NewsSettings() {
  const [sources, setSources] = useState([])
  const [schedules, setSchedules] = useState([])
  const [keywords, setKeywords] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState({ type: '', text: '' })
  const [newKw, setNewKw] = useState('')
  const [newKwType, setNewKwType] = useState('include')

  const load = useCallback(async () => {
    try {
      const data = await api.newsSettings()
      setSources(data.sources)
      setSchedules(data.schedules)
      setKeywords(data.keywords)
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
      flash('ok', 'スケジュールを保存しました')
    } catch (e) {
      flash('err', e.message)
    } finally {
      setSaving(false)
    }
  }

  const addKeyword = async () => {
    const kw = newKw.trim()
    if (!kw) return
    try {
      const added = await api.newsAddKeyword(kw, newKwType)
      setKeywords(prev => [...prev, added])
      setNewKw('')
    } catch (e) {
      flash('err', e.message)
    }
  }

  const deleteKeyword = async (id) => {
    try {
      await api.newsDeleteKeyword(id)
      setKeywords(prev => prev.filter(k => k.id !== id))
    } catch (e) {
      flash('err', e.message)
    }
  }

  if (loading) return <p style={{ color: '#888', textAlign: 'center', marginTop: '40px' }}>読み込み中...</p>

  const includeKws = keywords.filter(k => k.type === 'include')
  const excludeKws = keywords.filter(k => k.type === 'exclude')

  return (
    <div>
      {msg.text && (
        <p style={msg.type === 'ok' ? styles.successMsg : styles.errMsg}>{msg.text}</p>
      )}

      {/* RSSソース */}
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

      {/* 取得スケジュール */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>取得スケジュール</div>
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

      {/* キーワードフィルタリング */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>キーワードフィルタリング</div>

        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '13px', color: '#555', marginBottom: '6px' }}>取得キーワード（OR条件）</div>
          <div style={styles.tagArea}>
            {includeKws.map(k => (
              <span key={k.id} style={{ ...styles.tag, ...styles.tagInclude }}>
                {k.keyword}
                <button style={styles.tagDelete} onClick={() => deleteKeyword(k.id)}>×</button>
              </span>
            ))}
            {includeKws.length === 0 && <span style={{ color: '#aaa', fontSize: '13px' }}>なし</span>}
          </div>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '13px', color: '#555', marginBottom: '6px' }}>除外キーワード</div>
          <div style={styles.tagArea}>
            {excludeKws.map(k => (
              <span key={k.id} style={{ ...styles.tag, ...styles.tagExclude }}>
                {k.keyword}
                <button style={styles.tagDelete} onClick={() => deleteKeyword(k.id)}>×</button>
              </span>
            ))}
            {excludeKws.length === 0 && <span style={{ color: '#aaa', fontSize: '13px' }}>なし</span>}
          </div>
        </div>

        <div style={styles.addRow}>
          <input
            style={styles.input}
            type="text"
            placeholder="キーワードを追加..."
            value={newKw}
            onChange={e => setNewKw(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addKeyword()}
          />
          <div style={styles.typeToggle}>
            <button
              style={{ ...styles.typeBtn, ...(newKwType === 'include' ? styles.typeBtnActive : styles.typeBtnInactive) }}
              onClick={() => setNewKwType('include')}
            >取得</button>
            <button
              style={{ ...styles.typeBtn, ...(newKwType === 'exclude' ? styles.typeBtnActive : styles.typeBtnInactive) }}
              onClick={() => setNewKwType('exclude')}
            >除外</button>
          </div>
          <button style={styles.addBtn} onClick={addKeyword}>追加</button>
        </div>
      </div>
    </div>
  )
}
