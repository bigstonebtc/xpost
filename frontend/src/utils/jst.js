// このアプリの日時はすべてJST（日本標準時、UTC+9固定・夏時間なし）で運用する。
// 閲覧者のブラウザのタイムゾーン設定（海外にいる場合など）に影響されず、
// 常にJSTの値を表示するためのヘルパー。
//
// 仕組み: 実際のUTCエポック時刻に9時間分を加算した Date を作り、
// その UTC系ゲッター（getUTCFullYear等）を読むことで、
// 「常にJSTのwall-clock値」をブラウザのタイムゾーンに関係なく取得する。

export function toJstDate(iso) {
  const utc = new Date(iso)
  return new Date(utc.getTime() + 9 * 60 * 60 * 1000)
}

export function formatJst(iso, { withSeconds = false } = {}) {
  if (!iso) return ''
  const d = toJstDate(iso)
  const y = d.getUTCFullYear()
  const mo = d.getUTCMonth() + 1
  const day = d.getUTCDate()
  const hh = String(d.getUTCHours()).padStart(2, '0')
  const mm = String(d.getUTCMinutes()).padStart(2, '0')
  let result = `${y}-${mo}-${day} ${hh}:${mm}`
  if (withSeconds) {
    result += `:${String(d.getUTCSeconds()).padStart(2, '0')}`
  }
  return `${result} JST`
}

export function formatJstShort(iso) {
  if (!iso) return ''
  const d = toJstDate(iso)
  const mo = d.getUTCMonth() + 1
  const day = d.getUTCDate()
  const hh = String(d.getUTCHours()).padStart(2, '0')
  const mm = String(d.getUTCMinutes()).padStart(2, '0')
  return `${mo}/${day} ${hh}:${mm}`
}
