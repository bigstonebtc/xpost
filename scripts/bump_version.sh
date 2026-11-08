#!/bin/bash
# VERSION の番号を上げる（Claude Code が開発時の push 前に使う。デプロイ時には使わない）
#
# 使い方: ./scripts/bump_version.sh [patch|minor|major]   （省略時は patch）
#   patch: 2.1.10 → 2.1.11
#   minor: 2.1.15 → 2.2.0   （下位の桁は0に戻す）
#   major: 2.1.15 → 3.0.0
#
# VERSION を書き換えて新しい番号を表示するだけ。コミット・タグ作成・push は行わない。
set -euo pipefail

cd "$(dirname "$0")/.."
part="${1:-patch}"
current="$(tr -d '[:space:]' < VERSION)"
if ! [[ "$current" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
  echo "VERSION の形式が不正です: $current" >&2
  exit 1
fi
major="${BASH_REMATCH[1]}"; minor="${BASH_REMATCH[2]}"; patch="${BASH_REMATCH[3]}"

case "$part" in
  patch) patch=$((patch + 1)) ;;
  minor) minor=$((minor + 1)); patch=0 ;;
  major) major=$((major + 1)); minor=0; patch=0 ;;
  *) echo "使い方: $0 [patch|minor|major]" >&2; exit 1 ;;
esac

echo "${major}.${minor}.${patch}" > VERSION
echo "${major}.${minor}.${patch}"
