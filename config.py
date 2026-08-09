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

# K 線時框(1 小時)
# 與每小時檢查一次的排程對齊,每次檢查剛好有一根新收盤的 K 棒。
TIMEFRAME = "1h"

# 顯示時區。交易所回傳的時間戳為 UTC,抓取後即轉為此時區,
# 因此 K 線圖橫軸與所有時間標示都是這個時區的時間。
DISPLAY_TIMEZONE = "Asia/Taipei"

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

# 量能確認參數
# 量能本身沒有方向性,因此不當作獨立訊號,而是用來強化或削弱既有的價格訊號:
# 放量代表這個方向有籌碼支撐,縮量則代表推力不足、訊號存疑。
VOLUME_MA_PERIOD = 20        # 均量計算期數
VOLUME_SURGE_RATIO = 1.5     # 達均量幾倍視為放量
VOLUME_DRY_RATIO = 0.7       # 低於均量幾倍視為縮量

# 只有這些標的套用量能確認。
# 股票永續合約(MU/QQQ/MRVL/DRAM)追蹤的美股有開收盤時段,休市時量能會大幅萎縮,
# 用混合開盤與休市 K 棒算出的均量當基準會失真,量能規則會淪為偵測「美股是否開盤」,
# 因此僅對 24 小時連續交易的加密貨幣套用。
VOLUME_CONFIRM_SYMBOLS = ["BTC/USDT", "ETH/USDT"]

# 通知門檻:分數絕對值達到此值才發送 LINE 通知。
# 設為 2 表示需要兩條規則同時指向同一方向,可過濾 1 小時時框的雜訊。
# 實測(23 天回溯):1h 搭配門檻 1 每月約 542 則,會超出 LINE 免費額度 200 則;
# 搭配門檻 2 則約 117 則。
ALERT_MIN_SCORE = 2
