"""把技術指標組合成多空訊號評分。"""

import pandas as pd

import config


def _label_for_score(score: int) -> str:
    if score >= 3:
        return "強烈做多"
    if score >= 1:
        return "偏多"
    if score == 0:
        return "中性"
    if score >= -2:
        return "偏空"
    return "強烈做空"


def evaluate(df: pd.DataFrame) -> dict:
    """對指標 DataFrame 的最新一根 K 線計算多空分數,回傳分數、標籤與觸發理由。"""
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0
    reasons = []

    # RSI 超賣/超買
    if latest["rsi"] < config.RSI_OVERSOLD:
        score += 1
        reasons.append(f"RSI={latest['rsi']:.1f} 低於 {config.RSI_OVERSOLD}(超賣)")
    elif latest["rsi"] > config.RSI_OVERBOUGHT:
        score -= 1
        reasons.append(f"RSI={latest['rsi']:.1f} 高於 {config.RSI_OVERBOUGHT}(超買)")

    # MACD 黃金/死亡交叉
    golden_cross = prev["macd"] < prev["macd_signal"] and latest["macd"] > latest["macd_signal"]
    death_cross = prev["macd"] > prev["macd_signal"] and latest["macd"] < latest["macd_signal"]
    if golden_cross:
        score += 1
        reasons.append("MACD 黃金交叉(MACD 線由下往上穿越訊號線)")
    elif death_cross:
        score -= 1
        reasons.append("MACD 死亡交叉(MACD 線由上往下穿越訊號線)")

    # EMA 多頭/空頭排列
    if latest["close"] > latest["ema_fast"] > latest["ema_slow"]:
        score += 1
        reasons.append(
            f"價格站上 EMA{config.EMA_FAST} 且 EMA{config.EMA_FAST} > EMA{config.EMA_SLOW}(多頭排列)"
        )
    elif latest["close"] < latest["ema_fast"] < latest["ema_slow"]:
        score -= 1
        reasons.append(
            f"價格跌破 EMA{config.EMA_FAST} 且 EMA{config.EMA_FAST} < EMA{config.EMA_SLOW}(空頭排列)"
        )

    # 布林通道
    if latest["close"] <= latest["bb_lower"]:
        score += 1
        reasons.append("價格觸及/低於布林通道下軌")
    elif latest["close"] >= latest["bb_upper"]:
        score -= 1
        reasons.append("價格觸及/高於布林通道上軌")

    if not reasons:
        reasons.append("目前沒有任何指標觸發訊號條件")

    return {
        "score": score,
        "label": _label_for_score(score),
        "reasons": reasons,
        "price": latest["close"],
        "rsi": latest["rsi"],
        "macd": latest["macd"],
        "macd_signal": latest["macd_signal"],
        "ema_fast": latest["ema_fast"],
        "ema_slow": latest["ema_slow"],
    }
