"""計算技術指標:RSI、MACD、EMA、布林通道、量能與 Chandelier Exit。"""

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from ta.volatility import AverageTrueRange, BollingerBands

import config


def add_chandelier_exit(df: pd.DataFrame, timeframe: str | None = None) -> pd.DataFrame:
    """附加 Chandelier Exit 的停損線與多空狀態。

    以 ATR 為緩衝的移動停損(Chuck LeBeau 提出):
        多方停損 = 近 N 根最高 − ATR(N) × 倍數
        空方停損 = 近 N 根最低 + ATR(N) × 倍數

    關鍵在停損只往有利方向移動:持多時停損線只抬不降,價格回檔但未創新高
    則原地不動。收盤價跌破多方停損才翻空,反之翻多 —— ATR 緩衝使小幅
    震盪不會觸發翻轉,雜訊比單純的均線穿越少。
    """
    df = df.copy()
    n = config.ce_period(timeframe or config.TIMEFRAME)

    atr = AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=n
    ).average_true_range() * config.CE_MULTIPLIER

    # everget 版本預設以收盤價取極值,較不受長影線影響
    source = df["close"] if config.CE_USE_CLOSE else None
    highest = (source if source is not None else df["high"]).rolling(n).max()
    lowest = (source if source is not None else df["low"]).rolling(n).min()

    raw_long = highest - atr
    raw_short = lowest + atr

    close = df["close"].to_numpy()
    rl = raw_long.to_numpy()
    rs = raw_short.to_numpy()

    long_stop = np.full(len(df), np.nan)
    short_stop = np.full(len(df), np.nan)
    direction = np.ones(len(df), dtype=int)

    for i in range(len(df)):
        if np.isnan(rl[i]):
            continue
        prev_long = long_stop[i - 1] if i > 0 and not np.isnan(long_stop[i - 1]) else rl[i]
        prev_short = short_stop[i - 1] if i > 0 and not np.isnan(short_stop[i - 1]) else rs[i]

        # 前一根收在停損之上表示多方仍成立,停損只能往上抬,不可下移
        long_stop[i] = max(rl[i], prev_long) if close[i - 1] > prev_long and i > 0 else rl[i]
        # 空方對稱:前一根收在停損之下,停損只能往下降
        short_stop[i] = min(rs[i], prev_short) if close[i - 1] < prev_short and i > 0 else rs[i]

        prev_dir = direction[i - 1] if i > 0 else 1
        if close[i] > prev_short:
            direction[i] = 1
        elif close[i] < prev_long:
            direction[i] = -1
        else:
            direction[i] = prev_dir

    df["ce_long_stop"] = long_stop
    df["ce_short_stop"] = short_stop
    df["ce_direction"] = direction
    # 目前生效的停損:做多時看多方停損,做空時看空方停損
    df["ce_stop"] = np.where(direction == 1, long_stop, short_stop)
    return df


def add_indicators(df: pd.DataFrame, timeframe: str | None = None) -> pd.DataFrame:
    """在 OHLCV DataFrame 上附加指標欄位,回傳新的 DataFrame。

    timeframe 影響 Chandelier Exit 的期數(隨時框縮放),省略時採用
    config.TIMEFRAME。其餘指標的參數不隨時框改變。
    """
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

    # 均量與量能倍數。rolling 只涵蓋該列與之前的 K 棒,
    # 因此在最後一根已收盤 K 棒上取值時,基準不會混入尚未收盤的那根。
    df["volume_ma"] = df["volume"].rolling(window=config.VOLUME_MA_PERIOD).mean()
    df["volume_ratio"] = df["volume"] / df["volume_ma"].replace(0, pd.NA)

    df = add_chandelier_exit(df, timeframe)

    return df
