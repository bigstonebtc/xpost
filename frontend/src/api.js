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
  schedule: (id) => request('POST', `/queue/${id}/schedule`),
  discard: (id) => request('POST', `/queue/${id}/discard`),
  edit: (id, content) => request('PUT', `/queue/${id}`, { content }),
  clearQueue: () => request('DELETE', '/queue/'),
  history: (filter = 'today') => request('GET', `/history/?filter=${filter}`),
  // ニュース
  newsList: () => request('GET', '/news/'),
  newsFetch: () => request('POST', '/news/fetch'),
  newsAddToQueue: (id) => request('POST', `/news/${id}/add-to-queue`),
  newsSkip: (id) => request('POST', `/news/${id}/skip`),
  newsRegenerate: (id) => request('POST', `/news/${id}/regenerate`),
  newsDebug: () => request('GET', '/news/debug'),
  newsClearAiSkipped: () => request('POST', '/news/clear-ai-skipped'),
  // ニュース設定
  newsSettings: () => request('GET', '/settings/news/'),
  newsAddSource: (name, url, category) => request('POST', '/settings/news/sources', { name, url, category }),
  newsUpdateSource: (id, is_enabled, url, name) => request('PUT', `/settings/news/sources/${id}`, { is_enabled, url, name }),
  newsDeleteSource: (id) => request('DELETE', `/settings/news/sources/${id}`),
  newsUpdateSchedule: (slots) => request('PUT', '/settings/news/schedule', { slots }),
  newsUpdateGeneral: (fetch_limit_per_run, relevance_prompt, schedule_mode, news_prompt_file) =>
    request('PUT', '/settings/news/general', { fetch_limit_per_run, relevance_prompt, schedule_mode, news_prompt_file }),
  // プロンプト管理
  listPrompts: () => request('GET', '/prompts/'),
  getPrompt: (filename) => request('GET', `/prompts/${filename}`),
  createPrompt: (body) => request('POST', '/prompts/', body),
  updatePrompt: (filename, body) => request('PUT', `/prompts/${filename}`, body),
  deletePrompt: (filename) => request('DELETE', `/prompts/${filename}`),
  listDocuments: () => request('GET', '/prompts/documents/list'),
  generateWithPrompt: (prompt_file) => request('POST', '/tweets/generate', { prompt_file }),
}
