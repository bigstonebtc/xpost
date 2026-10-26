import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'

const styles = {
  section: { background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '20px', marginBottom: '20px' },
  sectionTitle: { fontSize: '16px', fontWeight: 'bold', marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid #eee' },
  row: { padding: '12px 0', borderBottom: '1px solid #f0f0f0' },
  rowLast: { padding: '12px 0' },
  label: { fontSize: '14px', marginBottom: '10px', fontWeight: '500' },
  inputRow: { display: 'flex', alignItems: 'center', gap: '10px' },
  input: { width: '120px', padding: '7px 10px', border: '1px solid #aaa', borderRadius: '4px', fontSize: '14px' },
  unit: { fontSize: '13px', color: '#555' },
  btnRow: { display: 'flex', gap: '8px', marginTop: '14px' },
  saveBtn: { padding: '8px 20px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  cancelBtn: { padding: '8px 16px', background: '#fff', color: '#718096', border: '1px solid #ccc', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' },
  errMsg: { color: '#dc3545', fontSize: '13px', marginTop: '8px' },
  successMsg: { color: '#198754', fontSize: '13px', marginTop: '8px' },
}

export default function ClaudeSettings() {
  const [inputPrice, setInputPrice] = useState('2')
  const [outputPrice, setOutputPrice] = useState('10')
  const [saved, setSaved] = useState({ inputPrice: '2', outputPrice: '10' })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState({ type: '', text: '' })

  const load = useCallback(async () => {
    try {
      const cfg = await api.getClaudePricing()
      const ip = String(cfg.claude_input_tokens_price)
      const op = String(cfg.claude_output_tokens_price)
      setInputPrice(ip)
      setOutputPrice(op)
      setSaved({ inputPrice: ip, outputPrice: op })
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleSave = async () => {
    setSaving(true)
    setMsg({ type: '', text: '' })
    try {
      await api.updateClaudePricing(Number(inputPrice), Number(outputPrice))
      setSaved({ inputPrice, outputPrice })
      setMsg({ type: 'ok', text: '保存しました' })
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setInputPrice(saved.inputPrice)
    setOutputPrice(saved.outputPrice)
    setMsg({ type: '', text: '' })
  }

  if (loading) return <p style={{ color: '#888', textAlign: 'center', marginTop: '40px' }}>読み込み中...</p>

  return (
    <div style={styles.section}>
      <div style={styles.sectionTitle}>Claude API 料金設定</div>
      <div style={styles.row}>
        <div style={styles.label}>入力トークン単価（100万トークンあたり）</div>
        <div style={styles.inputRow}>
          <span style={styles.unit}>$</span>
          <input
            type="number"
            min="0"
            step="0.01"
            value={inputPrice}
            onChange={e => setInputPrice(e.target.value)}
            style={styles.input}
          />
        </div>
      </div>
      <div style={styles.rowLast}>
        <div style={styles.label}>出力トークン単価（100万トークンあたり）</div>
        <div style={styles.inputRow}>
          <span style={styles.unit}>$</span>
          <input
            type="number"
            min="0"
            step="0.01"
            value={outputPrice}
            onChange={e => setOutputPrice(e.target.value)}
            style={styles.input}
          />
        </div>
      </div>
      {msg.text && <p style={msg.type === 'ok' ? styles.successMsg : styles.errMsg}>{msg.text}</p>}
      <div style={styles.btnRow}>
        <button style={styles.saveBtn} onClick={handleSave} disabled={saving}>{saving ? '保存中...' : '保存'}</button>
        <button style={styles.cancelBtn} onClick={handleCancel} disabled={saving}>キャンセル</button>
      </div>
    </div>
  )
}
