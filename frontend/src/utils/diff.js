// レビュー付きで予約した投稿の表示用。元のツイートと比べて、現在の本文のうち
// 追加・変更された箇所を求める。削除された箇所は扱わない（元のツイートは details で確認する）。
//
// 文字単位のLCS（最長共通部分列）で「元の本文にもあった文字」を決め、それ以外を追加箇所とする。
// 本文は最大1024文字なので、O(n*m) の表でも十分に軽い。

// 追加箇所に挟まれた、この文字数以下の変更なし部分は追加箇所にまとめる（細切れの青字を防ぐ）
const MERGE_GAP = 2

export function addedSegments(original, current) {
  const a = Array.from(original || '')
  const b = Array.from(current || '')
  const n = a.length
  const m = b.length
  const w = m + 1

  // dp[i*w+j] = a[i:] と b[j:] のLCS長
  const dp = new Uint16Array((n + 1) * w)
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i * w + j] = a[i] === b[j]
        ? dp[(i + 1) * w + j + 1] + 1
        : Math.max(dp[(i + 1) * w + j], dp[i * w + j + 1])
    }
  }

  const added = new Array(m).fill(true)
  let i = 0
  let j = 0
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      added[j] = false
      i++
      j++
    } else if (dp[(i + 1) * w + j] >= dp[i * w + j + 1]) {
      i++
    } else {
      j++
    }
  }

  for (let k = 0; k < m;) {
    if (added[k]) { k++; continue }
    let e = k
    while (e < m && !added[e]) e++
    if (k > 0 && e < m && e - k <= MERGE_GAP) {
      for (let x = k; x < e; x++) added[x] = true
    }
    k = e
  }

  const segments = []
  for (let k = 0; k < m; k++) {
    const last = segments[segments.length - 1]
    if (last && last.added === added[k]) last.text += b[k]
    else segments.push({ text: b[k], added: added[k] })
  }
  return segments
}
