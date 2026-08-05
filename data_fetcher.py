"""從 Kraken 公開 API 抓取 OHLCV K 線資料。"""

import ccxt
import pandas as pd

import config

_exchange = ccxt.kraken()


def fetch_ohlcv(symbol: str) -> pd.DataFrame:
    """抓取單一幣種的 OHLCV 資料,回傳 DataFrame。失敗時拋出例外由呼叫端處理。"""
    raw = _exchange.fetch_ohlcv(
        symbol, timeframe=config.TIMEFRAME, limit=config.OHLCV_LIMIT
    )
    df = pd.DataFrame(
        raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def fetch_all(symbols: list[str]) -> dict[str, pd.DataFrame | Exception]:
    """依序抓取多個幣種,單一幣種失敗不影響其他幣種,回傳 {symbol: DataFrame 或 Exception}。"""
    results: dict[str, pd.DataFrame | Exception] = {}
    for symbol in symbols:
        try:
            results[symbol] = fetch_ohlcv(symbol)
        except Exception as exc:
            results[symbol] = exc
    return results
