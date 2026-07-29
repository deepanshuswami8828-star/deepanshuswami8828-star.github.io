"""Build the multi-strategy PDF report.

Layout (landscape A4):
  1. Cover: instrument, timeframe, range, best strategy, method notes
  2. Ranked comparison table across all strategies (best row highlighted)
  3. Combined equity-curve chart
  4. Per strategy: metrics grid + equity/drawdown chart + per-regime table
     + full trade log (every trade with entry/exit, SL, target, P&L, reasons)

Note: ReportLab's core fonts have no rupee glyph, so money is labelled 'INR'.
"""
import io
import datetime as dt

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, Image)

from regime import by_regime

_ss = getSampleStyleSheet()
H1 = _ss["Title"]
H2 = ParagraphStyle("h2", parent=_ss["Heading2"], textColor=colors.HexColor("#0B3D91"))
BODY = _ss["Normal"]
SMALL = ParagraphStyle("small", parent=BODY, fontSize=6.5, leading=7.5)
NOTE = ParagraphStyle("note", parent=BODY, fontSize=8, textColor=colors.HexColor("#666666"))

BRAND = colors.HexColor("#0B3D91")
GREEN = colors.HexColor("#1B6B2E")
RED = colors.HexColor("#B01818")
BEST = colors.HexColor("#D3F9D8")
ZEBRA = colors.HexColor("#F1F3F5")


def _fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return "Inf" if v == float("inf") else f"{v:,.2f}"
    return str(v)


def _ts(x):
    t = pd.Timestamp(x)
    return t.strftime("%Y-%m-%d %H:%M") if (t.hour or t.minute) else t.strftime("%Y-%m-%d")


def _img(fig, width_mm=255):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    im = Image(buf)
    im.drawWidth = width_mm * mm
    im.drawHeight = width_mm * mm * (im.imageHeight / im.imageWidth)
    return im


def _combined_equity(results):
    fig, ax = plt.subplots(figsize=(11, 3.8))
    plotted = False
    for name, r in results.items():
        eq = r["equity"]
        if eq is not None and len(eq) > 1:
            ax.plot(eq.index, eq.values, linewidth=1.6, label=name)
            plotted = True
    ax.set_title("Equity Curves - All Strategies")
    ax.set_ylabel("Equity (INR)")
    ax.grid(alpha=0.3)
    if plotted:
        ax.legend(fontsize=8)
    return fig


def _equity_dd(name, eq):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 4.4), sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1]})
    a1.plot(eq.index, eq.values, color="#0B3D91", linewidth=1.6)
    a1.set_title(f"{name} - Equity & Drawdown")
    a1.set_ylabel("Equity (INR)")
    a1.grid(alpha=0.3)
    dd = eq - eq.cummax()
    a2.fill_between(dd.index, dd.values, 0, color="#B01818", alpha=0.35)
    a2.set_ylabel("Drawdown")
    a2.grid(alpha=0.3)
    return fig


def _comparison_table(results):
    header = ["Strategy", "Net P&L", "Return %", "Trades", "Win %", "PF", "R:R", "Max DD %", "Sharpe", "Expectancy"]
    ranked = sorted(results.items(), key=lambda kv: kv[1]["metrics"].get("net_pnl", -1e18), reverse=True)
    rows = [header]
    for name, r in ranked:
        m = r["metrics"]
        rows.append([name, _fmt(m.get("net_pnl")), _fmt(m.get("return_pct")), str(m.get("trades", "-")),
                     _fmt(m.get("win_rate")), _fmt(m.get("profit_factor")), _fmt(m.get("reward_risk")),
                     _fmt(m.get("max_drawdown_pct")), _fmt(m.get("sharpe")), _fmt(m.get("expectancy"))])
    t = Table(rows, colWidths=[120, 55, 48, 42, 40, 36, 36, 52, 45, 55], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
        ("BACKGROUND", (0, 1), (-1, 1), BEST),  # winner
    ]
    for r_idx in range(1, len(rows)):
        val = ranked[r_idx - 1][1]["metrics"].get("net_pnl", 0) or 0
        style.append(("TEXTCOLOR", (1, r_idx), (1, r_idx), GREEN if val >= 0 else RED))
    t.setStyle(TableStyle(style))
    return t, (ranked[0][0] if ranked else "-")


def _metrics_grid(m):
    order = [("Net P&L (INR)", "net_pnl"), ("Return %", "return_pct"), ("CAGR %", "cagr_pct"),
             ("Total Trades", "trades"), ("Win Rate %", "win_rate"), ("Profit Factor", "profit_factor"),
             ("Reward : Risk", "reward_risk"), ("Expectancy (INR)", "expectancy"), ("Sharpe", "sharpe"),
             ("Max Drawdown (INR)", "max_drawdown"), ("Max Drawdown %", "max_drawdown_pct"),
             ("Avg Win (INR)", "avg_win"), ("Avg Loss (INR)", "avg_loss"), ("Avg Trade (INR)", "avg_trade"),
             ("Largest Win", "largest_win"), ("Largest Loss", "largest_loss"),
             ("Max Consec Wins", "max_consec_wins"), ("Max Consec Losses", "max_consec_losses"),
             ("Total Charges (INR)", "total_charges")]
    pairs = [(lbl, _fmt(m.get(k))) for lbl, k in order]
    rows = [["Metric", "Value", "Metric", "Value"]]
    for i in range(0, len(pairs), 2):
        left = pairs[i]
        right = pairs[i + 1] if i + 1 < len(pairs) else ("", "")
        rows.append([left[0], left[1], right[0], right[1]])
    t = Table(rows, colWidths=[75, 55, 75, 55])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
    ]))
    return t


def _regime_table(trades):
    br = by_regime(trades)
    if br.empty:
        return Paragraph("No regime data.", NOTE)
    rows = [["Market Regime (at entry)", "Trades", "Net P&L (INR)", "Win %"]]
    for _, x in br.iterrows():
        rows.append([x["trend_regime"], str(int(x["trades"])), _fmt(x["net_pnl"]), _fmt(x["win_rate"])])
    t = Table(rows, colWidths=[80, 40, 60, 40])
    style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#495057")),
             ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
             ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
             ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA])]
    for i in range(1, len(rows)):
        val = br.iloc[i - 1]["net_pnl"]
        style.append(("TEXTCOLOR", (2, i), (2, i), GREEN if val >= 0 else RED))
    t.setStyle(TableStyle(style))
    return t


def _trades_table(trades):
    if trades.empty:
        return Paragraph("No trades taken.", NOTE)
    header = ["Entry", "Exit", "Dir", "Entry", "Exit", "Qty", "SL", "Target",
              "Net P&L", "Ret%", "Regime", "Entry Reason", "Exit Reason"]
    rows = [header]
    for _, t in trades.iterrows():
        rows.append([
            _ts(t["entry_time"]), _ts(t["exit_time"]), t["direction"],
            f"{t['entry']:.2f}", f"{t['exit']:.2f}", str(int(t["qty"])),
            f"{t['sl']:.2f}", f"{t['target']:.2f}", f"{t['net_pnl']:,.0f}",
            f"{t['return_pct']:.2f}", t.get("trend_regime", "-"),
            Paragraph(str(t["entry_reason"]), SMALL), Paragraph(str(t["exit_reason"]), SMALL),
        ])
    tbl = Table(rows, repeatRows=1,
                colWidths=[34, 34, 16, 26, 26, 20, 26, 26, 30, 22, 40, 118, 62])
    style = [("BACKGROUND", (0, 0), (-1, 0), BRAND), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
             ("FONTSIZE", (0, 0), (-1, -1), 6.5), ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
             ("ALIGN", (3, 0), (9, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA])]
    for i in range(1, len(rows)):
        pnl = trades.iloc[i - 1]["net_pnl"]
        style.append(("TEXTCOLOR", (8, i), (8, i), GREEN if pnl >= 0 else RED))
    tbl.setStyle(TableStyle(style))
    return tbl


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.grey)
    canvas.drawString(15 * mm, 8 * mm, "AI Trading Research Platform - backtest report (research only, not investment advice)")
    canvas.drawRightString(landscape(A4)[0] - 15 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_report(path, symbol, interval, df, results):
    doc = SimpleDocTemplate(path, pagesize=landscape(A4),
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f"Backtest - {symbol}")
    story = []

    # --- cover ---
    story.append(Paragraph("Multi-Strategy Backtest Report", H1))
    story.append(Spacer(1, 6))
    span = f"{df.index.min().date()} to {df.index.max().date()}" if len(df) else "-"
    meta = (f"<b>Instrument:</b> {symbol} &nbsp;&nbsp; <b>Timeframe:</b> {interval} &nbsp;&nbsp; "
            f"<b>Period:</b> {span} &nbsp;&nbsp; <b>Bars:</b> {len(df)} &nbsp;&nbsp; "
            f"<b>Generated:</b> {dt.datetime.now():%Y-%m-%d %H:%M}")
    story.append(Paragraph(meta, BODY))
    story.append(Spacer(1, 10))

    comp, best = _comparison_table(results)
    story.append(Paragraph("Strategy Leaderboard (ranked by net P&L)", H2))
    story.append(comp)
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Best performer this run:</b> {best}. Green row = top by net P&L. "
                           "Remember: a winner on one stock / period can be curve-fit noise - "
                           "confirm out-of-sample before trusting it.", NOTE))
    story.append(Spacer(1, 10))
    story.append(_img(_combined_equity(results)))
    story.append(PageBreak())

    # --- per strategy ---
    ranked = sorted(results.items(), key=lambda kv: kv[1]["metrics"].get("net_pnl", -1e18), reverse=True)
    for name, r in ranked:
        trades, eq, m = r["trades"], r["equity"], r["metrics"]
        story.append(Paragraph(name, H2))
        story.append(_metrics_grid(m))
        story.append(Spacer(1, 8))
        if eq is not None and len(eq) > 1:
            story.append(_img(_equity_dd(name, eq)))
            story.append(Spacer(1, 8))
        story.append(Paragraph("Performance by market regime", H2))
        story.append(_regime_table(trades))
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"Trade log ({0 if trades is None or trades.empty else len(trades)} trades)", H2))
        story.append(_trades_table(trades if trades is not None else pd.DataFrame()))
        story.append(PageBreak())

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return path
