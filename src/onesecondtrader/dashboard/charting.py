"""
Chart image generation for round-trip trade visualization.

Generates PNG images showing price action, fills, P&L watermarks, and indicators
for individual round-trip trades.
"""

from __future__ import annotations

import io
import json
import math
import os
import sqlite3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd

from .db import get_runs_db_path


def generate_chart_image(
    run_id: str,
    symbol: str,
    start_ns: int,
    end_ns: int,
    direction: str,
    pnl: float,
) -> bytes:
    """
    Generate a PNG chart image for a round-trip trade.

    Renders a multi-panel chart showing:
    - P&L panel with unrealized P&L range and high/low watermarks
    - Price panel with OHLC bars, overlay indicators, and fill markers
    - Additional panels for non-overlay indicators grouped by tag

    Parameters:
        run_id:
            Unique identifier of the backtest run.
        symbol:
            Instrument symbol for the trade.
        start_ns:
            Entry timestamp in nanoseconds.
        end_ns:
            Exit timestamp in nanoseconds.
        direction:
            Trade direction, either "LONG" or "SHORT".
        pnl:
            Net profit/loss for the trade.

    Returns:
        PNG image bytes, or empty bytes if no data is available.
    """
    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        return b""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    padding_bars = 100

    cursor.execute(
        """
        SELECT ts_event_ns, open, high, low, close, bar_period, indicators
        FROM bars_processed
        WHERE run_id = ? AND symbol = ? AND ts_event_ns < ?
        ORDER BY ts_event_ns DESC
        LIMIT ?
        """,
        (run_id, symbol, start_ns, padding_bars),
    )
    before_rows = cursor.fetchall()[::-1]

    cursor.execute(
        """
        SELECT ts_event_ns, open, high, low, close, bar_period, indicators
        FROM bars_processed
        WHERE run_id = ? AND symbol = ? AND ts_event_ns >= ? AND ts_event_ns <= ?
        ORDER BY ts_event_ns
        """,
        (run_id, symbol, start_ns, end_ns),
    )
    trade_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT ts_event_ns, open, high, low, close, bar_period, indicators
        FROM bars_processed
        WHERE run_id = ? AND symbol = ? AND ts_event_ns > ?
        ORDER BY ts_event_ns
        LIMIT ?
        """,
        (run_id, symbol, end_ns, padding_bars),
    )
    after_rows = cursor.fetchall()

    bar_rows = before_rows + trade_rows + after_rows
    bar_period = bar_rows[0][5] if bar_rows else "DAY"

    cursor.execute(
        """
        SELECT ts_broker_ns, side, quantity_filled, fill_price
        FROM fills
        WHERE run_id = ? AND symbol = ? AND ts_broker_ns >= ? AND ts_broker_ns <= ?
        ORDER BY ts_broker_ns
        """,
        (run_id, symbol, start_ns, end_ns),
    )
    fill_rows = cursor.fetchall()
    conn.close()

    if not bar_rows:
        return b""

    data = pd.DataFrame(
        bar_rows,
        columns=[
            "ts_event",
            "open",
            "high",
            "low",
            "close",
            "bar_period",
            "indicators",
        ],
    )
    data["ts_event"] = pd.to_datetime(data["ts_event"], unit="ns")

    indicator_series: dict[str, list[float]] = {}
    indicator_tags: dict[str, int] = {}
    for idx in range(len(data)):
        row = data.iloc[idx]
        indicators = json.loads(row["indicators"]) if row["indicators"] else {}
        for name, value in indicators.items():
            if name not in indicator_series:
                indicator_series[name] = [math.nan] * len(data)
                tag = int(name[:2]) if name[:2].isdigit() else 99
                indicator_tags[name] = tag
            indicator_series[name][idx] = value if value == value else math.nan

    overlay_indicators = {
        k: v for k, v in indicator_series.items() if indicator_tags.get(k, 99) == 0
    }
    subplot_tags = sorted(set(t for t in indicator_tags.values() if 1 <= t <= 98))
    subplot_indicators = {
        tag: {k: v for k, v in indicator_series.items() if indicator_tags.get(k) == tag}
        for tag in subplot_tags
    }

    entry_time = pd.to_datetime(start_ns, unit="ns")
    exit_time = pd.to_datetime(end_ns, unit="ns")

    fills = []
    for row in fill_rows:
        fills.append(
            {
                "ts_event": pd.to_datetime(row[0], unit="ns"),
                "side": row[1],
                "quantity": row[2],
                "price": row[3],
            }
        )

    highlight_start = (
        data[data["ts_event"] >= entry_time].index[0]
        if len(data[data["ts_event"] >= entry_time]) > 0
        else 0
    )
    highlight_end = (
        data[data["ts_event"] <= exit_time].index[-1]
        if len(data[data["ts_event"] <= exit_time]) > 0
        else len(data) - 1
    )

    num_subplots = 2 + len(subplot_tags)
    height_ratios = [1, 3] + [1] * len(subplot_tags)
    fig_height = 8 + 2 * len(subplot_tags)
    fig, axes = plt.subplots(
        num_subplots,
        1,
        figsize=(14, fig_height),
        sharex=True,
        gridspec_kw={"height_ratios": height_ratios},
    )
    if num_subplots == 2:
        axes = [axes[0], axes[1]]
    ax_pnl = axes[0]
    ax_main = axes[1]
    ax_indicators = axes[2:] if len(axes) > 2 else []

    entry_price = fills[0]["price"] if fills else 0
    fill_direction = fills[0]["side"] if fills else "BUY"

    pos_indices = []
    pnl_high_series = []
    pnl_low_series = []
    hwm_series = []
    low_watermark_series = []
    running_hwm = 0
    running_lwm = 0

    for i in range(len(data)):
        ts = data["ts_event"].iloc[i]
        bar_high = data["high"].iloc[i]
        bar_low = data["low"].iloc[i]
        if ts >= entry_time and ts <= exit_time:
            if fill_direction == "BUY":
                pnl_at_high = bar_high - entry_price
                pnl_at_low = bar_low - entry_price
            else:
                pnl_at_high = entry_price - bar_low
                pnl_at_low = entry_price - bar_high
            running_hwm = max(running_hwm, pnl_at_high)
            running_lwm = min(running_lwm, pnl_at_low)
            pos_indices.append(i)
            pnl_high_series.append(pnl_at_high)
            pnl_low_series.append(pnl_at_low)
            hwm_series.append(running_hwm)
            low_watermark_series.append(running_lwm)

    if pos_indices:
        ax_pnl.fill_between(
            pos_indices,
            pnl_low_series,
            pnl_high_series,
            color="blue",
            alpha=0.3,
            label="Unrealized P&L",
        )
        ax_pnl.plot(
            pos_indices,
            hwm_series,
            color="green",
            linewidth=1.5,
            label="High Watermark",
            alpha=0.8,
        )
        ax_pnl.plot(
            pos_indices,
            low_watermark_series,
            color="red",
            linewidth=1.5,
            label="Low Watermark",
            alpha=0.8,
        )
    ax_pnl.axhline(y=0, color="black", linestyle="-", alpha=0.5, linewidth=0.8)
    ax_pnl.set_ylabel("P&L", fontsize=10)
    ax_pnl.grid(True, alpha=0.3)
    ax_pnl.legend(loc="upper left", fontsize=8)

    for i in range(len(data)):
        ax_main.plot(
            [i, i],
            [data["low"].iloc[i], data["high"].iloc[i]],
            color="black",
            linewidth=0.8,
            alpha=0.7,
        )
        ax_main.plot(
            [i], [data["close"].iloc[i]], marker="_", color="blue", markersize=3
        )

    colors = ["orange", "purple", "cyan", "magenta", "brown", "pink", "olive", "teal"]
    for idx, (name, values) in enumerate(overlay_indicators.items()):
        display_name = name[3:] if len(name) > 3 else name
        color = colors[idx % len(colors)]
        ax_main.plot(
            range(len(values)),
            values,
            label=display_name,
            linewidth=1.2,
            alpha=0.8,
            color=color,
        )
    if overlay_indicators:
        ax_main.legend(loc="upper left", fontsize=8)

    for ax_idx, tag in enumerate(subplot_tags):
        ax = ax_indicators[ax_idx]
        tag_indicators = subplot_indicators[tag]
        for idx, (name, values) in enumerate(tag_indicators.items()):
            display_name = name[3:] if len(name) > 3 else name
            color = colors[idx % len(colors)]
            ax.plot(
                range(len(values)),
                values,
                label=display_name,
                linewidth=1.2,
                alpha=0.8,
                color=color,
            )
        ax.set_ylabel(f"Tag {tag}", fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper left", fontsize=8)

    all_axes = [ax_pnl, ax_main] + ax_indicators
    if 0 <= highlight_start < len(data) and 0 <= highlight_end < len(data):
        for ax in all_axes:
            y_min, y_max = ax.get_ylim()
            rect = Rectangle(
                (highlight_start, y_min),
                highlight_end - highlight_start,
                y_max - y_min,
                facecolor="lightblue",
                alpha=0.2,
            )
            ax.add_patch(rect)

    ax_main.set_ylabel("Price", fontsize=10)
    ax_main.grid(True, alpha=0.3)

    ts_to_idx = {ts: i for i, ts in enumerate(data["ts_event"])}
    for fill in fills:
        fill_idx = ts_to_idx.get(fill["ts_event"])
        if fill_idx is None:
            closest_idx = (data["ts_event"] - fill["ts_event"]).abs().argmin()
            fill_idx = closest_idx
        marker = "^" if fill["side"] == "BUY" else "v"
        color = "green" if fill["side"] == "BUY" else "red"
        qty = fill.get("quantity", 1)
        size = 120 * min(3.0, max(0.5, qty))
        ax_main.scatter(
            fill_idx,
            fill["price"],
            marker=marker,
            color=color,
            s=size,
            edgecolors="black",
            linewidth=1,
            zorder=5,
            alpha=0.8,
        )
        y_lim = ax_main.get_ylim()
        offset_y = (y_lim[1] - y_lim[0]) * 0.02
        ax_main.annotate(
            f"{qty}",
            (fill_idx, fill["price"] + offset_y),
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7),
        )

    label = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAK-EVEN"
    duration_secs = (exit_time - entry_time).total_seconds()
    if bar_period == "SECOND":
        duration_str = f"{duration_secs:.0f}s"
    elif bar_period == "MINUTE":
        duration_str = f"{duration_secs / 60:.0f}min"
    elif bar_period == "HOUR":
        duration_str = f"{duration_secs / 3600:.0f}h"
    else:
        duration_str = f"{duration_secs / 86400:.0f}d"
    ax_pnl.set_title(
        f"{symbol} - {direction} - {label} - P&L: ${pnl:.2f} - Duration: {duration_str}",
        fontsize=14,
    )

    num_bars = len(data)
    tick_interval = max(1, num_bars // 10)
    tick_positions = list(range(0, num_bars, tick_interval))
    tick_labels = [data["ts_event"].iloc[i].strftime("%m/%d") for i in tick_positions]
    for ax in all_axes:
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels)

    plt.xticks(rotation=45, fontsize=9)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=500, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    return buf.read()
