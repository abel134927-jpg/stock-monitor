"""
DeepSeek AI 分析模組
對有訊號的股票呼叫 DeepSeek API，產生中文技術分析說明
使用 openai 相容介面（DeepSeek API 與 OpenAI SDK 相容）
"""
import logging
import re
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from strategy import SignalResult

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _client


def _build_prompt(s: SignalResult) -> str:
    """組裝傳給 DeepSeek 的分析提示詞"""
    change_str = f"+{s.change_pct:.2f}%" if s.change_pct >= 0 else f"{s.change_pct:.2f}%"
    aux_str  = "、".join(s.aux_conditions) if s.aux_conditions else "無"
    sell_str = "、".join(s.sell_reasons)   if s.sell_reasons   else "無"

    ma_trend = "多頭排列" if s.ma5 > s.ma20 > s.ma60 else ("空頭排列" if s.ma5 < s.ma20 < s.ma60 else "混沌排列")
    macd_dir = "正值(多頭)" if s.macd_hist > 0 else "負值(空頭)"

    # 觀望時不顯示價格點位
    price_line = ""
    if s.action == "買進":
        price_line = f"\n【點位】買入={s.buy_price:.2f}  停損={s.stop_loss:.2f}  目標={s.target_price:.2f}"

    return f"""你是一位專業的港股技術分析師，請根據以下即時數據給出簡潔的繁體中文分析。

【標的】{s.name}（{s.code}）  日期：{s.date}
【價格】收盤 {s.close:.2f} HKD（{change_str}）  量比：{s.volume_ratio:.2f}x
【均線】5MA={s.ma5:.2f}  20MA={s.ma20:.2f}  60MA={s.ma60:.2f}  → {ma_trend}
【震盪】RSI={s.rsi:.1f}  MACD柱={s.macd_hist:+.4f}({macd_dir})  KD: K={s.k_val:.1f}/D={s.d_val:.1f}
【箱體】{s.box_bottom:.2f} ~ {s.box_top:.2f}
【訊號】{s.label}  核心={s.core_condition}  輔助={aux_str}  賣出原因={sell_str}{price_line}

請依序輸出以下三點（每點不超過指定字數，使用繁體中文）：
1.【市場解讀】（40字內）：說明目前技術面狀況
2.【操作建議】（30字內）：具體進出場建議
3.【風險提示】（20字內）：主要風險點"""


def analyze(signal: SignalResult) -> str:
    """
    對單支股票進行 AI 分析
    Returns: 分析文字，失敗時回傳錯誤說明
    """
    if not DEEPSEEK_API_KEY:
        return "（未設定 DEEPSEEK_API_KEY，跳過 AI 分析）"

    try:
        response = _get_client().chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你是專業港股技術分析師，回覆精準、簡潔，使用繁體中文，不加廢話。"
                },
                {
                    "role": "user",
                    "content": _build_prompt(signal)
                }
            ],
            max_tokens=350,
            temperature=0.3,
            timeout=10,
        )
        raw = response.choices[0].message.content.strip()
        # 移除 AI 回傳的字數限制標注，例如「（40字內）」「(30字內)」
        clean = re.sub(r'[（(]\d+字[內以]?[）)]', '', raw).strip()
        return clean

    except Exception as e:
        logger.error(f"[{signal.code}] DeepSeek API 錯誤: {e}")
        return f"（AI 分析暫時失敗: {e}）"


def batch_analyze(signals: list[SignalResult]) -> list[SignalResult]:
    """所有股票（包含觀望）都進行 AI 分析"""
    total = len(signals)
    if total == 0:
        return signals

    logger.info(f"開始 AI 分析，共 {total} 支股票...")
    for i, signal in enumerate(signals, 1):
        logger.info(f"  [{i}/{total}] 分析 {signal.name}({signal.code})...")
        signal.ai_analysis = analyze(signal)

    return signals
