"""
策略核心模組
實現「動態確信度分級」個股監測邏輯：
  核心條件: 突破 / 回測 / 反轉
  輔助加分: 黃金交叉 / MACD轉正 / RSI超賣反彈
  確信度分級: A類(高) / B類(中) / C類(低)
  賣出邏輯: 跌破箱底 / RSI超買+量縮背離
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import pandas as pd
from config import STRATEGY_PARAMS

P = STRATEGY_PARAMS


# ============================================================
# 資料結構
# ============================================================

@dataclass
class SignalResult:
    """單支股票當日訊號結果"""
    code: str
    name: str
    date: str
    action: str           # 買進 / 賣出 / 觀察中 / 觀望
    confidence: str       # A / B / C / -

    core_condition: str = "-"                    # 突破 / 回測 / 反轉
    aux_conditions: list = field(default_factory=list)
    sell_reasons: list = field(default_factory=list)

    # 價格點位
    close: float = 0.0
    change_pct: float = 0.0
    buy_price: float = 0.0
    stop_loss: float = 0.0
    target_price: float = 0.0

    # 指標數值 (用於報告與 AI 分析)
    ma5: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0
    rsi: float = 0.0
    macd_hist: float = 0.0
    k_val: float = 0.0
    d_val: float = 0.0
    volume_ratio: float = 0.0
    box_top: float = 0.0
    box_bottom: float = 0.0

    ai_analysis: str = ""

    @property
    def action_emoji(self) -> str:
        return {"買進": "✅", "賣出": "🔴", "觀察中": "👀", "觀望": "⏸"}.get(self.action, "❓")

    @property
    def label(self) -> str:
        if self.action == "買進":
            return f"買進({self.confidence}類)"
        return self.action


# ============================================================
# 核心條件偵測
# ============================================================

def _detect_breakout(row: pd.Series) -> bool:
    """突破訊號：收盤突破 20 日箱頂 + 成交量 > 5MA x 1.5"""
    close = row["Close"]
    vol = row["Volume"]
    vol_ma = row[f"Vol_MA{P['volume_ma_period']}"]
    box_top = row["Box_Top"]

    if pd.isna(box_top) or pd.isna(vol_ma) or vol_ma <= 0:
        return False
    return close > box_top and vol > vol_ma * P["volume_multiplier"]


def _detect_pullback(row: pd.Series) -> bool:
    """
    回測訊號：
    - 價格回拉至 20MA ±1.5%
    - 出現明顯下影線（下影線 > 全程 30%）
    - 收盤仍在 20MA 之上
    """
    close = row["Close"]
    ma20 = row[f"MA{P['ma_mid']}"]
    lower_shadow = row["Lower_Shadow"]
    candle_range = row["Candle_Range"]

    if pd.isna(ma20) or ma20 <= 0:
        return False

    near_ma20 = abs(close - ma20) / ma20 <= P["pullback_tolerance"]
    has_shadow = candle_range > 0 and lower_shadow > candle_range * 0.30
    above_ma20 = close >= ma20

    return near_ma20 and has_shadow and above_ma20


def _detect_reversal(row: pd.Series, prev: pd.DataFrame) -> bool:
    """
    反轉訊號 (任一成立即觸發)：
    1. 破底翻：近 10 日曾跌破前低，今日收盤回到前低之上
    2. W底：近 20 日出現兩個相近低點，今日收盤突破頸線
    """
    close = row["Close"]

    # --- 方法一：破底翻 ---
    if len(prev) >= 20:
        recent_10 = prev.tail(10)
        prior_10 = prev.iloc[-20:-10]
        if not prior_10.empty:
            prior_low = prior_10["Low"].min()
            recent_low = recent_10["Low"].min()
            broke_down = recent_low < prior_low * 0.99   # 曾破底
            recovered = close > prior_low                # 今日回升
            if broke_down and recovered:
                return True

    # --- 方法二：W底突破頸線 ---
    if len(prev) >= 20:
        recent_20 = prev.tail(20)
        lows = recent_20["Low"].values
        highs = recent_20["High"].values

        local_mins = [
            i for i in range(1, len(lows) - 1)
            if lows[i] < lows[i - 1] and lows[i] < lows[i + 1]
        ]

        if len(local_mins) >= 2:
            i1, i2 = local_mins[-2], local_mins[-1]
            low1, low2 = lows[i1], lows[i2]

            if abs(low1 - low2) / max(low1, low2) <= P["reversal_tolerance"]:
                neckline = highs[i1:i2].max() if i2 > i1 else 0
                if neckline > 0 and close > neckline:
                    return True

    return False


def detect_core(row: pd.Series, prev: pd.DataFrame) -> tuple[str, bool]:
    """
    偵測核心條件（依優先序）
    Returns: (condition_name, is_triggered)
    """
    if _detect_breakout(row):
        return "突破", True
    if _detect_pullback(row):
        return "回測", True
    if len(prev) >= 20 and _detect_reversal(row, prev):
        return "反轉", True
    return "-", False


# ============================================================
# 輔助條件偵測
# ============================================================

def detect_auxiliary(row: pd.Series, prev: pd.DataFrame) -> list[str]:
    """
    偵測輔助加分條件
    Returns: list of triggered condition names
    """
    aux = []
    ma5 = row[f"MA{P['ma_short']}"]
    ma20 = row[f"MA{P['ma_mid']}"]
    macd_hist = row["MACD_Hist"]
    rsi = row["RSI"]

    # 輔助一：5MA > 20MA (黃金交叉 / 短期多頭)
    if pd.notna(ma5) and pd.notna(ma20) and ma5 > ma20:
        aux.append("黃金交叉")

    # 輔助二：MACD 柱狀圖由負轉正
    if pd.notna(macd_hist) and len(prev) >= 1:
        prev_hist = prev["MACD_Hist"].iloc[-1]
        if macd_hist > 0 and pd.notna(prev_hist) and prev_hist <= 0:
            aux.append("MACD轉正")

    # 輔助三：RSI 從超賣區 (<30) 往上翻
    if pd.notna(rsi) and rsi > P["rsi_oversold"] and len(prev) >= 3:
        recent_min_rsi = prev["RSI"].tail(5).min()
        if pd.notna(recent_min_rsi) and recent_min_rsi < P["rsi_oversold"]:
            aux.append("RSI超賣反彈")

    return aux


# ============================================================
# 賣出訊號偵測
# ============================================================

def detect_sell(row: pd.Series) -> list[str]:
    """
    偵測賣出 / 出場警示
    Returns: list of sell reason strings
    """
    reasons = []
    close = row["Close"]
    rsi = row["RSI"]
    box_bottom = row["Box_Bottom"]
    vol = row["Volume"]
    vol_ma = row[f"Vol_MA{P['volume_ma_period']}"]

    # 賣出一：跌破 20 日箱底
    if pd.notna(box_bottom) and close < box_bottom:
        reasons.append("跌破20日箱底")

    # 賣出二：RSI > 80 且量縮 (量價背離)
    if pd.notna(rsi) and rsi > P["rsi_overbought"]:
        volume_shrink = pd.notna(vol_ma) and vol_ma > 0 and vol < vol_ma * 0.8
        if volume_shrink:
            reasons.append("RSI超買+量縮背離")
        else:
            reasons.append("RSI超買警示")

    return reasons


# ============================================================
# 主入口：對單支股票分類
# ============================================================

def classify(code: str, name: str, df: pd.DataFrame) -> SignalResult:
    """
    對含有技術指標的 DataFrame 進行訊號分析，回傳 SignalResult

    DataFrame 需已由 indicators.calculate_all() 處理
    """
    if len(df) < 30:
        return SignalResult(code=code, name=name, date="-", action="觀望", confidence="-")

    row = df.iloc[-1]
    prev = df.iloc[:-1]
    date = str(df.index[-1].date())

    # 基本數值
    close = row["Close"]
    prev_close = df["Close"].iloc[-2] if len(df) >= 2 else close
    change_pct = (close - prev_close) / prev_close * 100 if prev_close else 0.0

    vol_ma = row[f"Vol_MA{P['volume_ma_period']}"]
    vol_ratio = row["Volume"] / vol_ma if pd.notna(vol_ma) and vol_ma > 0 else 0.0

    def safe(val, decimals=2):
        return round(float(val), decimals) if pd.notna(val) else 0.0

    result = SignalResult(
        code=code,
        name=name,
        date=date,
        action="觀望",
        confidence="-",
        close=safe(close),
        change_pct=safe(change_pct),
        ma5=safe(row[f"MA{P['ma_short']}"]),
        ma20=safe(row[f"MA{P['ma_mid']}"]),
        ma60=safe(row[f"MA{P['ma_long']}"]),
        rsi=safe(row["RSI"], 1),
        macd_hist=safe(row["MACD_Hist"], 4),
        k_val=safe(row["K"], 1),
        d_val=safe(row["D"], 1),
        volume_ratio=safe(vol_ratio),
        box_top=safe(row["Box_Top"]),
        box_bottom=safe(row["Box_Bottom"]),
    )

    # 1. 先偵測賣出訊號（優先觸發）
    sell_reasons = detect_sell(row)
    if sell_reasons:
        result.action = "賣出"
        result.sell_reasons = sell_reasons
        return result

    # 2. 偵測核心條件
    core_name, core_hit = detect_core(row, prev)
    if not core_hit:
        return result  # 無訊號 → 觀望

    result.core_condition = core_name

    # 3. 假訊號過濾：突破幅度不足 3%
    if core_name == "突破" and result.box_top > 0:
        breakout_pct = (close - result.box_top) / result.box_top * 100
        if breakout_pct < P["breakout_min_pct"]:
            result.action = "觀察中"
            return result

    # 4. 輔助條件
    aux = detect_auxiliary(row, prev)
    result.aux_conditions = aux

    # 5. 確信度分級
    aux_count = len(aux)
    if aux_count >= 2:
        result.confidence = "A"
    elif aux_count == 1:
        result.confidence = "B"
    else:
        result.confidence = "C"

    # 6. 計算買入 / 停損 / 目標價
    result.action = "買進"
    result.buy_price = safe(close)
    result.stop_loss = safe(row["Low"])                            # 當根 K 棒低點
    result.target_price = safe(close * P["target_multiplier"])    # 簡易 5% 目標

    # 補充：若 20MA 比 K 棒低點更近，以 20MA 作為參考停損
    if result.ma20 > 0 and result.ma20 < result.stop_loss:
        result.stop_loss = safe(result.ma20)

    return result
