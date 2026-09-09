#!/usr/bin/env python3
"""setup_user.sh から呼び出す。env.conf に ADMIN_PASSWORD_HASH / SECRET_KEY を
冪等に追記する（既に存在する場合は何もしない＝既存ユーザーの設定を壊さない）。

使い方: gen_user_secrets.py <env.conf のパス> <平文パスワード>
"""
import sys
import uuid
from pathlib import Path

try:
    import bcrypt
except ImportError:
    print("bcrypt がインストールされていません: pip install bcrypt", file=sys.stderr)
    sys.exit(1)


def read_existing_keys(path: Path) -> set[str]:
    keys = set()
    if not path.exists():
        return keys
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, _ = line.partition("=")
        keys.add(key.strip())
    return keys


def main() -> int:
    if len(sys.argv) != 3:
        print(f"使い方: {sys.argv[0]} <env.confのパス> <平文パスワード>", file=sys.stderr)
        return 1

    env_path = Path(sys.argv[1])
    password = sys.argv[2]

    if not env_path.exists():
        print(f"env.confが見つかりません: {env_path}", file=sys.stderr)
        return 1

    existing = read_existing_keys(env_path)
    to_append = []

    # bcrypt: ソルト長12（bcrypt.gensalt()のデフォルト）
    if "ADMIN_PASSWORD_HASH" not in existing:
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
        to_append.append(f"ADMIN_PASSWORD_HASH={password_hash}")
    else:
        print("ADMIN_PASSWORD_HASH は既に存在します（スキップ）")

    if "SECRET_KEY" not in existing:
        to_append.append(f"SECRET_KEY={uuid.uuid4()}")
    else:
        print("SECRET_KEY は既に存在します（スキップ）")

    if to_append:
        with env_path.open("a", encoding="utf-8") as f:
            if env_path.stat().st_size > 0:
                f.write("\n")
            f.write("\n".join(to_append) + "\n")
        print(f"{len(to_append)}件のフィールドを追記しました: {env_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
