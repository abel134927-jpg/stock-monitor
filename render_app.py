"""
Render 部署版本 — 只讀取 results.json 並提供 API
不執行任何分析，等待本地機器推送最新結果
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("render_app")

RESULTS_FILE = Path("results.json")


def _load_results():
    if not RESULTS_FILE.exists():
        return None
    try:
        with open(RESULTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"讀取 results.json 失敗: {e}")
        return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze")
def api_analyze():
    data = _load_results()
    if data is None:
        return jsonify({"error": "no_data", "message": "尚無分析結果，請等待本地機器推送"}), 503
    try:
        generated = datetime.strptime(data.get("generated_at", ""), "%Y-%m-%d %H:%M:%S")
        cache_age = int((datetime.now() - generated).total_seconds())
    except Exception:
        cache_age = 0
    return jsonify({"cached": True, "cache_age": cache_age, **data})


@app.route("/api/health")
def api_health():
    data = _load_results()
    return jsonify({
        "status":      "ok",
        "cached":      data is not None,
        "analysing":   False,
        "last_update": data.get("generated_at") if data else None,
        "next_auto":   "由本地機器每日 16:30 自動更新",
        "watchlist":   len(data.get("signals", [])) if data else 0,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
