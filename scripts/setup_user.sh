#!/bin/bash
# xpost 共有プログラムモード — ユーザー初期化スクリプト
#
# 使い方: sudo ./setup_user.sh <username> <password>
#
# 処理内容（詳細はdocs/multi_user_design.md 14章参照）:
#   1. Linuxユーザー作成（既存ならスキップ）
#   2. /home/<user>/xpost/{conf,prompts,documents,logs,db,images} を作成
#   3. env.conf を env.conf.example からコピー（既存なら上書きしない）
#   4. news_search.prompt をテンプレートからコピー（既存なら上書きしない）
#   5. ADMIN_PASSWORD_HASH / SECRET_KEY を自動生成・追記（既存フィールドは上書きしない）
#   6. ファイル権限を設定
#   7. 初期パスワードを表示
#
# 実行後は backend の再起動が必要（新規ユーザーをconfigキャッシュに反映するため）:
#   docker compose restart backend

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "root権限で実行してください: sudo $0 <username> <password>" >&2
  exit 1
fi

if [ $# -ne 2 ]; then
  echo "使い方: $0 <username> <password>" >&2
  exit 1
fi

USERNAME="$1"
PASSWORD="$2"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_EXAMPLE="$APP_ROOT/env.conf.example"
NEWS_SEARCH_PROMPT_TEMPLATE="$SCRIPT_DIR/templates/news_search.prompt"

if [ ! -f "$ENV_EXAMPLE" ]; then
  echo "テンプレートが見つかりません: $ENV_EXAMPLE" >&2
  exit 1
fi

# 1. Linuxユーザー作成（既存ならスキップ）
if id -u "$USERNAME" >/dev/null 2>&1; then
  echo "Linuxユーザー $USERNAME は既に存在します（作成をスキップ）"
else
  useradd -m "$USERNAME"
  echo "Linuxユーザー $USERNAME を作成しました"
fi

HOME_DIR="$(getent passwd "$USERNAME" | cut -d: -f6)"
XPOST_HOME="$HOME_DIR/xpost"

# 2. ディレクトリ構造生成（既存はスキップ）
mkdir -p "$XPOST_HOME"/conf "$XPOST_HOME"/prompts "$XPOST_HOME"/documents "$XPOST_HOME"/logs "$XPOST_HOME"/db "$XPOST_HOME"/images

# 3. env.conf 処理
ENV_CONF="$XPOST_HOME/conf/env.conf"
if [ -f "$ENV_CONF" ]; then
  echo "env.conf は既に存在します（上書きしません）: $ENV_CONF"
else
  cp "$ENV_EXAMPLE" "$ENV_CONF"
  echo "env.conf をテンプレートから作成しました: $ENV_CONF"
fi

# 4. news_search.prompt 処理（既存なら上書きしない）
NEWS_SEARCH_PROMPT="$XPOST_HOME/prompts/news_search.prompt"
if [ -f "$NEWS_SEARCH_PROMPT" ]; then
  echo "news_search.prompt は既に存在します（上書きしません）: $NEWS_SEARCH_PROMPT"
elif [ -f "$NEWS_SEARCH_PROMPT_TEMPLATE" ]; then
  cp "$NEWS_SEARCH_PROMPT_TEMPLATE" "$NEWS_SEARCH_PROMPT"
  echo "news_search.prompt をテンプレートから作成しました: $NEWS_SEARCH_PROMPT"
else
  echo "news_search.prompt のテンプレートが見つかりません（スキップ、コード側のフォールバックが使われます）: $NEWS_SEARCH_PROMPT_TEMPLATE"
fi

# 5. 認証キーの自動生成・追記（冪等）
python3 "$SCRIPT_DIR/gen_user_secrets.py" "$ENV_CONF" "$PASSWORD"

# 6. ファイル権限設定
chown -R "$USERNAME:$USERNAME" "$XPOST_HOME"
chmod 700 "$XPOST_HOME/conf"
chmod 600 "$ENV_CONF"

# 7. 初期パスワード表示
echo "─────────────────────────────────"
echo "User created: $USERNAME"
echo "Initial password: $PASSWORD"
echo "─────────────────────────────────"
echo ""
echo "新規ユーザーを認識させるには backend の再起動が必要です:"
echo "  docker compose restart backend"
