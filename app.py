"""Market Signal Radar — 多空訊號儀表板(Streamlit)。"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
import data_fetcher
import indicators
import signals

CHART_BARS = 100  # K 線圖顯示的最近根數,避免太密集

# 配色與 .streamlit/config.toml 的佈景一致,確保圖表與頁面不會互相打架
COLOR_UP = "#16a34a"
COLOR_DOWN = "#dc2626"
COLOR_EMA_FAST = "#2563eb"
COLOR_EMA_SLOW = "#f59e0b"
COLOR_BAND = "#94a3b8"
COLOR_GRID = "#e2e8f0"

# 每個訊號標籤對應的圖示與底色(底色用於總覽表格)
SIGNAL_STYLE = {
    "強烈做多": ("🟢🟢", "#dcfce7"),
    "偏多": ("🟢", "#f0fdf4"),
    "中性": ("⚪", "#f8fafc"),
    "偏空": ("🔴", "#fef2f2"),
    "強烈做空": ("🔴🔴", "#fee2e2"),
}


def make_candlestick_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """畫出蠟燭圖,疊加 EMA 快慢線與布林通道。"""
    chart_df = df.tail(CHART_BARS)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["bb_upper"],
            name="布林上軌",
            line=dict(width=1, dash="dot", color=COLOR_BAND),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["bb_lower"],
            name="布林下軌",
            line=dict(width=1, dash="dot", color=COLOR_BAND),
            # 與上軌之間填色,讓通道範圍一眼可辨
            fill="tonexty",
            fillcolor="rgba(148, 163, 184, 0.10)",
        )
    )
    fig.add_trace(
        go.Candlestick(
            x=chart_df["timestamp"],
            open=chart_df["open"],
            high=chart_df["high"],
            low=chart_df["low"],
            close=chart_df["close"],
            name=symbol,
            increasing_line_color=COLOR_UP,
            increasing_fillcolor=COLOR_UP,
            decreasing_line_color=COLOR_DOWN,
            decreasing_fillcolor=COLOR_DOWN,
            line=dict(width=1),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["ema_fast"],
            name=f"EMA{config.EMA_FAST}",
            line=dict(width=1.6, color=COLOR_EMA_FAST),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["ema_slow"],
            name=f"EMA{config.EMA_SLOW}",
            line=dict(width=1.6, color=COLOR_EMA_SLOW),
        )
    )

    fig.update_layout(
        height=430,
        margin=dict(l=8, r=8, t=30, b=8),
        xaxis_rangeslider_visible=False,
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#334155", size=12),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.0,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLOR_GRID, linecolor=COLOR_GRID)
    fig.update_yaxes(showgrid=True, gridcolor=COLOR_GRID, linecolor=COLOR_GRID)
    return fig


def price_decimals(price: float) -> int:
    """依價格大小決定顯示小數位,避免高價標的補一堆無意義的零。"""
    if price >= 100:
        return 2
    if price >= 1:
        return 3
    return 5


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
        # 指標卡顯示即時價;漲跌幅為相對訊號所依據的已收盤 K 棒
        st.subheader("即時報價")
        items = list(evaluations.items())
        for row_start in range(0, len(items), 3):
            cols = st.columns(3)
            for col, (symbol, ev) in zip(cols, items[row_start:row_start + 3]):
                change = (ev["live_price"] / ev["price"] - 1) * 100
                dp = price_decimals(ev["live_price"])
                emoji, _ = SIGNAL_STYLE[ev["label"]]
                col.metric(
                    label=f"{emoji} {symbol}",
                    value=f"{ev['live_price']:,.{dp}f}",
                    delta=f"{change:+.2f}%",
                )

        # 所有標的取自同一時框,K 棒時間一致,取任一筆標示即可
        candle_time = next(iter(evaluations.values()))["candle_time"]
        st.subheader("訊號總覽")
        st.caption(
            f"訊號依據 {candle_time:%m-%d %H:%M} 起算的已收盤 K 棒(UTC)。"
            f"未收盤的 K 棒價格仍在變動,不納入判斷,因此訊號在該根 K 棒期間維持不變。"
        )
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
            emoji, _ = SIGNAL_STYLE[ev["label"]]
            rows.append(
                {
                    "標的": symbol,
                    "現價": round(ev["price"], price_decimals(ev["price"])),
                    "RSI": round(ev["rsi"], 1),
                    "MACD狀態": macd_trend,
                    "均線排列": ema_trend,
                    "量能": (
                        f"{ev['volume_ratio']:.2f}x"
                        if ev["volume_ratio"] is not None
                        else "—"
                    ),
                    "訊號": f"{emoji} {ev['label']}",
                    "分數": ev["score"],
                }
            )

        overview_df = pd.DataFrame(rows).set_index("標的")

        def shade_signal(value: str) -> str:
            for label, (_, bg) in SIGNAL_STYLE.items():
                if value.endswith(label):
                    return f"background-color: {bg}"
            return ""

        def shade_score(value: int) -> str:
            if value > 0:
                return f"color: {COLOR_UP}; font-weight: 600"
            if value < 0:
                return f"color: {COLOR_DOWN}; font-weight: 600"
            return "color: #64748b"

        styled = (
            overview_df.style
            .map(shade_signal, subset=["訊號"])
            .map(shade_score, subset=["分數"])
        )
        st.dataframe(styled, use_container_width=True)

        st.subheader("詳細判斷理由")
        for symbol, ev in evaluations.items():
            emoji, _ = SIGNAL_STYLE[ev["label"]]
            with st.expander(f"{emoji} {symbol} — {ev['label']}(分數 {ev['score']})"):
                st.plotly_chart(
                    make_candlestick_chart(indicator_dfs[symbol], symbol),
                    use_container_width=True,
                )

                dp = price_decimals(ev["price"])
                cols = st.columns(4)
                cols[0].metric(
                    "收盤價",
                    f"{ev['price']:,.{dp}f}",
                    help="訊號所依據的已收盤 K 棒收盤價,非即時價格。",
                )
                cols[1].metric("RSI", f"{ev['rsi']:.1f}")
                cols[2].metric(
                    f"EMA{config.EMA_FAST} / EMA{config.EMA_SLOW}",
                    f"{ev['ema_fast']:,.{dp}f}",
                    delta=f"{ev['ema_fast'] - ev['ema_slow']:+,.{dp}f}",
                )
                cols[3].metric(
                    "量能",
                    f"{ev['volume_ratio']:.2f}x" if ev["volume_ratio"] is not None else "—",
                    help="相對過去 20 根 K 棒均量。僅加密貨幣標的套用量能確認。",
                )

                st.markdown("**觸發條件**")
                for reason in ev["reasons"]:
                    st.markdown(f"- {reason}")
