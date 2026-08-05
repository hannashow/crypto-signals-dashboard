"""計算技術指標:RSI、MACD、EMA、布林通道。"""

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from ta.volatility import BollingerBands

import config


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """在 OHLCV DataFrame 上附加指標欄位,回傳新的 DataFrame。"""
    df = df.copy()

    rsi = RSIIndicator(close=df["close"], window=config.RSI_PERIOD)
    df["rsi"] = rsi.rsi()

    macd = MACD(
        close=df["close"],
        window_fast=config.MACD_FAST,
        window_slow=config.MACD_SLOW,
        window_sign=config.MACD_SIGNAL,
    )
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    df["ema_fast"] = EMAIndicator(close=df["close"], window=config.EMA_FAST).ema_indicator()
    df["ema_slow"] = EMAIndicator(close=df["close"], window=config.EMA_SLOW).ema_indicator()

    bb = BollingerBands(close=df["close"], window=config.BB_PERIOD, window_dev=config.BB_STD)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()

    return df
