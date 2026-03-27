"""
技術指標計算模組
計算: MA5/20/60, RSI(14), MACD(12,26,9), KD(9), 箱體區間, 蠟燭結構
"""
import numpy as np
import pandas as pd
from config import STRATEGY_PARAMS

P = STRATEGY_PARAMS


def calculate_ma(df: pd.DataFrame) -> pd.DataFrame:
    """移動平均線 MA5 / MA20 / MA60 及成交量均線"""
    df[f"MA{P['ma_short']}"] = df["Close"].rolling(P["ma_short"]).mean()
    df[f"MA{P['ma_mid']}"] = df["Close"].rolling(P["ma_mid"]).mean()
    df[f"MA{P['ma_long']}"] = df["Close"].rolling(P["ma_long"]).mean()
    df[f"Vol_MA{P['volume_ma_period']}"] = df["Volume"].rolling(P["volume_ma_period"]).mean()
    return df


def calculate_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """RSI(14) — 使用 Wilder EMA 平滑法"""
    period = P["rsi_period"]
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder smoothing = EWM with com = period - 1
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    return df


def calculate_macd(df: pd.DataFrame) -> pd.DataFrame:
    """MACD(12, 26, 9)"""
    ema_fast = df["Close"].ewm(span=P["macd_fast"], adjust=False).mean()
    ema_slow = df["Close"].ewm(span=P["macd_slow"], adjust=False).mean()

    df["MACD"] = ema_fast - ema_slow
    df["MACD_Signal"] = df["MACD"].ewm(span=P["macd_signal"], adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    return df


def calculate_kd(df: pd.DataFrame) -> pd.DataFrame:
    """
    KD 隨機指標 (台灣版加權平滑)
    K = K_prev * 2/3 + RSV * 1/3
    D = D_prev * 2/3 + K  * 1/3
    初始值 K=D=50
    """
    period = P["kd_period"]

    low_min = df["Low"].rolling(period).min()
    high_max = df["High"].rolling(period).max()
    price_range = (high_max - low_min).replace(0, np.nan)

    rsv = ((df["Close"] - low_min) / price_range * 100).fillna(50).values

    k_arr = np.full(len(rsv), 50.0)
    d_arr = np.full(len(rsv), 50.0)

    for i in range(1, len(rsv)):
        k_arr[i] = k_arr[i - 1] * (2 / 3) + rsv[i] * (1 / 3)
        d_arr[i] = d_arr[i - 1] * (2 / 3) + k_arr[i] * (1 / 3)

    df["K"] = k_arr
    df["D"] = d_arr
    return df


def calculate_box(df: pd.DataFrame) -> pd.DataFrame:
    """
    近 N 日箱體區間（使用前一日數據，避免當日影響）
    Box_Top    = 前 20 日最高點
    Box_Bottom = 前 20 日最低點
    """
    period = P["box_period"]
    df["Box_Top"] = df["High"].shift(1).rolling(period).max()
    df["Box_Bottom"] = df["Low"].shift(1).rolling(period).min()
    return df


def calculate_candle(df: pd.DataFrame) -> pd.DataFrame:
    """蠟燭結構分析：實體、上影線、下影線"""
    df["Body"] = (df["Close"] - df["Open"]).abs()
    df["Upper_Shadow"] = df["High"] - df[["Close", "Open"]].max(axis=1)
    df["Lower_Shadow"] = df[["Close", "Open"]].min(axis=1) - df["Low"]
    df["Candle_Range"] = df["High"] - df["Low"]
    return df


def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
    """一次計算所有技術指標"""
    df = df.copy()
    df = calculate_ma(df)
    df = calculate_rsi(df)
    df = calculate_macd(df)
    df = calculate_kd(df)
    df = calculate_box(df)
    df = calculate_candle(df)
    return df
