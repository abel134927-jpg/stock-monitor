"""
資料抓取模組
使用 yfinance 取得股票 OHLCV 日線數據
台股格式: 2330.TW / 美股格式: AAPL
"""
import logging
import yfinance as yf
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)


def fetch_stock_data(code: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    """
    抓取單支股票歷史數據

    Args:
        code: 股票代號 (e.g. "2330.TW", "AAPL")
        period: 抓取期間 ("1mo", "3mo", "6mo", "1y")
        interval: K棒週期 ("1d", "1wk")

    Returns:
        DataFrame [Open, High, Low, Close, Volume]，失敗回傳 None
    """
    try:
        ticker = yf.Ticker(code)
        df = ticker.history(period=period, interval=interval, auto_adjust=True)

        if df.empty:
            logger.warning(f"[{code}] 無法取得數據（可能代號錯誤或該交易日無資料）")
            return None

        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)  # 移除時區資訊
        df = df.dropna(subset=["Close", "Volume"])

        if len(df) < 65:
            logger.warning(f"[{code}] 數據筆數不足 ({len(df)} 筆)，無法計算所有指標")
            return None

        logger.info(f"[{code}] 取得 {len(df)} 筆數據，最新: {df.index[-1].date()}")
        return df

    except Exception as e:
        logger.error(f"[{code}] 抓取失敗: {e}")
        return None


def fetch_all_stocks(watchlist: list, period: str = "6mo", interval: str = "1d") -> dict:
    """
    批量抓取所有監測股票

    Returns:
        dict: { "2330.TW": ("台積電", DataFrame), ... }
        只包含成功取得數據的股票
    """
    results = {}
    total = len(watchlist)

    for i, stock in enumerate(watchlist, 1):
        code = stock["code"]
        name = stock["name"]
        logger.info(f"[{i}/{total}] 正在抓取 {name} ({code})...")

        df = fetch_stock_data(code, period, interval)
        if df is not None:
            results[code] = (name, df)
        else:
            logger.warning(f"[{code}] {name} 已略過")

    logger.info(f"成功取得 {len(results)}/{total} 支股票數據")
    return results
