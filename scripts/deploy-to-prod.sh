#!/bin/bash
# xpost 共有プログラムモード — 本番環境デプロイスクリプト
#
# 使い方: sudo ./deploy-to-prod.sh
#
# 前提: ~/xpost（開発者の作業ディレクトリ、git checkout main で最新化済み）の
# 内容を /app/xpost（本番実行用、root管理）へ反映し、docker composeを再起動する。
# すべての本番ユーザー（/home/<user>/xpost/）が新バージョンを使い始める。
#
# 詳細はdocs/multi_user_design.md 15章参照。

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "root権限で実行してください: sudo $0" >&2
  exit 1
fi

SRC_DIR="${XPOST_SRC_DIR:-$HOME/xpost}"
DEST_DIR="${XPOST_DEST_DIR:-/app/xpost}"

if [ ! -d "$SRC_DIR" ]; then
  echo "デプロイ元が見つかりません: $SRC_DIR" >&2
  exit 1
fi

echo "デプロイ元: $SRC_DIR"
echo "デプロイ先: $DEST_DIR"

mkdir -p "$DEST_DIR"

# env.conf.example はテンプレートなので同期してよいが、本番運用者が
# /app/xpost 直下に独自に置いた設定ファイル等は保護する。
# ユーザー個別データ（/home/<user>/xpost/）は /app の外にあるため対象外。
rsync -a --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  "$SRC_DIR"/ "$DEST_DIR"/

cd "$DEST_DIR"
docker compose up -d --build

echo "─────────────────────────────────"
echo "デプロイ完了: $DEST_DIR"
echo "すべての本番ユーザーが新バージョンを使用開始しました"
echo "─────────────────────────────────"
