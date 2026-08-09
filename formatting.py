"""價格顯示格式。

追蹤標的的價格橫跨數萬(BTC)到零點幾(DRAM)數個量級,
固定小數位會讓高價標的補一堆無意義的零、低價標的又精度不足,
因此依數量級決定位數。
"""


def price_decimals(price: float) -> int:
    """依價格大小決定顯示小數位。"""
    if price >= 100:
        return 2
    if price >= 1:
        return 3
    return 5


def format_price(price: float) -> str:
    """格式化價格,加上千分位並套用適當小數位。"""
    return f"{price:,.{price_decimals(price)}f}"
