"""
Checks on the P&L attribution maths in src/analytics/pnl.py.

A three-day toy account in an in-memory database, with answers that can
be worked out by hand: share counts must be rebuilt backwards from
today's position, the stock / FX / interaction split must sum exactly to
the change in base-currency value, and a market holiday must carry the
last price forward rather than drop the move.

Run with pytest, or directly:
    python tests/test_pnl.py
"""

import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analytics import pnl  # noqa: E402
from storage import db  # noqa: E402

DATES = ["2026-01-05", "2026-01-06", "2026-01-07"]


def _account(prices, fx, trades=()):
    """One JPY holding of 100 shares today; trades are (date, quantity)."""
    conn = db.connect(Path(":memory:"))
    db.upsert_df(conn, "nav_history", pd.DataFrame({
        "report_date": DATES, "account_id": "TEST", "total": 1.0,
    }))
    db.upsert_df(conn, "positions", pd.DataFrame([{
        "report_date": DATES[-1], "account_id": "TEST", "conid": "1",
        "symbol": "AAA", "currency": "JPY", "position": 100.0,
    }]))
    db.upsert_df(conn, "trades", pd.DataFrame(
        [{"transaction_id": str(i), "symbol": "AAA", "currency": "JPY",
          "trade_date": d, "quantity": q} for i, (d, q) in enumerate(trades)],
        columns=["transaction_id", "symbol", "currency", "trade_date", "quantity"],
    ))
    db.upsert_df(conn, "holding_prices", pd.DataFrame(
        [{"date": d, "symbol": "AAA", "close": p} for d, p in prices.items()]))
    db.upsert_df(conn, "fx_rates", pd.DataFrame(
        [{"date": d, "pair": "JPYSGD", "rate": r} for d, r in fx.items()]))
    return conn


def test_quantity_history_undoes_later_trades():
    conn = _account({d: 1000 for d in DATES}, {d: 0.01 for d in DATES},
                    trades=[("2026-01-06", 60.0), ("2026-01-07", -10.0)])
    q = pnl.reconstruct_quantity_history(conn).set_index("date")["quantity"]
    # 100 today; before selling 10 on the 7th it was 110; before buying 60 on the 6th, 50.
    assert q.to_dict() == {"2026-01-05": 50.0, "2026-01-06": 110.0, "2026-01-07": 100.0}


def test_split_sums_to_base_value_change():
    prices = {"2026-01-05": 1000, "2026-01-06": 1100, "2026-01-07": 1100}
    fx = {"2026-01-05": 0.0100, "2026-01-06": 0.0095, "2026-01-07": 0.0095}
    m = pnl.compute_mark_to_market(_account(prices, fx)).set_index("date")
    day = m.loc["2026-01-06"]
    assert math.isclose(day["r_local"], 0.10)
    assert math.isclose(day["r_fx"], -0.05)
    # 100 shares x 1000 JPY x 0.01 = 1000 SGD before; 100 x 1100 x 0.0095 = 1045 after.
    assert math.isclose(day["stock_move"], 100.0)
    assert math.isclose(day["fx_move"], -50.0)
    assert math.isclose(day["interaction"], -5.0)
    assert math.isclose(day["total_move"], 45.0)


def test_cross_term_is_reported_not_folded_in():
    prices = {"2026-01-05": 1000, "2026-01-06": 1200, "2026-01-07": 1200}
    fx = {"2026-01-05": 0.010, "2026-01-06": 0.012, "2026-01-07": 0.012}
    day = pnl.compute_mark_to_market(_account(prices, fx)).set_index("date").loc["2026-01-06"]
    assert math.isclose(day["interaction"], day["value_prev_base"] * 0.2 * 0.2)
    assert math.isclose(day["stock_move"] + day["fx_move"], day["total_move"] - day["interaction"])


def test_holiday_carries_price_forward_and_keeps_the_move():
    # No Tokyo print on the 6th: the move from the 5th to the 7th must still count.
    prices = {"2026-01-05": 1000, "2026-01-07": 1100}
    fx = {d: 0.01 for d in DATES}
    m = pnl.compute_mark_to_market(_account(prices, fx)).set_index("date")
    assert math.isclose(m.loc["2026-01-06", "stock_move"], 0.0)
    assert math.isclose(m.loc["2026-01-07", "stock_move"], 100.0)
    assert math.isclose(m["total_move"].sum(), 100 * (1100 - 1000) * 0.01)


def test_unheld_days_are_not_marked():
    conn = _account({"2026-01-05": 1000, "2026-01-06": 2000, "2026-01-07": 2000},
                    {d: 0.01 for d in DATES}, trades=[("2026-01-06", 100.0)])
    m = pnl.compute_mark_to_market(conn)
    # Bought on the 6th: nothing held overnight into the 6th, so its doubling is not P&L.
    assert "2026-01-06" not in set(m["date"])


def test_unknown_currency_is_an_error():
    try:
        pnl._fx_pair_for_currency("EUR")
    except ValueError:
        return
    raise AssertionError("expected ValueError for an unconfigured currency")


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"  ok  {name}")
    print(f"{len(tests)} passed")
