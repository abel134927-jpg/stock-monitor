"""
GitHub Actions 分析腳本
每日 16:30 HKT 自動執行，結果存入 results.json
"""
import dataclasses
import json
import logging
from datetime import datetime

from config import WATCHLIST, DATA_PERIOD, DATA_INTERVAL
from data_fetcher import fetch_all_stocks
from indicators import calculate_all
from strategy import classify
from ai_analyzer import batch_analyze

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("run_analysis")


def main():
    logger.info("=== 開始分析 ===")

    stock_data = fetch_all_stocks(WATCHLIST, DATA_PERIOD, DATA_INTERVAL)
    if not stock_data:
        raise RuntimeError("所有股票數據均抓取失敗")

    raw = []
    for code, (name, df) in stock_data.items():
        try:
            df_ind = calculate_all(df)
            signal = classify(code, name, df_ind)
            ph = [float(v) for v in df_ind["Close"].tail(30)]
            dh = [str(d.date()) for d in df_ind.index[-30:]]
            raw.append((signal, ph, dh))
        except Exception as e:
            logger.error(f"[{code}] 分析失敗: {e}")

    action_order = {"買進": 0, "觀察中": 1, "賣出": 2, "觀望": 3}
    conf_order   = {"A": 0, "B": 1, "C": 2, "-": 9}
    raw.sort(key=lambda x: (
        action_order.get(x[0].action, 9),
        conf_order.get(x[0].confidence, 9),
    ))

    signal_objs = batch_analyze([x[0] for x in raw])

    signals_list = []
    for sig, ph, dh in raw:
        d = dataclasses.asdict(sig)
        d["label"] = sig.label
        d["action_emoji"] = sig.action_emoji
        d["price_history"] = ph
        d["date_history"] = dh
        signals_list.append(d)

    result = {
        "date":         datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market":       "港股 (HKEX)",
        "summary": {
            "total":    len(signals_list),
            "buy_a":    sum(1 for s in signals_list if s["action"] == "買進" and s["confidence"] == "A"),
            "buy_b":    sum(1 for s in signals_list if s["action"] == "買進" and s["confidence"] == "B"),
            "buy_c":    sum(1 for s in signals_list if s["action"] == "買進" and s["confidence"] == "C"),
            "watching": sum(1 for s in signals_list if s["action"] == "觀察中"),
            "sell":     sum(1 for s in signals_list if s["action"] == "賣出"),
            "hold":     sum(1 for s in signals_list if s["action"] == "觀望"),
        },
        "signals": signals_list,
    }

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info(f"=== 分析完成 {result['summary']} ===")
    logger.info("results.json 已儲存")


if __name__ == "__main__":
    main()
