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
  rateLimitUsage: () => request('GET', '/rate-limit/usage'),
  features: () => request('GET', '/features/'),
  queue: () => request('GET', '/queue/'),
  generate: () => request('POST', '/tweets/generate'),
  post: (id) => request('POST', `/queue/${id}/post`),
  schedule: (id) => request('POST', `/queue/${id}/schedule`),
  unschedule: (id) => request('POST', `/queue/${id}/unschedule`),
  discard: (id) => request('POST', `/queue/${id}/discard`),
  reschedule: (id) => request('POST', `/queue/${id}/reschedule`),
  searchNews: (tweetId, search_pattern, exclude_urls) =>
    request('POST', `/tweets/${tweetId}/news/search`, { search_pattern, exclude_urls }),
  attachNews: (tweetId, url) => request('POST', `/tweets/${tweetId}/news/attach`, { url }),
  removeNews: (tweetId) => request('DELETE', `/tweets/${tweetId}/news`),
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
  // 画像
  uploadImage: (tweetId, file) => {
    const form = new FormData()
    form.append('file', file)
    form.append('tweet_id', String(tweetId))
    return fetch(`${BASE}/images/upload`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    }).then(async r => {
      if (r.ok) return r.json()
      const text = await r.text()
      let msg = `アップロードエラー (${r.status})`
      try { msg = JSON.parse(text).detail || msg } catch {}
      throw new Error(msg)
    })
  },
  deleteImage: (tweetId) => request('DELETE', `/images/${tweetId}`),
  // 投稿設定
  getPostingSettings: () => request('GET', '/settings/posting/'),
  updatePostingSettings: (daily_schedule_limit) => request('PUT', '/settings/posting/', { daily_schedule_limit }),
  getPostingMode: () => request('GET', '/settings/posting/mode'),
  updatePostingMode: (posting_mode) => request('PUT', '/settings/posting/mode', { posting_mode }),
  updateScheduleHours: (schedule_hours) => request('PUT', '/settings/posting/schedule-hours', { schedule_hours }),
  // Tor
  torStatus: () => request('GET', '/tor/status'),
  torRestart: () => request('POST', '/tor/restart'),
  // APIキー設定
  getApiKeys: () => request('GET', '/settings/apikeys'),
  getApiKeysRaw: () => request('GET', '/settings/apikeys/raw'),
  updateApiKeys: (keys) => request('PUT', '/settings/apikeys', keys),
  restartApp: () => request('POST', '/settings/restart'),
  // プロンプト管理
  listPrompts: () => request('GET', '/prompts/'),
  getPrompt: (filename) => request('GET', `/prompts/${filename}`),
  createPrompt: (body) => request('POST', '/prompts/', body),
  updatePrompt: (filename, body) => request('PUT', `/prompts/${filename}`, body),
  deletePrompt: (filename) => request('DELETE', `/prompts/${filename}`),
  listDocuments: () => request('GET', '/prompts/documents/list'),
  generateWithPrompt: (prompt_file) => request('POST', '/tweets/generate', { prompt_file }),
}
