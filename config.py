"""集中管理追蹤幣種、時框與技術指標參數。"""

# 使用 OKX:Binance(451)與 Bybit(403)會封鎖雲端主機 IP,
# OKX 實測可從 GitHub Actions / Streamlit Cloud 存取,且有股票永續合約。
# symbol 格式為 ccxt 慣例,":USDT" 後綴代表永續合約(perpetual swap)。
SYMBOLS = [
    "BTC/USDT",        # 比特幣(現貨)
    "ETH/USDT",        # 以太幣(現貨)
    "MU/USDT:USDT",    # 美光科技 永續合約
    "QQQ/USDT:USDT",   # 納斯達克100 ETF 永續合約
    "MRVL/USDT:USDT",  # Marvell 永續合約
    "DRAM/USDT:USDT",  # DRAM 記憶體指數 永續合約
]

# K 線時框(4 小時)
TIMEFRAME = "4h"

# 每次抓取的 K 線根數(需足夠計算 EMA50 等指標的暖機期)
OHLCV_LIMIT = 200

# 指標參數
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

EMA_FAST = 20
EMA_SLOW = 50

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

BB_PERIOD = 20
BB_STD = 2

# 通知門檻:分數絕對值達到此值才發送 LINE 通知(1 = 只要不是中性就通知)
ALERT_MIN_SCORE = 1
