"""從較高時框的 K 線找出壓力區與支撐區。

作法分三步:
1. 找擺動高低點(swing high / low)—— 價格轉折處,代表當時多空易手的位置
2. 把相近的轉折點聚成「區」—— 同一個價位被反覆測試,才是有意義的壓力支撐
3. 依測試次數篩選強度,再取離現價最近的幾個

壓力或支撐是相對於現價而定:現價之上為壓力,之下為支撐。同一個價位在跌破後
會由支撐轉為壓力,因此不在偵測階段區分,而在判讀時依現價決定。
"""

from dataclasses import dataclass

import pandas as pd

import config


@dataclass
class Zone:
    """一個壓力/支撐區。"""

    low: float          # 區間下緣
    high: float         # 區間上緣
    center: float       # 區間中心,用於距離計算
    touches: int        # 被測試的次數,次數越多代表越受重視

    def kind(self, price: float) -> str:
        """相對於現價,此區為壓力或支撐。"""
        return "支撐" if self.center <= price else "壓力"

    def distance_pct(self, price: float) -> float:
        """現價距離此區中心的百分比(取絕對值)。"""
        return abs(price - self.center) / price * 100


def find_pivots(df: pd.DataFrame, window: int) -> tuple[list[float], list[float]]:
    """找出擺動高點與低點。

    某根 K 棒的高點若是其前後各 window 根範圍內的最高,即視為擺動高點,低點同理。
    因為需要右側的 K 棒才能確認轉折,最後 window 根不會產生擺動點 —— 這是必要的,
    否則會把還在發展中的價格誤判為已成立的轉折。
    """
    highs: list[float] = []
    lows: list[float] = []
    h = df["high"].to_numpy()
    l = df["low"].to_numpy()

    for i in range(window, len(df) - window):
        seg_h = h[i - window : i + window + 1]
        seg_l = l[i - window : i + window + 1]
        if h[i] >= seg_h.max():
            highs.append(float(h[i]))
        if l[i] <= seg_l.min():
            lows.append(float(l[i]))
    return highs, lows


def cluster_prices(prices: list[float], tolerance_pct: float) -> list[list[float]]:
    """把價格聚成數群,每群的總寬度不超過 tolerance_pct。

    比對基準是群組的「第一個」成員而非前一個 —— 若只比對相鄰兩者,
    A→B、B→C 各差一個容忍度時會不斷串聯下去,整群寬度可以無限延伸,
    最後圈出一個涵蓋整段行情的區間,失去壓力支撐的意義。
    """
    if not prices:
        return []

    groups: list[list[float]] = []
    for price in sorted(prices):
        if groups and (price - groups[-1][0]) / groups[-1][0] * 100 <= tolerance_pct:
            groups[-1].append(price)
        else:
            groups.append([price])
    return groups


def find_zones(df: pd.DataFrame, price: float) -> list[Zone]:
    """從高時框 K 線找出離現價最近的幾個壓力支撐區。"""
    highs, lows = find_pivots(df, config.SR_PIVOT_WINDOW)
    groups = cluster_prices(highs + lows, config.SR_CLUSTER_PCT)

    zones = [
        Zone(
            low=min(g),
            high=max(g),
            center=sum(g) / len(g),
            touches=len(g),
        )
        for g in groups
        if len(g) >= config.SR_MIN_TOUCHES
    ]

    # 離現價太遠的區間短期內碰不到,參考價值低,只留最近的幾個
    zones.sort(key=lambda z: z.distance_pct(price))
    return zones[: config.SR_MAX_ZONES]


def fetch_zones(symbol: str, price: float) -> list[Zone]:
    """抓取高時框 K 線並找出壓力支撐區。失敗時回傳空清單。

    壓力支撐只是輔助判斷,抓不到不應讓整個訊號流程中斷,
    因此吞掉例外並以空清單表示「這次沒有可用的區間資訊」。
    """
    import data_fetcher  # 延後匯入,避免與 data_fetcher 形成循環相依

    try:
        df = data_fetcher.fetch_ohlcv(
            symbol, timeframe=config.SR_TIMEFRAME, limit=config.SR_LOOKBACK
        )
    except Exception:
        return []
    return find_zones(df, price)


def nearest_zone(zones: list[Zone], price: float) -> Zone | None:
    """回傳現價附近(SR_NEAR_PCT 以內)最接近的區,沒有則回 None。"""
    for zone in sorted(zones, key=lambda z: z.distance_pct(price)):
        # 價格落在區間內、或與中心距離夠近,都算「接近」
        if zone.low <= price <= zone.high:
            return zone
        if zone.distance_pct(price) <= config.SR_NEAR_PCT:
            return zone
    return None
