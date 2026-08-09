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


def evaluate(df: pd.DataFrame, symbol: str | None = None) -> dict:
    """依最後一根「已收盤」K 棒計算多空分數,回傳分數、標籤與觸發理由。

    傳入 symbol 且該標的列在 config.VOLUME_CONFIRM_SYMBOLS 時,
    會額外用量能確認強化或削弱價格訊號。

    刻意不使用最新一根 K 棒(df.iloc[-1]),因為它尚未收盤 ——
    其「收盤價」其實是即時價格,會隨每一筆成交跳動。價格落在均線附近時,
    分數會在同一根 K 棒內反覆翻轉,導致通知內容與稍後查看儀表板時不一致。
    改用已收盤 K 棒後,訊號在該根 K 棒期間保持穩定,也與量能規則的基準一致。
    """
    latest = df.iloc[-2]   # 最後一根已收盤 K 棒
    prev = df.iloc[-3]     # 再前一根,供 MACD 判斷是否發生穿越

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

    # 量能確認:量能沒有方向性,所以不獨立給分,而是調整既有價格訊號的強度。
    # 與價格規則同樣取最後一根已收盤 K 棒 —— 未收盤那根的成交量只累積了一部分,
    # 拿它跟完整 K 棒的均量相比會系統性地誤判為縮量。
    volume_ratio = None
    if symbol in config.VOLUME_CONFIRM_SYMBOLS and score != 0:
        ratio = latest["volume_ratio"]
        if pd.notna(ratio):
            volume_ratio = float(ratio)
            direction = 1 if score > 0 else -1
            if volume_ratio >= config.VOLUME_SURGE_RATIO:
                score += direction
                reasons.append(
                    f"成交量為均量的 {volume_ratio:.2f} 倍(放量),量價配合,訊號加強"
                )
            elif volume_ratio <= config.VOLUME_DRY_RATIO:
                score -= direction
                reasons.append(
                    f"成交量僅均量的 {volume_ratio:.2f} 倍(縮量),推力不足,訊號減弱"
                )

    if not reasons:
        reasons.append("目前沒有任何指標觸發訊號條件")

    return {
        "score": score,
        "label": _label_for_score(score),
        "reasons": reasons,
        # price 為訊號所依據的已收盤 K 棒收盤價;live_price 為當前形成中 K 棒的
        # 即時價格。兩者會有落差,顯示時需清楚區分以免誤解訊號的時間基準。
        "price": latest["close"],
        "live_price": df["close"].iloc[-1],
        "candle_time": latest["timestamp"],
        "rsi": latest["rsi"],
        "macd": latest["macd"],
        "macd_signal": latest["macd_signal"],
        "ema_fast": latest["ema_fast"],
        "ema_slow": latest["ema_slow"],
        "volume_ratio": volume_ratio,
    }
