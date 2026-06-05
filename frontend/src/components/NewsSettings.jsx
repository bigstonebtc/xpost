import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api'


const styles = {
  section: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '20px', marginBottom: '20px' },
  sectionTitle: { fontSize: '16px', fontWeight: 'bold', marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid #eee' },
  row: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '10px 0', borderBottom: '1px solid #f0f0f0' },
  rowLabel: { fontSize: '14px', fontWeight: '500' },
  rowMeta: { fontSize: '12px', color: '#888', marginTop: '2px' },
  toggle: { cursor: 'pointer', flexShrink: 0, marginLeft: '12px', marginTop: '2px' },
  urlInput: { width: '100%', marginTop: '6px', padding: '5px 8px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px', fontFamily: 'monospace', color: '#555', boxSizing: 'border-box' },
  nameInput: { width: '100%', marginTop: '6px', padding: '5px 8px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '13px', boxSizing: 'border-box' },
  saveBtn: { marginTop: '14px', padding: '8px 20px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  addBtn: { marginBottom: '14px', padding: '7px 16px', background: '#2b6cb0', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '13px' },
  editBtn: { padding: '4px 10px', background: '#fff', color: '#2b6cb0', border: '1px solid #2b6cb0', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', marginLeft: '6px' },
  deleteBtn: { padding: '4px 10px', background: '#fff', color: '#e53e3e', border: '1px solid #e53e3e', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', marginLeft: '6px' },
  cancelBtn: { padding: '4px 10px', background: '#fff', color: '#718096', border: '1px solid #718096', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', marginLeft: '6px' },
  doneBtn: { padding: '4px 10px', background: '#38a169', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', marginLeft: '6px' },
  addForm: { background: '#f7f9fc', border: '1px solid #d0dce8', borderRadius: '6px', padding: '14px', marginBottom: '14px' },
  addFormTitle: { fontSize: '13px', fontWeight: 'bold', marginBottom: '10px', color: '#2b6cb0' },
  addFormRow: { display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' },
  addFormLabel: { fontSize: '12px', color: '#555', width: '60px', flexShrink: 0 },
  addFormInput: { flex: 1, padding: '5px 8px', border: '1px solid #ccc', borderRadius: '4px', fontSize: '13px', boxSizing: 'border-box' },
  presetBadge: { fontSize: '10px', color: '#999', background: '#f0f0f0', borderRadius: '3px', padding: '1px 5px', marginLeft: '6px' },
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
  const [editingId, setEditingId] = useState(null)
  const [editDraft, setEditDraft] = useState({})
  const [showAddForm, setShowAddForm] = useState(false)
  const [newSource, setNewSource] = useState({ name: '', url: '', category: '経済', is_enabled: true })

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

  const startEdit = (s) => {
    setEditingId(s.id)
    setEditDraft({ name: s.name, url: s.url, category: s.category || '', is_enabled: s.is_enabled })
  }

  const cancelEdit = () => { setEditingId(null); setEditDraft({}) }

  const saveEdit = async (id) => {
    setSaving(true)
    try {
      await api.newsUpdateSource(id, editDraft.is_enabled, editDraft.url, editDraft.name)
      setSources(prev => prev.map(s => s.id === id ? { ...s, ...editDraft } : s))
      setEditingId(null)
      flash('ok', '保存しました')
    } catch (e) {
      flash('err', e.message)
    } finally {
      setSaving(false)
    }
  }

  const toggleEnabled = async (s) => {
    const next = !s.is_enabled
    setSources(prev => prev.map(x => x.id === s.id ? { ...x, is_enabled: next } : x))
    try {
      await api.newsUpdateSource(s.id, next, s.url, s.name)
    } catch (e) {
      setSources(prev => prev.map(x => x.id === s.id ? { ...x, is_enabled: s.is_enabled } : x))
      flash('err', e.message)
    }
  }

  const deleteSource = async (id) => {
    if (!confirm('このソースを削除しますか？')) return
    setSaving(true)
    try {
      await api.newsDeleteSource(id)
      setSources(prev => prev.filter(s => s.id !== id))
      flash('ok', '削除しました')
    } catch (e) {
      flash('err', e.message)
    } finally {
      setSaving(false)
    }
  }

  const addSource = async () => {
    if (!newSource.name.trim()) { flash('err', '名前を入力してください'); return }
    if (!newSource.url.trim()) { flash('err', 'URLを入力してください'); return }
    setSaving(true)
    try {
      const created = await api.newsAddSource(newSource.name.trim(), newSource.url.trim(), newSource.category)
      setSources(prev => [...prev, created])
      setNewSource({ name: '', url: '', category: '経済', is_enabled: true })
      setShowAddForm(false)
      flash('ok', 'ソースを追加しました')
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

        <button style={styles.addBtn} onClick={() => setShowAddForm(v => !v)}>
          {showAddForm ? '▲ キャンセル' : '+ 新規ソースを追加'}
        </button>

        {showAddForm && (
          <div style={styles.addForm}>
            <div style={styles.addFormTitle}>新規ソース追加</div>
            <div style={styles.addFormRow}>
              <span style={styles.addFormLabel}>名前</span>
              <input style={styles.addFormInput} type="text" placeholder="例: Google News - 相続税" value={newSource.name} onChange={e => setNewSource(p => ({ ...p, name: e.target.value }))} />
            </div>
            <div style={styles.addFormRow}>
              <span style={styles.addFormLabel}>URL</span>
              <input style={styles.addFormInput} type="url" placeholder="https://..." value={newSource.url} onChange={e => setNewSource(p => ({ ...p, url: e.target.value }))} />
            </div>
            <div style={styles.addFormRow}>
              <span style={styles.addFormLabel}>カテゴリ</span>
              <input style={{ ...styles.addFormInput, maxWidth: '140px' }} type="text" placeholder="経済" value={newSource.category} onChange={e => setNewSource(p => ({ ...p, category: e.target.value }))} />
            </div>
            <button style={{ ...styles.doneBtn, marginLeft: 0, padding: '6px 18px', fontSize: '13px' }} onClick={addSource} disabled={saving}>追加</button>
          </div>
        )}

        {sources.map(s => (
          <div key={s.id} style={{ ...styles.row, flexDirection: 'column', alignItems: 'stretch' }}>
            {editingId === s.id ? (
              <div style={{ padding: '4px 0' }}>
                <input style={styles.nameInput} type="text" value={editDraft.name} onChange={e => setEditDraft(p => ({ ...p, name: e.target.value }))} placeholder="名前" />
                <input style={styles.urlInput} type="url" value={editDraft.url} onChange={e => setEditDraft(p => ({ ...p, url: e.target.value }))} placeholder="URL" />
                <div style={{ display: 'flex', alignItems: 'center', marginTop: '8px', gap: '8px' }}>
                  <label style={{ fontSize: '13px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <input type="checkbox" checked={editDraft.is_enabled} onChange={e => setEditDraft(p => ({ ...p, is_enabled: e.target.checked }))} />
                    有効
                  </label>
                  <button style={{ ...styles.doneBtn, marginLeft: 0 }} onClick={() => saveEdit(s.id)} disabled={saving}>保存</button>
                  <button style={{ ...styles.cancelBtn, marginLeft: 0 }} onClick={cancelEdit} disabled={saving}>キャンセル</button>
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span style={{ ...styles.rowLabel, color: s.is_enabled ? '#1a1a2e' : '#aaa' }}>{s.name}</span>
                    {s.is_preset && <span style={styles.presetBadge}>固定</span>}
                    <span style={{ ...styles.rowMeta, marginTop: 0, marginLeft: '8px' }}>{s.category}</span>
                  </div>
                  <div style={{ fontSize: '11px', color: '#999', fontFamily: 'monospace', marginTop: '3px', wordBreak: 'break-all' }}>{s.url}</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0, marginLeft: '10px' }}>
                  <label style={{ cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <input type="checkbox" checked={s.is_enabled} onChange={() => toggleEnabled(s)} />
                    <span style={{ color: s.is_enabled ? '#38a169' : '#aaa' }}>{s.is_enabled ? 'ON' : 'OFF'}</span>
                  </label>
                  <button style={styles.editBtn} onClick={() => startEdit(s)}>編集</button>
                  {!s.is_preset && (
                    <button style={styles.deleteBtn} onClick={() => deleteSource(s.id)} disabled={saving}>削除</button>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
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
