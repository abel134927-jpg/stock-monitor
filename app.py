"""
港股監測系統 — Flask Web 應用

啟動方式：
  python app.py

開啟瀏覽器：
  http://localhost:5000

排程：
  每日 16:30 (港股收盤後) 自動抓取數據更新快取
  使用者隨時開網站都能看到最新結果
"""
import dataclasses
import json
import logging
import subprocess
import threading
import schedule
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request

from config import WATCHLIST, DATA_PERIOD, DATA_INTERVAL, WEB_HOST, WEB_PORT, CACHE_TTL
from data_fetcher import fetch_all_stocks
from indicators import calculate_all
from strategy import classify
from ai_analyzer import batch_analyze

# ── 初始化 ────────────────────────────────────────────────────
app = Flask(__name__)

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/{datetime.now().strftime('%Y-%m-%d')}.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("app")

# 快取（含分析中旗標，避免同時觸發兩次分析）
_cache: dict = {"data": None, "timestamp": None, "analysing": False}
_lock = threading.Lock()


# ── 分析核心 ──────────────────────────────────────────────────

def _signal_to_dict(signal, price_history: list, date_history: list) -> dict:
    d = dataclasses.asdict(signal)
    d["label"] = signal.label
    d["action_emoji"] = signal.action_emoji
    d["price_history"] = [round(float(p), 3) for p in price_history]
    d["date_history"] = date_history
    return d


def _run_analysis() -> dict:
    """完整分析流程，回傳可直接 jsonify 的 dict"""
    logger.info("=== 開始分析 ===")

    stock_data = fetch_all_stocks(WATCHLIST, DATA_PERIOD, DATA_INTERVAL)
    if not stock_data:
        raise RuntimeError("所有股票數據均抓取失敗，請確認網路與股票代號")

    raw: list[tuple] = []
    for code, (name, df) in stock_data.items():
        try:
            df_ind = calculate_all(df)
            signal = classify(code, name, df_ind)
            ph = [float(v) for v in df_ind["Close"].tail(30)]
            dh = [str(d.date()) for d in df_ind.index[-30:]]
            raw.append((signal, ph, dh))
        except Exception as e:
            logger.error(f"[{code}] 分析失敗: {e}", exc_info=True)

    action_order = {"買進": 0, "觀察中": 1, "賣出": 2, "觀望": 3}
    conf_order   = {"A": 0, "B": 1, "C": 2, "-": 9}
    raw.sort(key=lambda x: (
        action_order.get(x[0].action, 9),
        conf_order.get(x[0].confidence, 9),
    ))

    signal_objs = [x[0] for x in raw]
    signal_objs = batch_analyze(signal_objs)

    signals_list = [_signal_to_dict(sig, ph, dh) for sig, ph, dh in raw]

    summary = {
        "total":    len(signals_list),
        "buy_a":    sum(1 for s in signals_list if s["action"] == "買進" and s["confidence"] == "A"),
        "buy_b":    sum(1 for s in signals_list if s["action"] == "買進" and s["confidence"] == "B"),
        "buy_c":    sum(1 for s in signals_list if s["action"] == "買進" and s["confidence"] == "C"),
        "watching": sum(1 for s in signals_list if s["action"] == "觀察中"),
        "sell":     sum(1 for s in signals_list if s["action"] == "賣出"),
        "hold":     sum(1 for s in signals_list if s["action"] == "觀望"),
    }

    logger.info(f"=== 分析完成 {summary} ===")
    return {
        "date":         datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market":       "港股 (HKEX)",
        "summary":      summary,
        "signals":      signals_list,
    }


def _save_and_push(data: dict):
    """儲存 results.json 並推送到 GitHub（讓 Render 取得最新結果）"""
    try:
        work_dir = str(Path(__file__).parent)
        with open(Path(work_dir) / "results.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("results.json 已儲存")

        subprocess.run(["git", "add", "results.json"], cwd=work_dir, capture_output=True)
        commit = subprocess.run(
            ["git", "commit", "-m", f"Update results {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
            cwd=work_dir, capture_output=True
        )
        if commit.returncode == 0:
            subprocess.run(["git", "push"], cwd=work_dir, capture_output=True)
            logger.info("results.json 已推送到 GitHub")
        else:
            logger.info("results.json 無變化，略過推送")
    except Exception as e:
        logger.error(f"推送 results.json 失敗: {e}")


def _refresh_cache():
    """更新快取（可從排程或 API 觸發）"""
    with _lock:
        if _cache["analysing"]:
            logger.info("分析進行中，略過重複觸發")
            return
        _cache["analysing"] = True

    try:
        data = _run_analysis()
        with _lock:
            _cache["data"] = data
            _cache["timestamp"] = datetime.now()
        logger.info("快取已更新")
        threading.Thread(target=_save_and_push, args=(data,), daemon=True).start()
    except Exception as e:
        logger.error(f"分析失敗: {e}", exc_info=True)
    finally:
        with _lock:
            _cache["analysing"] = False


# ── 每日排程 ──────────────────────────────────────────────────

def _scheduler_thread():
    """
    背景排程執行緒
    港股收盤時間 16:00 HKT，16:30 執行確保數據已落地
    週一至週五執行，週末跳過
    """
    schedule.every().monday.at("16:30").do(lambda: threading.Thread(target=_refresh_cache, daemon=True).start())
    schedule.every().tuesday.at("16:30").do(lambda: threading.Thread(target=_refresh_cache, daemon=True).start())
    schedule.every().wednesday.at("16:30").do(lambda: threading.Thread(target=_refresh_cache, daemon=True).start())
    schedule.every().thursday.at("16:30").do(lambda: threading.Thread(target=_refresh_cache, daemon=True).start())
    schedule.every().friday.at("16:30").do(lambda: threading.Thread(target=_refresh_cache, daemon=True).start())

    logger.info("每日排程已啟動 — 港股交易日 16:30 自動更新")
    while True:
        schedule.run_pending()
        time.sleep(30)


# ── Flask 路由 ────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze")
def api_analyze():
    """
    GET /api/analyze         → 回傳快取（若快取存在且未過期）
    GET /api/analyze?refresh=1 → 強制重新分析
    """
    force = request.args.get("refresh") == "1"

    with _lock:
        now       = datetime.now()
        cache_age = (now - _cache["timestamp"]).total_seconds() if _cache["timestamp"] else float("inf")
        cache_hit = (not force) and (_cache["data"] is not None) and (cache_age < CACHE_TTL)
        analysing = _cache["analysing"]

    if cache_hit:
        logger.info(f"快取命中 (已快取 {int(cache_age//60)}分{int(cache_age%60)}秒)")
        return jsonify({"cached": True, "cache_age": int(cache_age), **_cache["data"]})

    if analysing:
        return jsonify({"error": "analysing", "message": "分析進行中，請稍後重試"}), 202

    # 在背景執行分析，立即返回 202，不阻塞 worker
    threading.Thread(target=_refresh_cache, daemon=True).start()
    return jsonify({"error": "analysing", "message": "分析已啟動，請稍後重試"}), 202


@app.route("/api/health")
def api_health():
    with _lock:
        ts  = _cache["timestamp"]
        has = _cache["data"] is not None
        ing = _cache["analysing"]
    next_run = str(schedule.next_run()) if schedule.jobs else "尚未設定"
    return jsonify({
        "status":      "ok",
        "cached":      has,
        "analysing":   ing,
        "last_update": ts.strftime("%Y-%m-%d %H:%M:%S") if ts else None,
        "next_auto":   next_run,
        "watchlist":   len(WATCHLIST),
    })


# ── 啟動背景執行緒（直接執行或 gunicorn 都適用）─────────────────

logger.info("=" * 50)
logger.info("  港股監測系統啟動")
logger.info("  每日 16:30 自動更新 (港股交易日)")
logger.info("=" * 50)

threading.Thread(target=_scheduler_thread, daemon=True).start()
threading.Thread(target=_refresh_cache, daemon=True).start()


if __name__ == "__main__":
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False, threaded=True)
