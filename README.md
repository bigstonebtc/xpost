# xpost

X account management web application. 複数ユーザーで利用できる共有プログラムモードに対応。

## Tech Stack

- Backend: Python + FastAPI
- Frontend: React
- Database: SQLite（ユーザーごとに独立したファイル）
- Container: Docker + Docker Compose
- Proxy: Nginx

## アーキテクチャ

プログラム本体（backend/frontend/nginx/tor）は単一のDocker Composeスタックとして
全ユーザーで共有する。ユーザーごとのデータ（設定・APIキー・DB・プロンプト・資料・ログ）
は `/home/<user>/xpost/` 以下に完全に隔離される。詳細は `docs/multi_user_design.md` を参照。

## Setup（新規ユーザー追加）

```bash
sudo ./scripts/setup_user.sh <username> <password>
sudo docker compose restart backend   # 新規ユーザーを認識させるため再起動が必要
```

初回のみ `/home/<user>/xpost/conf/env.conf`（`env.conf.example` からコピーされる）に
X APIキー・Anthropic APIキーを設定してください。

## 開発環境の起動

```bash
docker compose up -d --build
```

## Environment Variables

各ユーザーの `/home/<user>/xpost/conf/env.conf` に設定する。テンプレートは
`env.conf.example` を参照。
