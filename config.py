"""集中管理追蹤幣種、時框與技術指標參數。"""

# 使用 OKX:Binance(451)與 Bybit(403)會封鎖雲端主機 IP,
# OKX 實測可從 GitHub Actions / Streamlit Cloud 存取,且有股票永續合約。
# symbol 格式為 ccxt 慣例,":USDT" 後綴代表永續合約(perpetual swap)。
#
# SYMBOLS 是儀表板顯示的完整清單;ALERT_SYMBOLS 是其中會發 LINE 通知的子集。
# 兩者分開是因為 LINE 免費額度每月僅 200 則,標的越多通知越多,
# 全部都通知會超量。不通知的標的仍可隨時打開儀表板查看。
SYMBOLS = [
    "BTC/USDT",         # 比特幣(現貨)
    "ETH/USDT",         # 以太幣(現貨)
    "MU/USDT:USDT",     # 美光科技
    "QQQ/USDT:USDT",    # 納斯達克100 ETF
    "MRVL/USDT:USDT",   # Marvell
    "DRAM/USDT:USDT",   # DRAM 記憶體指數
    "NVDA/USDT:USDT",   # NVIDIA
    "TSLA/USDT:USDT",   # Tesla
    "AAPL/USDT:USDT",   # Apple
    "GOOGL/USDT:USDT",  # Alphabet A 股(OKX 無 GOOG,GOOGL 為有投票權的股別)
    "COIN/USDT:USDT",   # Coinbase
    "SPCX/USDT:USDT",   # OKX 上架的 SPCX 合約
]

# 會發送 LINE 通知的標的。其餘標的只在儀表板顯示。
ALERT_SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "MU/USDT:USDT",
    "QQQ/USDT:USDT",
    "MRVL/USDT:USDT",
    "DRAM/USDT:USDT",
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

# 壓力支撐參數
# 用日線找主要區間、1 小時看價格接近時的反應,是搭配短線操作的標準組合。
# 高時框的區間累積了更多成交與時間,比低時框的價位更受重視;時框太短則雜訊過多,
# 到處都是「支撐」反而失去參考價值。
SR_TIMEFRAME = "1d"
SR_LOOKBACK = 120            # 取幾根日線,約半年
SR_PIVOT_WINDOW = 3          # 前後各幾根都不越過,才算擺動高低點
SR_CLUSTER_PCT = 1.5         # 相距多少 % 以內的轉折點視為同一區
SR_MIN_TOUCHES = 2           # 至少被測試幾次才算有效區間
SR_NEAR_PCT = 1.0            # 現價距離區間多少 % 以內算「接近」
SR_MAX_ZONES = 6             # 最多保留離現價最近的幾個區
# 距離現價超過此 % 的區間一律捨棄。除了短期內碰不到、參考價值低之外,
# 也用來擋掉合約規格變更造成的假區間 —— 例如 SPCX 曾在 2026 年 6 月重設
# 換算基準,價格由二千餘跌至一百餘,變更前的歷史價位與現價並非同一基準。
SR_MAX_DISTANCE_PCT = 25.0

# 通知門檻:分數絕對值達到此值才發送 LINE 通知。
# 設為 2 表示需要兩條規則同時指向同一方向,可過濾 1 小時時框的雜訊。
# 實測(23 天回溯):1h 搭配門檻 1 每月約 542 則,會超出 LINE 免費額度 200 則;
# 搭配門檻 2 則約 117 則。
ALERT_MIN_SCORE = 2
