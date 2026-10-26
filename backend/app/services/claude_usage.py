import csv
import fcntl
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.logger import get_logger
from app.paths import conf_dir, logs_dir

JST = ZoneInfo("Asia/Tokyo")

PRICING_FILENAME = "pricing.json"
USAGE_CSV_FILENAME = "claude_usage.csv"

# Sonnet 5 の公式レート（2026年9月時点）を初期値とする
DEFAULT_PRICING = {
    "claude_input_tokens_price": 2.00,
    "claude_output_tokens_price": 10.00,
}

_CSV_HEADER = ["timestamp", "operation_type", "input_tokens", "output_tokens", "cost_usd"]


def _pricing_path(user_id: str):
    return conf_dir(user_id) / PRICING_FILENAME


def _usage_csv_path(user_id: str):
    return logs_dir(user_id) / USAGE_CSV_FILENAME


def _calc_cost(input_tokens: int, output_tokens: int, pricing: dict) -> float:
    return (
        (input_tokens / 1_000_000) * pricing["claude_input_tokens_price"]
        + (output_tokens / 1_000_000) * pricing["claude_output_tokens_price"]
    )


def get_pricing_config(user_id: str) -> dict:
    path = _pricing_path(user_id)
    if not path.exists():
        return dict(DEFAULT_PRICING)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "claude_input_tokens_price": float(data.get("claude_input_tokens_price", DEFAULT_PRICING["claude_input_tokens_price"])),
            "claude_output_tokens_price": float(data.get("claude_output_tokens_price", DEFAULT_PRICING["claude_output_tokens_price"])),
        }
    except Exception:
        return dict(DEFAULT_PRICING)


def estimate_cost(user_id: str, input_tokens: int, output_tokens: int) -> float:
    """現在のpricing.json設定でのコスト見積り（USD）を返す。"""
    pricing = get_pricing_config(user_id)
    return round(_calc_cost(input_tokens, output_tokens, pricing), 4)


def update_pricing_config(user_id: str, input_price: float, output_price: float) -> dict:
    path = _pricing_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    pricing = {
        "claude_input_tokens_price": input_price,
        "claude_output_tokens_price": output_price,
    }
    path.write_text(json.dumps(pricing, indent=2) + "\n", encoding="utf-8")
    return pricing


def log_claude_usage(user_id: str, operation_type: str, input_tokens: int, output_tokens: int) -> None:
    """Claude API呼び出し直後に使用量をCSVへ追記する（fcntlで排他制御）。
    統計は補助情報のため、記録に失敗してもAPI呼び出し元の処理は継続させる。"""
    try:
        pricing = get_pricing_config(user_id)
        cost = _calc_cost(input_tokens, output_tokens, pricing)
        path = _usage_csv_path(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                writer = csv.writer(f)
                if is_new:
                    writer.writerow(_CSV_HEADER)
                writer.writerow([
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    operation_type,
                    input_tokens,
                    output_tokens,
                    f"{cost:.6f}",
                ])
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception:
        get_logger(user_id).error("claude_usage.csvへの記録に失敗しました", exc_info=True)


def get_claude_stats(user_id: str) -> dict:
    """本日・当月の合計トークン数とコストを集計する。
    コストは記録時点のcost_usd列ではなく、常に現在のpricing.jsonで再計算する
    （料金変更後は過去分も含めて『現在の設定での見積り』を表示するため）。"""
    now_jst = datetime.now(JST)
    today = now_jst.date()
    pricing = get_pricing_config(user_id)
    path = _usage_csv_path(user_id)

    today_input = today_output = 0
    month_input = month_output = 0

    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
                    input_tokens = int(row["input_tokens"])
                    output_tokens = int(row["output_tokens"])
                except (KeyError, ValueError):
                    continue
                ts_jst = ts.astimezone(JST)

                if ts_jst.year == today.year and ts_jst.month == today.month:
                    month_input += input_tokens
                    month_output += output_tokens
                    if ts_jst.date() == today:
                        today_input += input_tokens
                        today_output += output_tokens

    return {
        "today": {
            "input_tokens": today_input,
            "output_tokens": today_output,
            "cost_usd": round(_calc_cost(today_input, today_output, pricing), 4),
        },
        "this_month": {
            "input_tokens": month_input,
            "output_tokens": month_output,
            "cost_usd": round(_calc_cost(month_input, month_output, pricing), 4),
        },
    }
