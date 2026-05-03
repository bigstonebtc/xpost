import { useState } from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { getToken, setToken, api } from './api'
import Dashboard from './components/Dashboard'
import Queue from './components/Queue'
import TweetCreate from './components/TweetCreate'
import History from './components/History'
import News from './components/News'
import NewsSettings from './components/NewsSettings'

const styles = {
  nav: { background: '#1a1a2e', color: '#fff', padding: '12px 16px', display: 'flex', gap: '20px', alignItems: 'center' },
  navTitle: { fontWeight: 'bold', fontSize: '16px', flex: 1 },
  navLink: { color: '#aaa', textDecoration: 'none', fontSize: '14px', padding: '4px 8px', borderRadius: '4px' },
  navLinkActive: { color: '#fff', background: '#16213e' },
  container: { maxWidth: '600px', margin: '0 auto', padding: '16px' },
  loginBox: { maxWidth: '320px', margin: '80px auto', padding: '32px', background: '#fff', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' },
  input: { width: '100%', padding: '10px', marginBottom: '12px', border: '1px solid #ddd', borderRadius: '6px', fontSize: '16px' },
  btn: { width: '100%', padding: '10px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: '6px', fontSize: '16px', cursor: 'pointer' },
}

function Login({ onLogin }) {
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    try {
      const data = await api.login('admin', pw)
      setToken(data.access_token)
      onLogin()
    } catch {
      setErr('パスワードが違います')
    }
  }

  return (
    <div style={styles.loginBox}>
      <h2 style={{ marginBottom: '20px', textAlign: 'center' }}>xpost</h2>
      <form onSubmit={submit}>
        <input style={styles.input} type="password" placeholder="パスワード" value={pw} onChange={e => setPw(e.target.value)} autoFocus />
        {err && <p style={{ color: 'red', marginBottom: '8px', fontSize: '14px' }}>{err}</p>}
        <button style={styles.btn} type="submit">ログイン</button>
      </form>
    </div>
  )
}

// NavLinkのactiveStyle用
const navLinkStyle = ({ isActive }) => ({
  ...styles.navLink,
  ...(isActive ? styles.navLinkActive : {}),
})

export default function App() {
  const [authed, setAuthed] = useState(!!getToken())

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />
  }

  return (
    <BrowserRouter basename="/xpost">
      <nav style={styles.nav}>
        <span style={styles.navTitle}>xpost</span>
        <NavLink to="/dashboard" style={navLinkStyle}>ダッシュボード</NavLink>
        <NavLink to="/queue" style={navLinkStyle}>キュー</NavLink>
        <NavLink to="/create" style={navLinkStyle}>ツイート作成</NavLink>
        <NavLink to="/news" style={navLinkStyle}>ニュース</NavLink>
        <NavLink to="/history" style={navLinkStyle}>履歴</NavLink>
        <NavLink to="/settings" style={navLinkStyle}>設定</NavLink>
      </nav>
      <div style={styles.container}>
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/queue" element={<Queue />} />
          <Route path="/create" element={<TweetCreate />} />
          <Route path="/news" element={<News />} />
          <Route path="/news-settings" element={<Navigate to="/settings" />} />
          <Route path="/settings" element={<NewsSettings />} />
          <Route path="/history" element={<History />} />
          <Route path="*" element={<Navigate to="/queue" />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
