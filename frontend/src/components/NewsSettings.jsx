import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'


const styles = {
  section: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '20px', marginBottom: '20px' },
  sectionTitle: { fontSize: '16px', fontWeight: 'bold', marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid #eee' },
  row: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '10px 0', borderBottom: '1px solid #f0f0f0' },
  rowLabel: { fontSize: '14px' },
  rowMeta: { fontSize: '12px', color: '#888', marginTop: '2px' },
  toggle: { cursor: 'pointer', flexShrink: 0, marginLeft: '12px', marginTop: '2px' },
  urlInput: { width: '100%', marginTop: '6px', padding: '5px 8px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px', fontFamily: 'monospace', color: '#555', boxSizing: 'border-box' },
  saveBtn: { marginTop: '14px', padding: '8px 20px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  slotRow: { display: 'flex', alignItems: 'center', gap: '12px', padding: '8px 0', borderBottom: '1px solid #f0f0f0' },
  slotLabel: { fontSize: '14px', width: '70px' },
  select: { padding: '4px 8px', border: '1px solid #ccc', borderRadius: '4px', fontSize: '14px' },
  limitRow: { display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 0', borderBottom: '1px solid #f0f0f0', marginBottom: '4px' },
  limitLabel: { fontSize: '14px', flex: 1 },
  promptArea: { width: '100%', minHeight: '200px', padding: '10px', border: '1px solid #ccc', borderRadius: '6px', fontSize: '13px', fontFamily: 'monospace', lineHeight: '1.6', resize: 'vertical', boxSizing: 'border-box' },
  promptHint: { fontSize: '12px', color: '#888', marginTop: '6px' },
  radioRow: { display: 'flex', flexDirection: 'column', gap: '10px', padding: '12px 0' },
  radioLabel: { display: 'flex', alignItems: 'flex-start', gap: '8px', cursor: 'pointer', fontSize: '14px' },
  radioDesc: { fontSize: '12px', color: '#888', marginTop: '2px' },
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
  const [scheduleMode, setScheduleMode] = useState('120min')
  const [newsPromptFile, setNewsPromptFile] = useState('news_comment.prompt')
  const [availablePrompts, setAvailablePrompts] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState({ type: '', text: '' })

  const load = useCallback(async () => {
    try {
      const [data, promptList] = await Promise.all([api.newsSettings(), api.listPrompts()])
      setSources(data.sources)
      setSchedules(data.schedules)
      setAvailablePrompts(promptList)
      if (data.general) {
        setFetchLimit(data.general.fetch_limit_per_run)
        setPrompt(data.general.relevance_prompt)
        setScheduleMode(data.general.schedule_mode || '120min')
        setNewsPromptFile(data.general.news_prompt_file || 'news_comment.prompt')
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

  const updateSourceUrl = (id, url) => {
    setSources(prev => prev.map(s => s.id === id ? { ...s, url } : s))
  }

  const saveSources = async () => {
    setSaving(true)
    try {
      await Promise.all(sources.map(s => api.newsUpdateSource(s.id, s.is_enabled, s.url)))
      flash('ok', 'RSSソース設定を保存しました')
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
      await api.newsUpdateGeneral(fetchLimit, prompt, scheduleMode, newsPromptFile)
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
      {msg.text && (
        <p style={msg.type === 'ok' ? styles.successMsg : styles.errMsg}>{msg.text}</p>
      )}

      {/* キュー設定 */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>キュー設定</div>
        <div style={styles.radioRow}>
          <label style={styles.radioLabel}>
            <input
              type="radio"
              name="scheduleMode"
              value="120min"
              checked={scheduleMode === '120min'}
              onChange={() => setScheduleMode('120min')}
            />
            <div>
              <div>120分以内にランダム投稿</div>
              <div style={styles.radioDesc}>Scheduleボタンを押してから最大120分以内にランダムなタイミングで投稿</div>
            </div>
          </label>
          <label style={styles.radioLabel}>
            <input
              type="radio"
              name="scheduleMode"
              value="24h_daytime"
              checked={scheduleMode === '24h_daytime'}
              onChange={() => setScheduleMode('24h_daytime')}
            />
            <div>
              <div>24時間以内・日中（JST 7:00〜20:00）にランダム投稿</div>
              <div style={styles.radioDesc}>向こう24時間以内の朝7時〜夜8時の範囲でランダムなタイミングで投稿</div>
            </div>
          </label>
          <label style={styles.radioLabel}>
            <input
              type="radio"
              name="scheduleMode"
              value="72h"
              checked={scheduleMode === '72h'}
              onChange={() => setScheduleMode('72h')}
            />
            <div>
              <div>72時間以内にランダム投稿</div>
              <div style={styles.radioDesc}>Scheduleボタンを押してから最大72時間以内にランダムなタイミングで投稿</div>
            </div>
          </label>
          <label style={styles.radioLabel}>
            <input
              type="radio"
              name="scheduleMode"
              value="120h"
              checked={scheduleMode === '120h'}
              onChange={() => setScheduleMode('120h')}
            />
            <div>
              <div>120時間以内にランダム投稿</div>
              <div style={styles.radioDesc}>Scheduleボタンを押してから最大120時間以内にランダムなタイミングで投稿</div>
            </div>
          </label>
        </div>
        <button style={styles.saveBtn} onClick={saveGeneral} disabled={saving}>保存</button>
      </div>

      {/* RSSソース */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>ニュース — RSSソース</div>
        {sources.map(s => (
          <div key={s.id} style={styles.row}>
            <div style={{ flex: 1 }}>
              <div style={styles.rowLabel}>{s.name}</div>
              <div style={styles.rowMeta}>{s.category}</div>
              <input
                style={styles.urlInput}
                type="url"
                value={s.url}
                onChange={e => updateSourceUrl(s.id, e.target.value)}
              />
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

      {/* スケジュール・件数 */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>ニュース — 取得スケジュール・件数</div>

        <div style={styles.limitRow}>
          <span style={styles.limitLabel}>1回あたりの取得件数上限</span>
          <select style={styles.select} value={fetchLimit} onChange={e => setFetchLimit(Number(e.target.value))}>
            {LIMIT_OPTIONS.map(n => <option key={n} value={n}>{n}件</option>)}
          </select>
        </div>

        <div style={styles.limitRow}>
          <span style={styles.limitLabel}>ニュース生成に使用するプロンプト</span>
          <select style={styles.select} value={newsPromptFile} onChange={e => setNewsPromptFile(e.target.value)}>
            {availablePrompts.length === 0
              ? <option value="news_comment.prompt">news_comment.prompt</option>
              : availablePrompts.map(p => (
                <option key={p.filename} value={p.filename}>{p.name}</option>
              ))
            }
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

      {/* AI関連度判定プロンプト */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>ニュース — AI関連度判定プロンプト</div>
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
