"""Market Signal Radar — 多空訊號儀表板(Streamlit)。"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import config
import data_fetcher
import formatting
import indicators
import levels
import signals

CHART_BARS = 100  # K 線圖顯示的最近根數,避免太密集

# 配色與 .streamlit/config.toml 的佈景一致,確保圖表與頁面不會互相打架
COLOR_UP = "#16a34a"
COLOR_DOWN = "#dc2626"
COLOR_EMA_FAST = "#2563eb"
COLOR_EMA_SLOW = "#f59e0b"
COLOR_BAND = "#94a3b8"
COLOR_GRID = "#e2e8f0"

# Squeeze Momentum 的四色柱:深色為動能增強、淺色為動能減弱
COLOR_SQZ_UP_STRONG = "#16a34a"
COLOR_SQZ_UP_WEAK = "#86efac"
COLOR_SQZ_DOWN_STRONG = "#dc2626"
COLOR_SQZ_DOWN_WEAK = "#fca5a5"
# 零軸上的擠壓狀態點
COLOR_SQZ_ON = "#0f172a"
COLOR_SQZ_OFF = "#94a3b8"
COLOR_SQZ_NONE = "#2563eb"

# 每個訊號標籤對應的圖示與底色(底色用於總覽表格)
SIGNAL_STYLE = {
    "強烈做多": ("🟢🟢", "#dcfce7"),
    "偏多": ("🟢", "#f0fdf4"),
    "中性": ("⚪", "#f8fafc"),
    "偏空": ("🔴", "#fef2f2"),
    "強烈做空": ("🔴🔴", "#fee2e2"),
}


def make_candlestick_chart(
    df: pd.DataFrame, symbol: str, zones: list | None = None
) -> go.Figure:
    """畫出蠟燭圖(疊加 EMA、布林通道、CE 停損與壓力支撐區),
    下方副圖為 Squeeze Momentum 動能柱與擠壓狀態。"""
    chart_df = df.tail(CHART_BARS)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.72, 0.28],
    )

    # 壓力支撐區畫成整幅橫帶,先畫才會落在 K 棒下層不擋住價格。
    # 只畫上下最近各一個:離現價過遠的區間短期內碰不到,畫出來只是干擾。
    if zones:
        price = float(df["close"].iloc[-2])
        support, resistance = levels.nearest_pair(zones, price)
        for zone in [z for z in (support, resistance) if z is not None]:
            is_support = zone.center <= price
            fig.add_hrect(
                y0=zone.low,
                y1=zone.high,
                fillcolor=COLOR_UP if is_support else COLOR_DOWN,
                opacity=0.10,
                line_width=0,
                layer="below",
                annotation_text=f"{'支撐' if is_support else '壓力'}×{zone.touches}",
                annotation_position="top left",
                annotation_font=dict(
                    size=10, color=COLOR_UP if is_support else COLOR_DOWN
                ),
                row=1, col=1,
            )
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["bb_upper"],
            name="布林上軌",
            line=dict(width=1, dash="dot", color=COLOR_BAND),
        ),
        row=1, col=1,
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
        ),
        row=1, col=1,
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
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["ema_fast"],
            name=f"EMA{config.EMA_FAST}",
            line=dict(width=1.6, color=COLOR_EMA_FAST),
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=chart_df["ema_slow"],
            name=f"EMA{config.EMA_SLOW}",
            line=dict(width=1.6, color=COLOR_EMA_SLOW),
        ),
        row=1, col=1,
    )

    # Chandelier Exit 停損線。多空狀態切換時線會跳到另一側,
    # 因此依狀態拆成兩條繪製,避免跨越時被連成一條斜線。
    ce_long = chart_df["ce_stop"].where(chart_df["ce_direction"] == 1)
    ce_short = chart_df["ce_stop"].where(chart_df["ce_direction"] == -1)
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=ce_long,
            name="CE 停損(多)",
            line=dict(width=2, color=COLOR_UP),
            connectgaps=False,
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=ce_short,
            name="CE 停損(空)",
            line=dict(width=2, color=COLOR_DOWN),
            connectgaps=False,
        ),
        row=1, col=1,
    )

    # 多空翻轉點標示,對應 TradingView 上的 Buy / Sell 標籤
    flips = chart_df[chart_df["ce_direction"].diff() != 0].iloc[1:]
    for _, row in flips.iterrows():
        is_buy = row["ce_direction"] == 1
        fig.add_annotation(
            x=row["timestamp"],
            y=row["low"] if is_buy else row["high"],
            text="Buy" if is_buy else "Sell",
            showarrow=True,
            arrowhead=2,
            arrowsize=0.8,
            ay=24 if is_buy else -24,
            ax=0,
            bgcolor=COLOR_UP if is_buy else COLOR_DOWN,
            font=dict(color="white", size=10),
            bordercolor=COLOR_UP if is_buy else COLOR_DOWN,
            row=1, col=1,
        )

    # ── 副圖:Squeeze Momentum ──
    mom = chart_df["sqz_momentum"]
    prev_mom = mom.shift(1)
    # 四色柱:零軸上下決定方向,與前一根比較決定強弱。
    # 深色為動能增強、淺色為動能減弱 —— 淺色是動能轉折的預警,
    # 價格尚未反轉但推力已在消退。
    bar_colors = np.where(
        mom > 0,
        np.where(mom > prev_mom, COLOR_SQZ_UP_STRONG, COLOR_SQZ_UP_WEAK),
        np.where(mom < prev_mom, COLOR_SQZ_DOWN_STRONG, COLOR_SQZ_DOWN_WEAK),
    )
    fig.add_trace(
        go.Bar(
            x=chart_df["timestamp"],
            y=mom,
            name="Squeeze 動能",
            marker_color=bar_colors,
            showlegend=False,
        ),
        row=2, col=1,
    )

    # 零軸上的擠壓狀態點
    state_color = {
        "擠壓中": COLOR_SQZ_ON,
        "已釋放": COLOR_SQZ_OFF,
        "過渡": COLOR_SQZ_NONE,
    }
    fig.add_trace(
        go.Scatter(
            x=chart_df["timestamp"],
            y=np.zeros(len(chart_df)),
            mode="markers",
            name="擠壓狀態",
            marker=dict(
                size=4,
                color=[state_color[s] for s in chart_df["sqz_state"]],
                symbol="x",
            ),
            showlegend=False,
            hovertemplate="%{customdata}<extra></extra>",
            customdata=chart_df["sqz_state"],
        ),
        row=2, col=1,
    )

    fig.update_layout(
        height=560,
        margin=dict(l=8, r=8, t=30, b=8),
        bargap=0.15,
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
    fig.update_yaxes(title_text="Squeeze", title_font=dict(size=10), row=2, col=1)
    return fig


price_decimals = formatting.price_decimals


# Streamlit 每次互動(例如展開折疊區塊)都會重跑整個腳本。
# 沒有快取的話,每次點擊都會對 OKX 發出十餘次請求,既慢又容易被限流。
@st.cache_data(ttl=300, show_spinner=False)
def load_indicators(symbol: str, timeframe: str) -> pd.DataFrame:
    return indicators.add_indicators(
        data_fetcher.fetch_ohlcv(symbol, timeframe=timeframe), timeframe
    )


@st.cache_data(ttl=3600, show_spinner=False)
def load_zones(symbol: str, price: float) -> list:
    # 日線區間變動遠慢於 1 小時訊號,快取時間拉長
    return levels.fetch_zones(symbol, price)


st.set_page_config(page_title="Market Signal Radar", layout="wide")

st.title("Market Signal Radar")

head_left, head_right = st.columns([3, 1])
with head_right:
    timeframe = st.selectbox(
        "K 線時框",
        config.DASHBOARD_TIMEFRAMES,
        index=config.DASHBOARD_TIMEFRAMES.index(config.TIMEFRAME),
        help=(
            f"僅影響此頁面。LINE 通知固定使用 {config.TIMEFRAME},不受此處切換影響。"
        ),
    )
with head_left:
    st.caption(
        f"資料來源:OKX 公開 API｜檢視時框:{timeframe}"
        f"(通知固定 {config.TIMEFRAME})｜僅供參考,非投資建議"
    )
    if timeframe != config.TIMEFRAME:
        st.info(
            f"目前檢視 {timeframe} 時框,與通知所用的 {config.TIMEFRAME} 不同,"
            f"因此下方訊號與你收到的 LINE 內容可能不一致。",
            icon="ℹ️",
        )

if st.button("🔄 重新整理"):
    # 清掉快取才會真的重抓,否則按了也是拿到同一份資料
    st.cache_data.clear()

with st.spinner("抓取資料並計算指標中..."):
    evaluations = {}
    indicator_dfs = {}
    zone_map = {}
    errors = {}
    for symbol in config.SYMBOLS:
        try:
            df = load_indicators(symbol, timeframe)
        except Exception as exc:
            errors[symbol] = str(exc)
            continue
        zones = load_zones(symbol, float(df["close"].iloc[-2]))
        evaluations[symbol] = signals.evaluate(df, symbol, zones)
        indicator_dfs[symbol] = df
        zone_map[symbol] = zones

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
        f"訊號依據 {candle_time:%m-%d %H:%M} 起算的已收盤 K 棒(台灣時間)。"
        f"未收盤的 K 棒價格仍在變動,不納入判斷,因此訊號在該根 K 棒期間維持不變。"
        f"　🔔 標記者會發送 LINE 通知,其餘僅在此顯示。"
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
                "擠壓": indicator_dfs[symbol]["sqz_state"].iloc[-2],
                "CE": "多" if ev["ce_direction"] == 1 else "空",
                "CE停損": (
                    formatting.format_price(ev["ce_stop"])
                    if ev["ce_stop"] is not None
                    else "—"
                ),
                "鄰近區間": (
                    f"{ev['near_zone']['kind']}×{ev['near_zone']['touches']}"
                    if ev["near_zone"]
                    else "—"
                ),
                "通知": "🔔" if symbol in config.ALERT_SYMBOLS else "",
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
                make_candlestick_chart(
                    indicator_dfs[symbol], symbol, zone_map.get(symbol)
                ),
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

            if ev["ce_stop"] is not None:
                gap = (ev["price"] - ev["ce_stop"]) / ev["price"] * 100
                st.metric(
                    f"Chandelier Exit 停損({'多方' if ev['ce_direction'] == 1 else '空方'})",
                    formatting.format_price(ev["ce_stop"]),
                    delta=f"距現價 {abs(gap):.2f}%",
                    delta_color="off",
                    help=(
                        f"ATR({config.ce_period(timeframe)})×{config.CE_MULTIPLIER} 的移動停損。"
                        "持多時只往上抬、持空時只往下降,收盤價跌破即翻轉方向。"
                    ),
                )

            st.markdown("**觸發條件**")
            for reason in ev["reasons"]:
                st.markdown(f"- {reason}")
