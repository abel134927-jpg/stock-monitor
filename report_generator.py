"""
報告生成模組
提供三種格式：
  1. 終端純文字（Console / 存檔）
  2. HTML（Email）
  3. 純文字摘要（LINE Notify）
"""
from datetime import date as dt_date
from strategy import SignalResult


# ============================================================
# 分類輔助
# ============================================================

def _split(signals: list[SignalResult]) -> dict:
    return {
        "buy_a":    [s for s in signals if s.action == "買進" and s.confidence == "A"],
        "buy_b":    [s for s in signals if s.action == "買進" and s.confidence == "B"],
        "buy_c":    [s for s in signals if s.action == "買進" and s.confidence == "C"],
        "watching": [s for s in signals if s.action == "觀察中"],
        "sell":     [s for s in signals if s.action == "賣出"],
        "hold":     [s for s in signals if s.action == "觀望"],
    }


# ============================================================
# 終端純文字報告
# ============================================================

def generate_text(signals: list[SignalResult], report_date: str = None) -> str:
    if not report_date:
        report_date = str(dt_date.today())

    g = _split(signals)
    lines = [
        "=" * 58,
        f"   個股監測日報  {report_date}",
        "=" * 58,
        "",
    ]

    def fmt_signal(s: SignalResult) -> list[str]:
        chg = f"+{s.change_pct:.2f}%" if s.change_pct >= 0 else f"{s.change_pct:.2f}%"
        block = [
            f"  {s.action_emoji} {s.name} ({s.code})   {chg}",
            f"     收盤:{s.close:.2f}  量比:{s.volume_ratio:.2f}x  RSI:{s.rsi:.1f}  KD:{s.k_val:.0f}/{s.d_val:.0f}",
        ]
        if s.action in ("買進", "觀察中"):
            aux = " | ".join(s.aux_conditions) if s.aux_conditions else "無"
            block.append(f"     核心:{s.core_condition}  輔助:{aux}")
        if s.action == "買進":
            block.append(f"     買入:{s.buy_price:.2f}  停損:{s.stop_loss:.2f}  目標:{s.target_price:.2f}")
        if s.action == "觀察中":
            block.append(f"     (突破幅度未達3%，持續觀察)")
        if s.action == "賣出":
            block.append(f"     原因: {' | '.join(s.sell_reasons)}")
        if s.ai_analysis:
            block.append(f"     --- AI 分析 ---")
            for ln in s.ai_analysis.strip().split("\n"):
                if ln.strip():
                    block.append(f"     {ln.strip()}")
        block.append("")
        return block

    sections = [
        ("【A類 - 高確信度買進】", g["buy_a"]),
        ("【B類 - 中確信度買進】", g["buy_b"]),
        ("【C類 - 低確信度買進】", g["buy_c"]),
        ("【觀察中 - 突破幅度不足3%】", g["watching"]),
        ("【賣出警示】", g["sell"]),
    ]

    for title, group in sections:
        if group:
            lines.append(title)
            lines.append("-" * 40)
            for s in group:
                lines.extend(fmt_signal(s))

    if g["hold"]:
        hold_names = "  ".join([f"{s.name}({s.code})" for s in g["hold"]])
        lines.append("【今日觀望】")
        lines.append(f"  {hold_names}")
        lines.append("")

    total = len(signals)
    active = sum(len(g[k]) for k in ("buy_a", "buy_b", "buy_c", "watching", "sell"))
    lines += [
        "=" * 58,
        f"  監測:{total}支  有訊號:{active}支  "
        f"買進:A{len(g['buy_a'])} B{len(g['buy_b'])} C{len(g['buy_c'])}  賣出:{len(g['sell'])}",
        "=" * 58,
    ]
    return "\n".join(lines)


# ============================================================
# HTML 報告（Email 用）
# ============================================================

def generate_html(signals: list[SignalResult], report_date: str = None) -> str:
    if not report_date:
        report_date = str(dt_date.today())

    g = _split(signals)
    total = len(signals)
    active = sum(len(g[k]) for k in ("buy_a", "buy_b", "buy_c", "watching", "sell"))

    _card_bg = {
        ("買進", "A"): "#e8f5e9",
        ("買進", "B"): "#f1f8e9",
        ("買進", "C"): "#f9fbe7",
        ("賣出", "-"): "#fce4ec",
        ("觀察中", "-"): "#fff3e0",
    }

    def signal_card(s: SignalResult) -> str:
        bg = _card_bg.get((s.action, s.confidence), "#f5f5f5")
        chg_color = "#2e7d32" if s.change_pct >= 0 else "#c62828"
        chg_str = f"+{s.change_pct:.2f}%" if s.change_pct >= 0 else f"{s.change_pct:.2f}%"

        # 輔助條件 badges
        aux_html = ""
        if s.aux_conditions:
            badges = "".join(
                f'<span style="background:#388e3c;color:#fff;padding:2px 10px;border-radius:12px;'
                f'font-size:12px;margin-right:4px;">{c}</span>'
                for c in s.aux_conditions
            )
            aux_html = f'<div style="margin-top:5px;">輔助: {badges}</div>'

        # 價格點位
        price_html = ""
        if s.action == "買進":
            price_html = f"""
            <div style="margin-top:8px;padding:8px 12px;background:#fff;border-radius:6px;
                        display:flex;gap:20px;font-size:14px;">
                <span>買入 <b>{s.buy_price:.2f}</b></span>
                <span>停損 <b style="color:#c62828;">{s.stop_loss:.2f}</b></span>
                <span>目標 <b style="color:#2e7d32;">{s.target_price:.2f}</b></span>
            </div>"""

        # 賣出原因
        sell_html = ""
        if s.action == "賣出":
            sell_html = (
                f'<div style="color:#c62828;margin-top:6px;font-size:13px;">'
                f'警示: {" | ".join(s.sell_reasons)}</div>'
            )

        # 觀察中提示
        watch_html = ""
        if s.action == "觀察中":
            watch_html = (
                '<div style="color:#e65100;margin-top:4px;font-size:12px;">'
                '突破幅度未達 3%，建議持續觀察</div>'
            )

        # AI 分析
        ai_html = ""
        if s.ai_analysis:
            ai_content = s.ai_analysis.replace("\n", "<br>")
            ai_html = f"""
            <div style="margin-top:10px;padding:10px;background:#f8f9fa;
                        border-left:3px solid #1565c0;font-size:13px;border-radius:0 6px 6px 0;">
                <b style="color:#1565c0;">AI 分析</b><br>{ai_content}
            </div>"""

        return f"""
        <div style="background:{bg};border:1px solid #e0e0e0;border-radius:10px;
                    padding:14px 16px;margin:8px 0;box-shadow:0 1px 3px rgba(0,0,0,.08);">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:17px;font-weight:700;">
                    {s.action_emoji} {s.name}
                    <span style="font-size:13px;color:#666;font-weight:normal;">({s.code})</span>
                </span>
                <span style="font-size:17px;font-weight:700;color:{chg_color};">{chg_str}</span>
            </div>
            <div style="color:#555;font-size:13px;margin-top:5px;">
                收盤 <b>{s.close:.2f}</b> &nbsp;|&nbsp;
                量比 <b>{s.volume_ratio:.2f}x</b> &nbsp;|&nbsp;
                RSI <b>{s.rsi:.1f}</b> &nbsp;|&nbsp;
                KD <b>{s.k_val:.0f}/{s.d_val:.0f}</b> &nbsp;|&nbsp;
                MACD柱 <b>{s.macd_hist:+.4f}</b>
            </div>
            <div style="color:#555;font-size:13px;">
                均線: 5MA={s.ma5:.2f} | 20MA={s.ma20:.2f} | 60MA={s.ma60:.2f}
            </div>
            <div style="font-size:13px;margin-top:4px;">
                核心訊號: <b>{s.core_condition}</b> &nbsp;
                箱體: {s.box_bottom:.2f} ~ {s.box_top:.2f}
            </div>
            {aux_html}{price_html}{sell_html}{watch_html}{ai_html}
        </div>"""

    def section_block(title: str, color: str, group: list) -> str:
        if not group:
            return ""
        cards = "".join(signal_card(s) for s in group)
        return f"""
        <div style="margin-bottom:28px;">
            <h3 style="color:{color};border-bottom:2px solid {color};
                       padding-bottom:6px;margin-bottom:0;">{title}</h3>
            {cards}
        </div>"""

    hold_html = ""
    if g["hold"]:
        names = "、".join(f"{s.name}({s.code})" for s in g["hold"])
        hold_html = f'<p style="color:#9e9e9e;font-size:13px;"><b>今日觀望：</b>{names}</p>'

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>個股監測日報 {report_date}</title>
</head>
<body style="font-family:'Microsoft JhengHei',Arial,sans-serif;background:#f0f2f5;
             margin:0;padding:20px;">
<div style="max-width:760px;margin:0 auto;">

  <!-- 標題 -->
  <div style="background:linear-gradient(135deg,#1a237e,#1565c0);color:#fff;
              padding:24px;border-radius:14px;text-align:center;margin-bottom:24px;">
    <h1 style="margin:0;font-size:24px;letter-spacing:2px;">個股監測日報</h1>
    <p style="margin:8px 0 0;opacity:.85;font-size:15px;">
      {report_date} &nbsp;|&nbsp; 監測 {total} 支 &nbsp;|&nbsp; 有訊號 {active} 支
    </p>
  </div>

  {section_block("A類 — 高確信度買進", "#2e7d32", g["buy_a"])}
  {section_block("B類 — 中確信度買進", "#558b2f", g["buy_b"])}
  {section_block("C類 — 低確信度買進", "#f9a825", g["buy_c"])}
  {section_block("觀察中（突破幅度不足 3%）", "#e65100", g["watching"])}
  {section_block("賣出警示", "#b71c1c", g["sell"])}

  {hold_html}

  <div style="text-align:center;color:#bbb;font-size:12px;margin-top:24px;
              border-top:1px solid #e0e0e0;padding-top:16px;">
    本報告由自動化系統生成，僅供技術分析參考，不構成投資建議。<br>
    投資有風險，操作須謹慎。
  </div>
</div>
</body>
</html>"""


# ============================================================
# LINE Notify 純文字摘要
# ============================================================

def generate_line_summary(signals: list[SignalResult], report_date: str = None) -> str:
    if not report_date:
        report_date = str(dt_date.today())

    g = _split(signals)
    lines = [f"\n個股監測日報 {report_date}"]

    def fmt_buy(s: SignalResult) -> str:
        chg = f"+{s.change_pct:.2f}%" if s.change_pct >= 0 else f"{s.change_pct:.2f}%"
        return (
            f"  {s.action_emoji}{s.name} {s.close:.2f}({chg})\n"
            f"     停損:{s.stop_loss:.2f} 目標:{s.target_price:.2f}"
        )

    if g["buy_a"]:
        lines.append("\nA類買進 (高確信度):")
        lines.extend(fmt_buy(s) for s in g["buy_a"])

    if g["buy_b"]:
        lines.append("\nB類買進 (中確信度):")
        lines.extend(fmt_buy(s) for s in g["buy_b"])

    if g["buy_c"]:
        lines.append("\nC類買進 (低確信度):")
        for s in g["buy_c"]:
            chg = f"+{s.change_pct:.2f}%" if s.change_pct >= 0 else f"{s.change_pct:.2f}%"
            lines.append(f"  {s.action_emoji}{s.name} {s.close:.2f}({chg})")

    if g["watching"]:
        lines.append("\n觀察中:")
        for s in g["watching"]:
            lines.append(f"  👀{s.name} {s.close:.2f} (突破幅度不足)")

    if g["sell"]:
        lines.append("\n賣出警示:")
        for s in g["sell"]:
            lines.append(f"  🔴{s.name} {s.close:.2f} | {' '.join(s.sell_reasons)}")

    if not any([g["buy_a"], g["buy_b"], g["buy_c"], g["watching"], g["sell"]]):
        lines.append("\n今日無明顯訊號，建議觀望。")

    return "\n".join(lines)
