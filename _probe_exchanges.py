"""暫時性診斷腳本:測試各交易所在目前執行環境是否可存取目標標的。

用途是確認 GitHub Actions / Streamlit Cloud 的雲端 IP 是否被交易所地區封鎖。
確認完資料來源後即可刪除。
"""

import ccxt

CANDIDATES = {
    "okx": [
        "BTC/USDT",
        "ETH/USDT",
        "MU/USDT:USDT",
        "QQQ/USDT:USDT",
        "MRVL/USDT:USDT",
        "DRAM/USDT:USDT",
    ],
}


def main() -> None:
    for name, symbols in CANDIDATES.items():
        print(f"=== {name} ===")
        try:
            ex = getattr(ccxt, name)()
            ex.load_markets()
        except Exception as exc:
            print(f"  載入市場失敗:{str(exc)[:160]}\n")
            continue

        for symbol in symbols:
            try:
                bars = ex.fetch_ohlcv(symbol, timeframe="4h", limit=60)
                print(f"  ✓ {symbol}:取得 {len(bars)} 根 K 線,最新收盤 {bars[-1][4]}")
            except Exception as exc:
                print(f"  ✗ {symbol}:{str(exc)[:160]}")
        print()


if __name__ == "__main__":
    main()
