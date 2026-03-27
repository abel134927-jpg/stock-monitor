"""
個股監測系統 — 主程式入口

執行方式：
  python main.py              # 立即執行一次分析
  python main.py --schedule   # 排程模式（每日 14:30 自動執行）
  python main.py --no-ai      # 跳過 AI 分析（省 API 費用，快速測試）

輸出：
  - 終端彩色報告
  - reports/YYYY-MM-DD.txt  (文字存檔)
  - Email 推送 (需設定 .env)
  - LINE Notify 推送 (需設定 .env)
"""
import argparse
import logging
import os
import schedule
import time
from datetime import datetime
from pathlib import Path

from config import WATCHLIST, DATA_PERIOD, DATA_INTERVAL, REPORT_DIR, LOG_DIR
from data_fetcher import fetch_all_stocks
from indicators import calculate_all
from strategy import classify
from ai_analyzer import batch_analyze
from report_generator import generate_text, generate_html, generate_line_summary
from notifier import send_email, send_line_notify


# ============================================================
# 日誌設定
# ============================================================

def setup_logging():
    Path(LOG_DIR).mkdir(exist_ok=True)
    log_file = Path(LOG_DIR) / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    fmt = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
    logging.basicConfig(level=logging.INFO, format=fmt, datefmt="%H:%M:%S", handlers=handlers)


logger = logging.getLogger("main")


# ============================================================
# 主分析流程
# ============================================================

def run_analysis(skip_ai: bool = False):
    """
    執行每日個股監測分析完整流程

    1. 抓取 OHLCV 數據
    2. 計算技術指標
    3. 判斷訊號與確信度
    4. AI 分析（可選）
    5. 生成並推送報告
    """
    start_time = datetime.now()
    logger.info("=" * 55)
    logger.info("  個股監測系統啟動")
    logger.info("=" * 55)

    # ── Step 1: 抓取數據 ──────────────────────────────────
    logger.info(f"監測清單: {len(WATCHLIST)} 支股票")
    stock_data = fetch_all_stocks(WATCHLIST, DATA_PERIOD, DATA_INTERVAL)

    if not stock_data:
        logger.error("所有股票數據均抓取失敗，終止執行。請確認網路連線與股票代號。")
        return

    # ── Step 2 & 3: 計算指標 + 產生訊號 ───────────────────
    signals = []
    for code, (name, df) in stock_data.items():
        try:
            df_with_ind = calculate_all(df)
            signal = classify(code, name, df_with_ind)
            signals.append(signal)
            logger.info(f"  {name}({code}): {signal.label}")
        except Exception as e:
            logger.error(f"  [{code}] 分析失敗: {e}", exc_info=True)

    if not signals:
        logger.error("無任何有效訊號，終止執行")
        return

    # 排序：A > B > C > 觀察中 > 賣出 > 觀望
    action_order = {"買進": 0, "觀察中": 1, "賣出": 2, "觀望": 3}
    conf_order = {"A": 0, "B": 1, "C": 2, "-": 9}
    signals.sort(key=lambda s: (action_order.get(s.action, 9), conf_order.get(s.confidence, 9)))

    # ── Step 4: AI 分析 ────────────────────────────────────
    if not skip_ai:
        signals = batch_analyze(signals)
    else:
        logger.info("已略過 AI 分析 (--no-ai)")

    # ── Step 5: 生成報告 ───────────────────────────────────
    report_date = start_time.strftime("%Y-%m-%d")
    text_report = generate_text(signals, report_date)
    html_report = generate_html(signals, report_date)
    line_msg = generate_line_summary(signals, report_date)

    # 終端輸出
    print("\n" + text_report + "\n")

    # 存檔
    Path(REPORT_DIR).mkdir(exist_ok=True)
    report_path = Path(REPORT_DIR) / f"{report_date}.txt"
    report_path.write_text(text_report, encoding="utf-8")
    logger.info(f"報告已存檔: {report_path}")

    # 推送
    subject = f"個股監測日報 {report_date}"
    send_email(subject, html_report, text_report)
    send_line_notify(line_msg)

    elapsed = (datetime.now() - start_time).seconds
    logger.info(f"分析完成，耗時 {elapsed} 秒")
    logger.info("=" * 55)

    return signals


# ============================================================
# 排程模式
# ============================================================

def schedule_mode(run_time: str = "14:30", skip_ai: bool = False):
    """
    每日排程執行
    台股收盤 13:30，預設 14:30 執行（確保數據已更新）
    """
    def job():
        run_analysis(skip_ai=skip_ai)

    schedule.every().day.at(run_time).do(job)
    logger.info(f"排程已設定：每日 {run_time} 自動執行")
    logger.info("等待中... (按 Ctrl+C 中斷)")

    # 首次啟動立即執行一次
    logger.info("首次啟動，立即執行一次分析...")
    run_analysis(skip_ai=skip_ai)

    while True:
        schedule.run_pending()
        time.sleep(30)


# ============================================================
# 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="個股監測系統 — 每日技術分析 + DeepSeek AI 推送"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="排程模式：每日固定時間自動執行（預設 14:30）",
    )
    parser.add_argument(
        "--time",
        default="14:30",
        metavar="HH:MM",
        help="排程執行時間，格式 HH:MM（預設 14:30）",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="跳過 DeepSeek AI 分析（快速測試 / 節省 API 費用）",
    )
    args = parser.parse_args()

    setup_logging()

    if args.schedule:
        schedule_mode(run_time=args.time, skip_ai=args.no_ai)
    else:
        run_analysis(skip_ai=args.no_ai)


if __name__ == "__main__":
    main()
