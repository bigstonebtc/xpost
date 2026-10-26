#!/bin/bash
# xpost 本番環境（/app/xpost）の一発更新スクリプト
#
# 使い方: sudo ./scripts/update_prod.sh
#
# 処理内容:
#   1. 現在のコミットを記録（失敗時のロールバック用）
#   2. git pull で最新化
#   3. docker compose build（変更のあったイメージのみ再ビルドされる）
#   4. docker compose up -d（変更のあったコンテナのみ再作成される）
#   5. ヘルスチェックで正常性を確認
#   6. 失敗したら、記録しておいたコミットに自動で戻し、再ビルド・再起動する
#
# DBスキーマ変更を伴う大きな更新（マイグレーション追加など）には使わないこと。
# そういう変更は docs/vps_migration_runbook.md の手順（並行構築・検証）を使う。

set -uo pipefail

# 本番が追従する開発ブランチ（決め打ち）。
# 誤って別ブランチをpullしないよう、意図的にハードコードしている。
# 開発ブランチが変わったら（例: main にマージして本番をmain追従に切り替える等）
# ここを書き換えること。
BRANCH="claude/addition20260909"

APP_ROOT="${XPOST_APP_ROOT:-/app/xpost}"
PROJECT_NAME="${XPOST_COMPOSE_PROJECT:-xpost_prod}"
HEALTH_URL="${XPOST_HEALTH_URL:-https://localhost/xpost/api/health}"
HEALTH_RETRIES=10
HEALTH_WAIT_SECONDS=3

rollback() {
  local target_commit="$1"
  local project="$2"
  echo "─── ロールバック: $target_commit に戻します ───" >&2
  git reset --hard "$target_commit"
  docker compose -p "$project" build
  docker compose -p "$project" up -d
}

if [ "$(id -u)" -ne 0 ]; then
  echo "root権限で実行してください: sudo $0" >&2
  exit 1
fi

cd "$APP_ROOT" || { echo "APP_ROOTが見つかりません: $APP_ROOT" >&2; exit 1; }

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
  echo "現在チェックアウトされているブランチ ($CURRENT_BRANCH) が" >&2
  echo "スクリプトの想定ブランチ ($BRANCH) と一致しません。誤ったブランチを" >&2
  echo "pullしないよう処理を中断します。意図した変更であれば、このスクリプト" >&2
  echo "冒頭のBRANCH変数を更新してください。" >&2
  exit 1
fi

PREV_COMMIT="$(git rev-parse HEAD)"
echo "現在のコミット（ロールバック用に記録）: $PREV_COMMIT ($BRANCH)"

echo "─── git pull ───"
if ! git pull origin "$BRANCH"; then
  echo "git pull に失敗しました。手動で確認してください（コンテナは変更していません）。" >&2
  exit 1
fi

NEW_COMMIT="$(git rev-parse HEAD)"
if [ "$NEW_COMMIT" = "$PREV_COMMIT" ]; then
  echo "変更はありませんでした（既に最新）。"
  exit 0
fi

echo "─── docker compose build ───"
if ! docker compose -p "$PROJECT_NAME" build; then
  echo "ビルドに失敗しました。コードは更新済みですがコンテナは起動していません。" >&2
  echo "手動で確認するか、ロールバックしてください: git reset --hard $PREV_COMMIT" >&2
  exit 1
fi

echo "─── docker compose up -d ───"
if ! docker compose -p "$PROJECT_NAME" up -d; then
  echo "起動に失敗しました。ロールバックします。" >&2
  rollback "$PREV_COMMIT" "$PROJECT_NAME"
  exit 1
fi

echo "─── ヘルスチェック ───"
ok=false
for i in $(seq 1 "$HEALTH_RETRIES"); do
  sleep "$HEALTH_WAIT_SECONDS"
  response="$(curl -sk "$HEALTH_URL" 2>/dev/null || true)"
  if echo "$response" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
    ok=true
    break
  fi
  echo "  試行 $i/$HEALTH_RETRIES: まだ正常応答なし ($response)"
done

if [ "$ok" != "true" ]; then
  echo "ヘルスチェックに失敗しました。$PREV_COMMIT へ自動ロールバックします。" >&2
  rollback "$PREV_COMMIT" "$PROJECT_NAME"
  echo "ロールバック後の再ヘルスチェック:" >&2
  sleep "$HEALTH_WAIT_SECONDS"
  curl -sk "$HEALTH_URL" || true
  echo "" >&2
  echo "更新は失敗し、$PREV_COMMIT にロールバックしました。原因を調査してください。" >&2
  exit 1
fi

echo ""
echo "─────────────────────────────────"
echo "更新完了: $PREV_COMMIT → $NEW_COMMIT"
echo "─────────────────────────────────"
docker compose -p "$PROJECT_NAME" ps
