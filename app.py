"""Market Signal Radar — 多空訊號儀表板(Streamlit)。"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
import data_fetcher
import indicators
import signals

CHART_BARS = 100  # K 線圖顯示的最近根數,避免太密集


def make_candlestick_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """畫出蠟燭圖,疊加 EMA 快慢線與布林通道。"""
    chart_df = df.tail(CHART_BARS)

    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=chart_df["timestamp"],
            open=chart_df["open"],
            high=chart_df["high"],
            low=chart_df["low"],
            close=chart_df["close"],
            name=symbol,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["ema_fast"],
            name=f"EMA{config.EMA_FAST}",
            line=dict(width=1),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["ema_slow"],
            name=f"EMA{config.EMA_SLOW}",
            line=dict(width=1),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["bb_upper"],
            name="布林上軌",
            line=dict(width=1, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["bb_lower"],
            name="布林下軌",
            line=dict(width=1, dash="dot"),
        )
    )
    fig.update_layout(
        title=f"{symbol} K線圖({config.TIMEFRAME},近 {CHART_BARS} 根)",
        xaxis_rangeslider_visible=False,
        height=420,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


st.set_page_config(page_title="Market Signal Radar", layout="wide")

st.title("Market Signal Radar")
st.caption(f"資料來源:OKX 公開 API｜時框:{config.TIMEFRAME}｜僅供參考,非投資建議")

if st.button("🔄 重新整理"):
    st.session_state["fetched"] = True

if "fetched" not in st.session_state:
    st.session_state["fetched"] = True  # 首次載入自動抓一次

if st.session_state["fetched"]:
    with st.spinner("抓取資料並計算指標中..."):
        raw_results = data_fetcher.fetch_all(config.SYMBOLS)

        evaluations = {}
        indicator_dfs = {}
        errors = {}
        for symbol, result in raw_results.items():
            if isinstance(result, Exception):
                errors[symbol] = str(result)
                continue
            df = indicators.add_indicators(result)
            evaluations[symbol] = signals.evaluate(df, symbol)
            indicator_dfs[symbol] = df

    if errors:
        for symbol, msg in errors.items():
            st.error(f"{symbol} 抓取失敗:{msg}")

    if evaluations:
        emoji_map = {
            "強烈做多": "🟢🟢",
            "偏多": "🟢",
            "中性": "⚪",
            "偏空": "🔴",
            "強烈做空": "🔴🔴",
        }

        rows = []
        for symbol, ev in evaluations.items():
            ema_trend = (
                "多頭排列"
                if ev["ema_fast"] > ev["ema_slow"]
                else "空頭排列"
                if ev["ema_fast"] < ev["ema_slow"]
                else "持平"
            )
            macd_trend = "MACD > 訊號線" if ev["macd"] > ev["macd_signal"] else "MACD < 訊號線"
            rows.append(
                {
                    "幣種": symbol,
                    "現價": round(ev["price"], 4),
                    "RSI(14)": round(ev["rsi"], 1),
                    "MACD狀態": macd_trend,
                    "均線排列": ema_trend,
                    "訊號": f"{emoji_map[ev['label']]} {ev['label']}",
                    "分數": ev["score"],
                }
            )

        overview_df = pd.DataFrame(rows).set_index("幣種")
        st.dataframe(overview_df, use_container_width=True)

        st.subheader("詳細判斷理由")
        for symbol, ev in evaluations.items():
            with st.expander(f"{symbol} — {emoji_map[ev['label']]} {ev['label']}(分數 {ev['score']})"):
                st.plotly_chart(
                    make_candlestick_chart(indicator_dfs[symbol], symbol),
                    use_container_width=True,
                )
                for reason in ev["reasons"]:
                    st.write(f"- {reason}")
                detail = (
                    f"現價 {ev['price']:.4f} ｜ RSI {ev['rsi']:.1f} ｜ "
                    f"MACD {ev['macd']:.4f} / 訊號線 {ev['macd_signal']:.4f} ｜ "
                    f"EMA{config.EMA_FAST} {ev['ema_fast']:.4f} / EMA{config.EMA_SLOW} {ev['ema_slow']:.4f}"
                )
                if ev["volume_ratio"] is not None:
                    detail += f" ｜ 量能 {ev['volume_ratio']:.2f} 倍均量"
                st.write(detail)
