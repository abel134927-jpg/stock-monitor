"""
個股監測系統設定檔
港股格式: XXXX.HK  (yfinance 慣例，前置零只保留4位)
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 監測股票清單 — 港股
# ============================================================
WATCHLIST = [
    {"code": "0823.HK",  "name": "領展房產基金"},
    {"code": "9961.HK",  "name": "攜程集團"},
    {"code": "9988.HK",  "name": "阿里巴巴"},
    {"code": "7709.HK",  "name": "恒科指數反向1X"},
    {"code": "3110.HK",  "name": "GX中國電動車ETF"},
    {"code": "9992.HK",  "name": "泡泡瑪特"},
]

# ============================================================
# 策略參數
# ============================================================
STRATEGY_PARAMS = {
    "ma_short": 5,
    "ma_mid": 20,
    "ma_long": 60,
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 80,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "kd_period": 9,
    "box_period": 20,
    "volume_ma_period": 5,
    "volume_multiplier": 1.5,
    "breakout_min_pct": 3.0,
    "pullback_tolerance": 0.015,
    "reversal_tolerance": 0.03,
    "target_multiplier": 1.05,
}

# ============================================================
# DeepSeek API
# ============================================================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

# ============================================================
# 資料設定
# ============================================================
DATA_PERIOD = "6mo"
DATA_INTERVAL = "1d"

# Web Server
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "1800"))   # 快取秒數，預設30分鐘

# 舊版 CLI 設定（保留相容性）
REPORT_DIR = "reports"
LOG_DIR = "logs"

# Email / LINE（若需要 CLI 版推送）
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
LINE_NOTIFY_ENABLED = os.getenv("LINE_NOTIFY_ENABLED", "false").lower() == "true"
LINE_NOTIFY_TOKEN = os.getenv("LINE_NOTIFY_TOKEN", "")
