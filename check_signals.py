"""定時檢查訊號並在有變化時發送 LINE 通知(供 GitHub Actions 排程執行)。

因為 4 小時 K 線的訊號在同一根 K 棒內不會變,而排程是每小時執行,
所以用 .alert_state.json 記住上次已通知的訊號,只在訊號改變時才推播,
避免重複通知並節省 LINE 每月免費額度。
"""

import json
import os
from pathlib import Path

import config
import data_fetcher
import indicators
import levels
import notifier
import signals

STATE_FILE = Path(".alert_state.json")


def load_state() -> dict[str, str]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict[str, str]) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def build_message(alerts: list[tuple[str, dict]]) -> str:
    lines = [f"📊 Market Signal Radar({config.TIMEFRAME})", ""]
    for symbol, ev in alerts:
        arrow = "🟢" if ev["score"] > 0 else "🔴"
        lines.append(f"{arrow} {symbol} — {ev['label']}(分數 {ev['score']})")
        lines.append(f"　收盤 {ev['price']:.4f}｜RSI {ev['rsi']:.1f}")
        for reason in ev["reasons"]:
            lines.append(f"　· {reason}")
        lines.append("")
    # 標明訊號基準,避免收到通知後看到即時價不同而困惑
    candle_time = alerts[0][1]["candle_time"]
    lines.append(f"依據 {candle_time:%m-%d %H:%M} 收盤 K 棒(台灣時間)")
    lines.append("僅供參考,非投資建議")
    return "\n".join(lines)


def main() -> None:
    state = load_state()
    new_state: dict[str, str] = {}
    alerts: list[tuple[str, dict]] = []

    results = data_fetcher.fetch_all(config.SYMBOLS)
    for symbol, result in results.items():
        if isinstance(result, Exception):
            print(f"{symbol} 抓取失敗:{result}")
            # 抓取失敗時保留舊狀態,避免下次誤判為「訊號改變」
            if symbol in state:
                new_state[symbol] = state[symbol]
            continue

        df = indicators.add_indicators(result)
        zones = levels.fetch_zones(symbol, df["close"].iloc[-2])
        ev = signals.evaluate(df, symbol, zones)
        print(f"{symbol} {ev['label']}(分數 {ev['score']})")

        if abs(ev["score"]) >= config.ALERT_MIN_SCORE:
            new_state[symbol] = ev["label"]
            if state.get(symbol) != ev["label"]:
                alerts.append((symbol, ev))
        # 未達門檻的幣種不寫入 new_state,等於清除記錄,
        # 之後若再次觸發同樣訊號仍會通知

    if not alerts:
        save_state(new_state)
        print("沒有新的訊號變化,不發送通知")
        return

    message = build_message(alerts)
    print("發送通知:")
    print(message)

    if os.environ.get("DRY_RUN") == "1":
        print("(DRY_RUN 模式,略過實際發送,不寫入狀態)")
        return

    # 必須先送出成功才寫入狀態。若順序顛倒,發送失敗時(LINE 額度用罄、
    # 憑證過期、網路中斷)訊號已被記為「已通知」,下次執行會因為狀態沒變
    # 而跳過,該則通知就永遠遺失了。
    notifier.send_line_message(message)
    save_state(new_state)
    print("LINE 通知已發送")


if __name__ == "__main__":
    main()
