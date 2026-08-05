"""從 OKX 公開 API 抓取 OHLCV K 線資料。

直接呼叫 OKX REST API 而不透過 ccxt:ccxt 在抓資料前會先載入交易所的
全部市場定義(OKX 有四千多個),記憶體開銷在 Streamlit Cloud 的免費方案
容易超限。直接打單一端點輕量許多,也省去一次額外的網路往返。
"""

import pandas as pd
import requests

import config

CANDLES_ENDPOINT = "https://www.okx.com/api/v5/market/candles"


def to_inst_id(symbol: str) -> str:
    """把 ccxt 慣例的 symbol 轉成 OKX 的 instId。

    現貨   "BTC/USDT"      -> "BTC-USDT"
    永續   "MU/USDT:USDT"  -> "MU-USDT-SWAP"
    """
    pair, _, settle = symbol.partition(":")
    base, _, quote = pair.partition("/")
    if settle:
        return f"{base}-{quote}-SWAP"
    return f"{base}-{quote}"


def to_bar(timeframe: str) -> str:
    """把時框轉成 OKX 的 bar 參數(分鐘用小寫 m,小時以上用大寫)。"""
    unit = timeframe[-1]
    return timeframe if unit == "m" else timeframe[:-1] + unit.upper()


def fetch_ohlcv(symbol: str) -> pd.DataFrame:
    """抓取單一標的的 OHLCV 資料,回傳 DataFrame。失敗時拋出例外由呼叫端處理。"""
    response = requests.get(
        CANDLES_ENDPOINT,
        params={
            "instId": to_inst_id(symbol),
            "bar": to_bar(config.TIMEFRAME),
            "limit": config.OHLCV_LIMIT,
        },
        timeout=15,
    )
    if not response.ok:
        raise RuntimeError(f"OKX API 回應 {response.status_code}:{response.text[:200]}")

    payload = response.json()
    if payload.get("code") != "0":
        raise RuntimeError(f"OKX API 錯誤:{payload.get('msg') or payload}")

    rows = payload.get("data") or []
    if not rows:
        raise RuntimeError(f"OKX 沒有回傳 {symbol} 的 K 線資料")

    # OKX 回傳順序為新到舊,且每列前六欄為 [時間, 開, 高, 低, 收, 量]
    df = pd.DataFrame(
        [row[:6] for row in reversed(rows)],
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype("int64"), unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


def fetch_all(symbols: list[str]) -> dict[str, pd.DataFrame | Exception]:
    """依序抓取多個標的,單一標的失敗不影響其他,回傳 {symbol: DataFrame 或 Exception}。"""
    results: dict[str, pd.DataFrame | Exception] = {}
    for symbol in symbols:
        try:
            results[symbol] = fetch_ohlcv(symbol)
        except Exception as exc:
            results[symbol] = exc
    return results
