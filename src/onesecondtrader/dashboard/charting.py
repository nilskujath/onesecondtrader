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


def _draw_ohlc_bars(ax, data, x_values, chart_type: str, bar_width) -> None:
    """
    Draw OHLC bars on the given axis based on chart type.

    Parameters:
        ax: Matplotlib axis to draw on.
        data: DataFrame with open, high, low, close columns.
        x_values: X-axis values for each bar.
        chart_type: One of 'candlestick', 'oc_bars', 'c_bars', 'bars'.
        bar_width: Width of bars (for candlesticks).
    """
    for i in range(len(data)):
        x = x_values[i]
        o = data["open"].iloc[i]
        h = data["high"].iloc[i]
        low = data["low"].iloc[i]
        c = data["close"].iloc[i]

        if chart_type == "candlestick":
            color = "black" if c <= o else "white"
            edge_color = "black"
            body_bottom = min(o, c)
            body_height = abs(c - o)
            if isinstance(bar_width, pd.Timedelta):
                rect_width = bar_width * 0.8  # type: ignore[assignment]
            else:
                rect_width = bar_width * 0.8
            ax.plot([x, x], [low, h], color="black", linewidth=0.8, alpha=0.7)
            rect = Rectangle(
                (x - rect_width / 2, body_bottom),
                rect_width,  # type: ignore[arg-type]
                body_height if body_height > 0 else 0.001,
                facecolor=color,
                edgecolor=edge_color,
                linewidth=0.5,
            )
            ax.add_patch(rect)
        elif chart_type == "oc_bars":
            ax.plot([x, x], [low, h], color="black", linewidth=0.8, alpha=0.7)
            if isinstance(bar_width, pd.Timedelta):
                tick_offset = bar_width * 0.3
            else:
                tick_offset = 0.3  # type: ignore[assignment]
            ax.plot(
                [x - tick_offset, x], [o, o], color="black", linewidth=0.8, alpha=0.7
            )
            ax.plot(
                [x, x + tick_offset], [c, c], color="blue", linewidth=0.8, alpha=0.7
            )
        elif chart_type == "c_bars":
            ax.plot([x, x], [low, h], color="black", linewidth=0.8, alpha=0.7)
            ax.plot([x], [c], marker="_", color="blue", markersize=3)
        else:
            ax.plot([x, x], [low, h], color="black", linewidth=0.8, alpha=0.7)


def generate_chart_image(
    run_id: str,
    symbol: str,
    start_ns: int,
    end_ns: int,
    direction: str,
    pnl: float,
    chart_type: str = "c_bars",
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
        chart_type:
            OHLC rendering style: 'candlestick', 'oc_bars', 'c_bars', or 'bars'.

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

    color_code_to_matplotlib = {
        "K": "black",
        "R": "red",
        "B": "blue",
        "G": "green",
        "O": "orange",
        "P": "purple",
        "C": "cyan",
        "M": "magenta",
        "Y": "yellow",
        "W": "white",
        "T": "teal",
    }

    indicator_series: dict[str, list[float]] = {}
    indicator_tags: dict[str, int] = {}
    indicator_styles: dict[str, str] = {}
    indicator_colors: dict[str, str] = {}
    for idx in range(len(data)):
        row = data.iloc[idx]
        indicators = json.loads(row["indicators"]) if row["indicators"] else {}
        for name, value in indicators.items():
            if name not in indicator_series:
                indicator_series[name] = [math.nan] * len(data)
                tag = int(name[:2]) if name[:2].isdigit() else 99
                indicator_tags[name] = tag
                style = name[2] if len(name) > 2 and name[2] in "LHD" else "L"
                indicator_styles[name] = style
                color_code = (
                    name[3]
                    if len(name) > 3 and name[3] in color_code_to_matplotlib
                    else "K"
                )
                indicator_colors[name] = color_code_to_matplotlib[color_code]
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
    ax_indicators = list(axes[2:]) if len(axes) > 2 else []

    use_time_axis = bar_period in ("HOUR", "MINUTE", "SECOND")
    if use_time_axis:
        x_values = data["ts_event"].values
        bar_width = (
            pd.Timedelta(minutes=1)
            if bar_period == "MINUTE"
            else (
                pd.Timedelta(seconds=1)
                if bar_period == "SECOND"
                else pd.Timedelta(hours=1)
            )
        )
    else:
        x_values = list(range(len(data)))  # type: ignore[assignment]
        bar_width = 0.8  # type: ignore[assignment]

    entry_price = fills[0]["price"] if fills else 0
    fill_direction = fills[0]["side"] if fills else "BUY"

    pos_x_values = []
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
            pos_x_values.append(x_values[i])
            pnl_high_series.append(pnl_at_high)
            pnl_low_series.append(pnl_at_low)
            hwm_series.append(running_hwm)
            low_watermark_series.append(running_lwm)

    if pos_x_values:
        ax_pnl.fill_between(
            pos_x_values,
            pnl_low_series,
            pnl_high_series,
            color="blue",
            alpha=0.3,
            label="Unrealized P&L",
        )
        ax_pnl.plot(
            pos_x_values,
            hwm_series,
            color="green",
            linewidth=1.5,
            label="High Watermark",
            alpha=0.8,
        )
        ax_pnl.plot(
            pos_x_values,
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

    _draw_ohlc_bars(ax_main, data, x_values, chart_type, bar_width)

    for idx, (name, values) in enumerate(overlay_indicators.items()):
        display_name = name[5:] if len(name) > 5 else name
        color = indicator_colors.get(name, "black")
        style = indicator_styles.get(name, "L")
        if style == "H":
            ax_main.bar(
                x_values,
                values,
                label=display_name,
                alpha=0.6,
                color=color,
                width=bar_width,
            )
        elif style == "D":
            ax_main.scatter(
                x_values,
                values,
                label=display_name,
                alpha=0.8,
                color=color,
                s=10,
            )
        else:
            ax_main.plot(
                x_values,
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
            display_name = name[5:] if len(name) > 5 else name
            color = indicator_colors.get(name, "black")
            style = indicator_styles.get(name, "L")
            if style == "H":
                ax.bar(
                    x_values,
                    values,
                    label=display_name,
                    alpha=0.6,
                    color=color,
                    width=bar_width,
                )
            elif style == "D":
                ax.scatter(
                    x_values,
                    values,
                    label=display_name,
                    alpha=0.8,
                    color=color,
                    s=10,
                )
            else:
                ax.plot(
                    x_values,
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
        highlight_x_start = x_values[highlight_start]
        highlight_x_end = x_values[highlight_end]
        if use_time_axis:
            highlight_width = highlight_x_end - highlight_x_start
        else:
            highlight_width = highlight_end - highlight_start
        for ax in all_axes:
            y_min, y_max = ax.get_ylim()
            rect = Rectangle(
                (highlight_x_start, y_min),  # type: ignore[arg-type]
                highlight_width,  # type: ignore[arg-type]
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
        fill_x = x_values[fill_idx]
        marker = "^" if fill["side"] == "BUY" else "v"
        color = "green" if fill["side"] == "BUY" else "red"
        qty = fill.get("quantity", 1)
        size = 120 * min(3.0, max(0.5, qty))
        ax_main.scatter(
            fill_x,
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
            (fill_x, fill["price"] + offset_y),
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

    if use_time_axis:
        import matplotlib.dates as mdates

        for ax in all_axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    else:
        num_bars = len(data)
        tick_interval = max(1, num_bars // 10)
        tick_positions = list(range(0, num_bars, tick_interval))
        tick_labels = [
            data["ts_event"].iloc[i].strftime("%m/%d") for i in tick_positions
        ]
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


def generate_segment_chart_image(
    run_id: str,
    symbol: str,
    start_ns: int,
    end_ns: int,
    period_start_ns: int | None = None,
    period_end_ns: int | None = None,
    chart_type: str = "c_bars",
) -> bytes:
    """
    Generate a PNG chart image for a bar segment.

    Renders a multi-panel chart showing:
    - Price panel with OHLC bars and overlay indicators
    - Additional panels for non-overlay indicators grouped by tag

    Parameters:
        run_id:
            Unique identifier of the backtest run.
        symbol:
            Instrument symbol.
        start_ns:
            Start timestamp in nanoseconds.
        end_ns:
            End timestamp in nanoseconds.
        period_start_ns:
            Optional period start for fixed x-axis limits.
        period_end_ns:
            Optional period end for fixed x-axis limits.
        chart_type:
            OHLC rendering style: 'candlestick', 'oc_bars', 'c_bars', or 'bars'.

    Returns:
        PNG image bytes, or empty bytes if no data is available.
    """
    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        return b""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT ts_event_ns, open, high, low, close, bar_period, indicators
        FROM bars_processed
        WHERE run_id = ? AND symbol = ? AND ts_event_ns >= ? AND ts_event_ns <= ?
        ORDER BY ts_event_ns
        """,
        (run_id, symbol, start_ns, end_ns),
    )
    bar_rows = cursor.fetchall()
    conn.close()

    if not bar_rows:
        return b""

    bar_period = bar_rows[0][5] if bar_rows else "DAY"

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

    color_code_to_matplotlib = {
        "K": "black",
        "R": "red",
        "B": "blue",
        "G": "green",
        "O": "orange",
        "P": "purple",
        "C": "cyan",
        "M": "magenta",
        "Y": "yellow",
        "W": "white",
        "T": "teal",
    }

    indicator_series: dict[str, list[float]] = {}
    indicator_tags: dict[str, int] = {}
    indicator_styles: dict[str, str] = {}
    indicator_colors: dict[str, str] = {}
    for idx in range(len(data)):
        row = data.iloc[idx]
        indicators = json.loads(row["indicators"]) if row["indicators"] else {}
        for name, value in indicators.items():
            if name not in indicator_series:
                indicator_series[name] = [math.nan] * len(data)
                tag = int(name[:2]) if name[:2].isdigit() else 99
                indicator_tags[name] = tag
                style = name[2] if len(name) > 2 and name[2] in "LHD" else "L"
                indicator_styles[name] = style
                color_code = (
                    name[3]
                    if len(name) > 3 and name[3] in color_code_to_matplotlib
                    else "K"
                )
                indicator_colors[name] = color_code_to_matplotlib[color_code]
            indicator_series[name][idx] = value if value == value else math.nan

    overlay_indicators = {
        k: v for k, v in indicator_series.items() if indicator_tags.get(k, 99) == 0
    }
    subplot_tags = sorted(set(t for t in indicator_tags.values() if 1 <= t <= 98))
    subplot_indicators = {
        tag: {k: v for k, v in indicator_series.items() if indicator_tags.get(k) == tag}
        for tag in subplot_tags
    }

    num_subplots = 1 + len(subplot_tags)
    height_ratios = [3] + [1] * len(subplot_tags)
    fig_height = 6 + 2 * len(subplot_tags)
    fig, axes = plt.subplots(
        num_subplots,
        1,
        figsize=(14, fig_height),
        sharex=True,
        gridspec_kw={"height_ratios": height_ratios},
    )
    if num_subplots == 1:
        axes = [axes]
    ax_main = axes[0]
    ax_indicators = list(axes[1:]) if len(axes) > 1 else []

    use_time_axis = bar_period in ("HOUR", "MINUTE", "SECOND")
    if use_time_axis:
        x_values = data["ts_event"].values
        bar_width = (
            pd.Timedelta(minutes=1)
            if bar_period == "MINUTE"
            else (
                pd.Timedelta(seconds=1)
                if bar_period == "SECOND"
                else pd.Timedelta(hours=1)
            )
        )
    else:
        x_values = list(range(len(data)))  # type: ignore[assignment]
        bar_width = 0.8  # type: ignore[assignment]

    _draw_ohlc_bars(ax_main, data, x_values, chart_type, bar_width)

    for idx, (name, values) in enumerate(overlay_indicators.items()):
        display_name = name[5:] if len(name) > 5 else name
        color = indicator_colors.get(name, "black")
        style = indicator_styles.get(name, "L")
        if style == "H":
            ax_main.bar(
                x_values,
                values,
                label=display_name,
                alpha=0.6,
                color=color,
                width=bar_width,
            )
        elif style == "D":
            ax_main.scatter(
                x_values,
                values,
                label=display_name,
                alpha=0.8,
                color=color,
                s=10,
            )
        else:
            ax_main.plot(
                x_values,
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
            display_name = name[5:] if len(name) > 5 else name
            color = indicator_colors.get(name, "black")
            style = indicator_styles.get(name, "L")
            if style == "H":
                ax.bar(
                    x_values,
                    values,
                    label=display_name,
                    alpha=0.6,
                    color=color,
                    width=bar_width,
                )
            elif style == "D":
                ax.scatter(
                    x_values,
                    values,
                    label=display_name,
                    alpha=0.8,
                    color=color,
                    s=10,
                )
            else:
                ax.plot(
                    x_values,
                    values,
                    label=display_name,
                    linewidth=1.2,
                    alpha=0.8,
                    color=color,
                )
        ax.set_ylabel(f"Tag {tag}", fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper left", fontsize=8)

    ax_main.set_ylabel("Price", fontsize=10)
    ax_main.grid(True, alpha=0.3)

    start_time = data["ts_event"].iloc[0]
    end_time = data["ts_event"].iloc[-1]
    ax_main.set_title(
        f"{symbol} - {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')} ({len(data)} bars)",
        fontsize=14,
    )

    all_axes = [ax_main] + ax_indicators
    if use_time_axis:
        import matplotlib.dates as mdates

        if period_start_ns is not None and period_end_ns is not None:
            xlim_start = pd.to_datetime(period_start_ns, unit="ns")
            xlim_end = pd.to_datetime(period_end_ns, unit="ns")
            for ax in all_axes:
                ax.set_xlim(xlim_start, xlim_end)
            first_data_time = data["ts_event"].iloc[0]
            if first_data_time < xlim_start:
                for ax in all_axes:
                    ax.axvspan(first_data_time, xlim_start, facecolor="grey", alpha=0.2)
        for ax in all_axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    else:
        num_bars = len(data)
        tick_interval = max(1, num_bars // 10)
        tick_positions = list(range(0, num_bars, tick_interval))
        tick_labels = [
            data["ts_event"].iloc[i].strftime("%m/%d %H:%M") for i in tick_positions
        ]
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


def _compute_trade_journey_data(
    run_id: str,
    roundtrips: list[dict],
) -> list[dict]:
    """
    Compute max positive/negative price movements for each round-trip trade.

    Parameters:
        run_id:
            Unique identifier of the backtest run.
        roundtrips:
            List of round-trip trade dictionaries.

    Returns:
        List of dictionaries with max_positive_pts, max_negative_pts, exit_pts, is_winner, and duration_bars.
    """
    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    journey_data = []
    for rt in roundtrips:
        symbol = rt["symbol"]
        direction = rt["direction"]
        entry_ts = rt["entry_ts"]
        exit_ts = rt["exit_ts"]

        cursor.execute(
            """
            SELECT fill_price FROM fills
            WHERE run_id = ? AND symbol = ? AND ts_broker_ns = ?
            LIMIT 1
            """,
            (run_id, symbol, entry_ts),
        )
        entry_row = cursor.fetchone()
        if not entry_row:
            cursor.execute(
                """
                SELECT fill_price FROM fills
                WHERE run_id = ? AND symbol = ? AND ts_broker_ns >= ?
                ORDER BY ts_broker_ns LIMIT 1
                """,
                (run_id, symbol, entry_ts),
            )
            entry_row = cursor.fetchone()

        cursor.execute(
            """
            SELECT fill_price FROM fills
            WHERE run_id = ? AND symbol = ? AND ts_broker_ns = ?
            LIMIT 1
            """,
            (run_id, symbol, exit_ts),
        )
        exit_row = cursor.fetchone()
        if not exit_row:
            cursor.execute(
                """
                SELECT fill_price FROM fills
                WHERE run_id = ? AND symbol = ? AND ts_broker_ns <= ?
                ORDER BY ts_broker_ns DESC LIMIT 1
                """,
                (run_id, symbol, exit_ts),
            )
            exit_row = cursor.fetchone()

        if not entry_row or not exit_row:
            journey_data.append(
                {
                    "max_positive_pts": 0.0,
                    "max_negative_pts": 0.0,
                    "exit_pts": 0.0,
                    "is_winner": rt["pnl_after_commission"] > 0,
                    "duration_bars": rt.get("duration_bars", 1),
                }
            )
            continue

        entry_price = entry_row[0]
        exit_price = exit_row[0]

        cursor.execute(
            """
            SELECT high, low FROM bars
            WHERE run_id = ? AND symbol = ? AND ts_event_ns >= ? AND ts_event_ns <= ?
            ORDER BY ts_event_ns
            """,
            (run_id, symbol, entry_ts, exit_ts),
        )
        bars = cursor.fetchall()

        max_positive_pts = 0.0
        max_negative_pts = 0.0

        for bar_high, bar_low in bars:
            if direction == "LONG":
                positive_move = bar_high - entry_price
                negative_move = bar_low - entry_price
            else:
                positive_move = entry_price - bar_low
                negative_move = entry_price - bar_high

            max_positive_pts = max(max_positive_pts, positive_move)
            max_negative_pts = min(max_negative_pts, negative_move)

        if direction == "LONG":
            exit_pts = exit_price - entry_price
        else:
            exit_pts = entry_price - exit_price

        journey_data.append(
            {
                "max_positive_pts": max_positive_pts,
                "max_negative_pts": max_negative_pts,
                "exit_pts": exit_pts,
                "is_winner": rt["pnl_after_commission"] > 0,
                "duration_bars": rt.get("duration_bars", 1),
            }
        )

    conn.close()
    return journey_data


def generate_trade_journey_chart(run_id: str, roundtrips: list[dict]) -> bytes:
    """
    Generate a Trade Journey chart showing max price movements and exit points.

    Renders a bar chart where each trade shows:
    - Vertical bar from 0 to max positive movement (green for wins, red for losses)
    - Vertical bar from 0 to max negative movement (same color)
    - Circle marker at exit point (dark green for wins, dark red for losses)
    - Horizontal lines for average winning and losing exit points

    Parameters:
        run_id:
            Unique identifier of the backtest run.
        roundtrips:
            List of round-trip trade dictionaries.

    Returns:
        PNG image bytes, or empty bytes if no data is available.
    """
    if not roundtrips:
        return b""

    journey_data = _compute_trade_journey_data(run_id, roundtrips)
    if not journey_data:
        return b""

    fig, ax = plt.subplots(figsize=(14, 7))

    win_color = "#3fb950"
    loss_color = "#f85149"
    win_exit_color = "#1a7f37"
    loss_exit_color = "#a40e26"

    winning_exits = []
    losing_exits = []
    winning_bars = []
    losing_bars = []

    all_durations = [d["duration_bars"] for d in journey_data]
    max_duration = max(all_durations) if all_durations else 1
    min_width = 0.2
    max_width = 0.9

    for i, data in enumerate(journey_data):
        trade_num = i + 1
        max_pos = data["max_positive_pts"]
        max_neg = data["max_negative_pts"]
        exit_pt = data["exit_pts"]
        is_winner = data["is_winner"]
        duration = data["duration_bars"]

        if max_duration > 1:
            bar_width = min_width + (duration / max_duration) * (max_width - min_width)
        else:
            bar_width = max_width

        bar_color = win_color if is_winner else loss_color

        if max_pos > 0:
            ax.bar(
                trade_num,
                max_pos,
                bottom=0,
                color=bar_color,
                width=bar_width,
                alpha=0.7,
            )
        if max_neg < 0:
            ax.bar(
                trade_num,
                abs(max_neg),
                bottom=max_neg,
                color=bar_color,
                width=bar_width,
                alpha=0.7,
            )

        half_width = bar_width / 2
        ax.hlines(
            exit_pt,
            trade_num - half_width,
            trade_num + half_width,
            colors="black",
            linewidth=1.5,
            zorder=5,
        )

        if is_winner:
            winning_exits.append(exit_pt)
            winning_bars.append(duration)
        else:
            losing_exits.append(exit_pt)
            losing_bars.append(duration)

    ax.axhline(y=0, color="black", linestyle="-", linewidth=0.8, alpha=0.5)

    if winning_exits:
        avg_win = sum(winning_exits) / len(winning_exits)
        ax.axhline(
            y=avg_win,
            color=win_exit_color,
            linestyle="--",
            linewidth=1.5,
            alpha=0.8,
            label=f"Avg Win Exit: {avg_win:.1f} pts",
        )

    if losing_exits:
        avg_loss = sum(losing_exits) / len(losing_exits)
        ax.axhline(
            y=avg_loss,
            color=loss_exit_color,
            linestyle="--",
            linewidth=1.5,
            alpha=0.8,
            label=f"Avg Loss Exit: {avg_loss:.1f} pts",
        )

    total_trades = len(journey_data)
    max_pos_values = [d["max_positive_pts"] for d in journey_data]
    max_neg_values = [d["max_negative_pts"] for d in journey_data]
    exit_values = [d["exit_pts"] for d in journey_data]

    avg_max_pos = sum(max_pos_values) / total_trades if total_trades > 0 else 0
    highest_pos = max(max_pos_values) if max_pos_values else 0
    avg_max_neg = abs(sum(max_neg_values) / total_trades) if total_trades > 0 else 0
    worst_neg = abs(min(max_neg_values)) if max_neg_values else 0
    avg_exit = sum(exit_values) / total_trades if total_trades > 0 else 0
    best_exit = max(exit_values) if exit_values else 0
    worst_exit = min(exit_values) if exit_values else 0

    max_win_bars = max(winning_bars) if winning_bars else 0
    avg_win_bars = sum(winning_bars) / len(winning_bars) if winning_bars else 0
    max_loss_bars = max(losing_bars) if losing_bars else 0
    avg_loss_bars = sum(losing_bars) / len(losing_bars) if losing_bars else 0

    summary_text = (
        f"Trade Journey Summary\n"
        f"Total Trades: {total_trades}\n\n"
        f"Max Positive Movement:\n"
        f"  Average: {avg_max_pos:.1f} pts\n"
        f"  Highest: {highest_pos:.1f} pts\n\n"
        f"Max Negative Movement:\n"
        f"  Average: {avg_max_neg:.1f} pts\n"
        f"  Worst: {worst_neg:.1f} pts\n\n"
        f"Exit Points:\n"
        f"  Average: {avg_exit:.1f} pts\n"
        f"  Best: {best_exit:.1f} pts\n"
        f"  Worst: {worst_exit:.1f} pts\n\n"
        f"Trade Duration (Bars):\n"
        f"  Wins:   Max {max_win_bars}, Avg {avg_win_bars:.1f}\n"
        f"  Losses: Max {max_loss_bars}, Avg {avg_loss_bars:.1f}"
    )

    props = dict(
        boxstyle="round,pad=0.5", facecolor="#add8e6", edgecolor="#4682b4", alpha=0.9
    )
    ax.text(
        0.02,
        0.98,
        summary_text,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        fontfamily="monospace",
        bbox=props,
    )

    from matplotlib.lines import Line2D

    legend_elements = [
        Line2D(
            [0], [0], color=win_color, linewidth=8, alpha=0.7, label="Winning Trades"
        ),
        Line2D(
            [0], [0], color=loss_color, linewidth=8, alpha=0.7, label="Losing Trades"
        ),
        Line2D([0], [0], color="black", linewidth=2, label="Exit Point"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=9)

    ax.set_title(
        "Trade Journey Analysis - Maximum Price Movements & Exit Points", fontsize=14
    )
    ax.set_xlabel("Trade Number", fontsize=11)
    ax.set_ylabel("Points from Entry Price", fontsize=11)
    ax.grid(True, alpha=0.3, axis="y")

    num_trades = len(journey_data)
    if num_trades > 20:
        tick_interval = max(1, num_trades // 15)
        tick_positions = list(range(1, num_trades + 1, tick_interval))
        ax.set_xticks(tick_positions)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=500, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    return buf.read()


def generate_pnl_summary_chart(roundtrips: list[dict]) -> bytes:
    """
    Generate a PnL Summary chart showing cumulative PnL and trade metrics.

    Renders a single-panel chart showing cumulative PnL (gross and net) with max drawdown bars.

    Parameters:
        roundtrips:
            List of round-trip trade dictionaries.

    Returns:
        PNG image bytes, or empty bytes if no data is available.
    """
    if not roundtrips:
        return b""

    fig, ax = plt.subplots(figsize=(14, 7))

    trade_nums = list(range(1, len(roundtrips) + 1))
    cumulative_pnl_gross = []
    cumulative_pnl_net = []
    max_drawdowns = []

    running_gross = 0.0
    running_net = 0.0
    for rt in roundtrips:
        running_gross += rt["pnl_before_commission"]
        running_net += rt["pnl_after_commission"]
        cumulative_pnl_gross.append(running_gross)
        cumulative_pnl_net.append(running_net)
        max_drawdowns.append(rt["max_drawdown"])

    ax.plot(
        trade_nums,
        cumulative_pnl_gross,
        color="#3fb950",
        linewidth=2,
        label="Cumulative PnL (Gross)",
        marker="o",
        markersize=4,
    )
    ax.plot(
        trade_nums,
        cumulative_pnl_net,
        color="#1f6feb",
        linewidth=2,
        label="Cumulative PnL (Net)",
        marker="o",
        markersize=4,
    )
    ax.bar(
        trade_nums,
        [-d for d in max_drawdowns],
        color="#f85149",
        alpha=0.5,
        width=0.4,
        label="Max Drawdown",
    )

    total_trades = len(roundtrips)
    total_pnl_gross = cumulative_pnl_gross[-1] if cumulative_pnl_gross else 0
    total_pnl_net = cumulative_pnl_net[-1] if cumulative_pnl_net else 0

    winning_trades = [rt for rt in roundtrips if rt["pnl_after_commission"] > 0]
    losing_trades = [rt for rt in roundtrips if rt["pnl_after_commission"] <= 0]
    num_winners = len(winning_trades)
    num_losers = len(losing_trades)

    avg_winner = (
        sum(rt["pnl_after_commission"] for rt in winning_trades) / num_winners
        if num_winners > 0
        else 0
    )
    avg_loser = (
        sum(rt["pnl_after_commission"] for rt in losing_trades) / num_losers
        if num_losers > 0
        else 0
    )

    summary_text = (
        f"PnL Summary\n"
        f"Total Trades: {total_trades}\n\n"
        f"Overall PnL (Gross): {total_pnl_gross:+.2f}\n"
        f"Overall PnL (Net): {total_pnl_net:+.2f}\n\n"
        f"Winning Trades: {num_winners}\n"
        f"Losing Trades: {num_losers}\n\n"
        f"Avg Winning Trade: {avg_winner:+.2f}\n"
        f"Avg Losing Trade: {avg_loser:+.2f}"
    )

    props = dict(
        boxstyle="round,pad=0.5", facecolor="#add8e6", edgecolor="#4682b4", alpha=0.9
    )
    ax.text(
        0.02,
        0.98,
        summary_text,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        fontfamily="monospace",
        bbox=props,
    )

    ax.legend(loc="upper right", fontsize=9)
    ax.axhline(y=0, color="black", linestyle="-", alpha=0.5, linewidth=0.8)
    ax.set_title("PnL Summary - Cumulative Performance & Trade Metrics", fontsize=14)
    ax.set_ylabel("PnL", fontsize=11)
    ax.set_xlabel("Trade Number", fontsize=11)
    ax.grid(True, alpha=0.3, axis="y")

    if total_trades > 20:
        tick_interval = max(1, total_trades // 15)
        tick_positions = list(range(1, total_trades + 1, tick_interval))
        ax.set_xticks(tick_positions)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=500, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    return buf.read()
