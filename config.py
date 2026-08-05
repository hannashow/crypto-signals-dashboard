"""集中管理追蹤幣種、時框與技術指標參數。"""

# 交易所使用 ccxt 的 symbol 格式(例如 "BTC/USD")
# 使用 Kraken:Binance 會封鎖 Streamlit Cloud 等雲端主機所在地區(HTTP 451)
SYMBOLS = ["BTC/USD", "ETH/USD", "ADA/USD", "SOL/USD", "XRP/USD"]

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
