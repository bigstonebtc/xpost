const BASE = '/xpost/api'

let token = localStorage.getItem('token') || ''

export function setToken(t) {
  token = t
  localStorage.setItem('token', t)
}

export function getToken() {
  return token
}

async function request(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    return
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'エラーが発生しました')
  }
  return res.json()
}

export const api = {
  login: (username, password) => {
    const form = new URLSearchParams({ username, password })
    return fetch(`${BASE}/auth/login`, { method: 'POST', body: form })
      .then(r => r.ok ? r.json() : Promise.reject('認証失敗'))
  },
  stats: () => request('GET', '/history/stats'),
  queue: () => request('GET', '/queue/'),
  generate: () => request('POST', '/tweets/generate'),
  post: (id) => request('POST', `/queue/${id}/post`),
  discard: (id) => request('POST', `/queue/${id}/discard`),
  edit: (id, content) => request('PUT', `/queue/${id}`, { content }),
  clearQueue: () => request('DELETE', '/queue/'),
  history: () => request('GET', '/history/'),
  // ニュース
  newsList: () => request('GET', '/news/'),
  newsFetch: () => request('POST', '/news/fetch'),
  newsAddToQueue: (id) => request('POST', `/news/${id}/add-to-queue`),
  newsSkip: (id) => request('POST', `/news/${id}/skip`),
  newsRegenerate: (id) => request('POST', `/news/${id}/regenerate`),
  // ニュース設定
  newsSettings: () => request('GET', '/settings/news/'),
  newsUpdateSource: (id, is_enabled) => request('PUT', `/settings/news/sources/${id}`, { is_enabled }),
  newsUpdateSchedule: (slots) => request('PUT', '/settings/news/schedule', { slots }),
  newsUpdateGeneral: (fetch_limit_per_run, relevance_prompt) =>
    request('PUT', '/settings/news/general', { fetch_limit_per_run, relevance_prompt }),
}
