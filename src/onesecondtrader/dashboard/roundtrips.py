"""
Round-trip trade computation from fill records.

Aggregates fill events into complete round-trip trades with P&L, duration,
high watermark, and maximum drawdown metrics.
"""

from __future__ import annotations

import os
import sqlite3

from .db import get_runs_db_path


def compute_hwm_and_drawdown(
    conn: sqlite3.Connection,
    run_id: str,
    symbol: str,
    direction: str,
    avg_entry: float,
    quantity: float,
    entry_ts: int,
    exit_ts: int,
) -> tuple[float, float]:
    """
    Compute high watermark and maximum drawdown for a round-trip trade.

    Iterates through bars during the trade period to track the best unrealized
    P&L (high watermark) and the largest decline from that peak (max drawdown).

    Parameters:
        conn:
            SQLite database connection.
        run_id:
            Unique identifier of the backtest run.
        symbol:
            Instrument symbol for the trade.
        direction:
            Trade direction, either "LONG" or "SHORT".
        avg_entry:
            Average entry price.
        quantity:
            Total position quantity.
        entry_ts:
            Entry timestamp in nanoseconds.
        exit_ts:
            Exit timestamp in nanoseconds.

    Returns:
        Tuple of (high_watermark, max_drawdown) in currency units.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT high, low FROM bars
        WHERE run_id = ? AND symbol = ? AND ts_event_ns >= ? AND ts_event_ns <= ?
        ORDER BY ts_event_ns
        """,
        (run_id, symbol, entry_ts, exit_ts),
    )
    bars = cursor.fetchall()

    if not bars:
        return 0.0, 0.0

    high_watermark = 0.0
    max_drawdown = 0.0

    for bar_high, bar_low in bars:
        if direction == "LONG":
            best_pnl = (bar_high - avg_entry) * quantity
            worst_pnl = (bar_low - avg_entry) * quantity
        else:
            best_pnl = (avg_entry - bar_low) * quantity
            worst_pnl = (avg_entry - bar_high) * quantity

        if best_pnl > high_watermark:
            high_watermark = best_pnl

        drawdown = high_watermark - worst_pnl
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return high_watermark, max_drawdown


def get_roundtrips(run_id: str) -> list[dict]:
    """
    Compute round-trip trades from fill records for a run.

    Aggregates fills by symbol into complete round-trips, calculating entry/exit
    prices, P&L, duration, high watermark, and maximum drawdown for each.

    Parameters:
        run_id:
            Unique identifier of the backtest run.

    Returns:
        List of round-trip dictionaries with symbol, direction, duration, max_position,
        high_watermark, max_drawdown, pnl_before_commission, pnl_after_commission,
        entry_ts, and exit_ts.
    """
    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT symbol, side, quantity_filled, fill_price, commission, ts_broker_ns
        FROM fills
        WHERE run_id = ?
        ORDER BY symbol, ts_broker_ns
        """,
        (run_id,),
    )
    rows = cursor.fetchall()

    fills_by_symbol: dict[str, list] = {}
    for row in rows:
        symbol = row[0]
        fills_by_symbol.setdefault(symbol, []).append(
            {
                "side": row[1],
                "quantity": row[2],
                "price": row[3],
                "commission": row[4],
                "ts_ns": row[5],
            }
        )

    roundtrips = []
    for symbol, fills in fills_by_symbol.items():
        position = 0.0
        entry_fills: list[dict] = []
        entry_value = 0.0
        entry_commission = 0.0
        max_pos = 0.0
        start_ts: int = 0

        for fill in fills:
            signed_qty = (
                fill["quantity"] if fill["side"] == "BUY" else -fill["quantity"]
            )
            if position == 0.0:
                start_ts = fill["ts_ns"]
                entry_fills = []
                entry_value = 0.0
                entry_commission = 0.0
                max_pos = 0.0

            position += signed_qty
            max_pos = max(max_pos, abs(position))

            if (signed_qty > 0 and position > 0) or (signed_qty < 0 and position < 0):
                entry_value += fill["price"] * fill["quantity"]
                entry_commission += fill["commission"]
                entry_fills.append(fill)
            else:
                exit_commission = fill["commission"]

                if abs(position) < 1e-9:
                    direction = (
                        "LONG"
                        if entry_fills and entry_fills[0]["side"] == "BUY"
                        else "SHORT"
                    )
                    total_entry_qty = sum(f["quantity"] for f in entry_fills)
                    avg_entry = (
                        entry_value / total_entry_qty if total_entry_qty > 0 else 0
                    )
                    avg_exit = fill["price"]
                    total_commission = entry_commission + exit_commission

                    if direction == "LONG":
                        pnl_before_commission = (avg_exit - avg_entry) * total_entry_qty
                    else:
                        pnl_before_commission = (avg_entry - avg_exit) * total_entry_qty

                    pnl_after_commission = pnl_before_commission - total_commission

                    duration_ns = fill["ts_ns"] - start_ts
                    duration_seconds = duration_ns / 1_000_000_000

                    hwm, mdd = compute_hwm_and_drawdown(
                        conn,
                        run_id,
                        symbol,
                        direction,
                        avg_entry,
                        total_entry_qty,
                        start_ts,
                        fill["ts_ns"],
                    )

                    roundtrips.append(
                        {
                            "symbol": symbol,
                            "direction": direction,
                            "duration_seconds": round(duration_seconds, 2),
                            "max_position": round(max_pos, 4),
                            "high_watermark": round(hwm, 2),
                            "max_drawdown": round(mdd, 2),
                            "pnl_before_commission": round(pnl_before_commission, 2),
                            "pnl_after_commission": round(pnl_after_commission, 2),
                            "entry_ts": start_ts,
                            "exit_ts": fill["ts_ns"],
                        }
                    )
                    position = 0.0

    conn.close()
    return roundtrips
