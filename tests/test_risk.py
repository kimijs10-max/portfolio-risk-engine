"""
Checks on the risk maths in src/analytics/risk.py.

VaR against a hand-computed quantile and the normal formula, the tail
count that decides whether a VaR is quotable, and concentration (HHI and
effective N) with and without cash.

Run with pytest, or directly:
    python tests/test_risk.py
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analytics import risk  # noqa: E402
from storage import db  # noqa: E402


def test_historical_var_is_the_empirical_quantile_as_a_loss():
    r = pd.Series(np.linspace(-0.10, 0.09, 20))
    v = risk.value_at_risk(r, 0.95)
    assert math.isclose(v.historical, -float(np.quantile(r, 0.05)))
    assert v.historical > 0
    assert v.n_obs == 20


def test_parametric_var_matches_the_normal_formula():
    r = pd.Series([0.01, -0.02, 0.015, -0.005, 0.0, 0.02, -0.03])
    v = risk.value_at_risk(r, 0.99)
    expected = -(r.mean() - risk.Z[0.99] * r.std(ddof=1))
    assert math.isclose(v.parametric, expected)


def test_small_tail_is_flagged_unreliable():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0, 0.01, 250))
    assert not risk.value_at_risk(r, 0.99).reliable  # ~3 points in a 1% tail
    assert risk.value_at_risk(r, 0.95).reliable      # ~13 points in a 5% tail


def test_unsupported_level_and_empty_series_raise():
    for args in [(pd.Series([0.01]), 0.90), (pd.Series(dtype=float), 0.95)]:
        try:
            risk.value_at_risk(*args)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {args}")


def test_concentration_with_and_without_cash():
    conn = db.connect(Path(":memory:"))
    db.upsert_df(conn, "positions", pd.DataFrame([
        {"report_date": "2026-01-05", "account_id": "T", "conid": "1", "symbol": "A",
         "position_value": 600.0, "fx_rate_to_base": 1.0},
        {"report_date": "2026-01-05", "account_id": "T", "conid": "2", "symbol": "B",
         "position_value": 200.0, "fx_rate_to_base": 1.0},
    ]))
    db.upsert_df(conn, "nav_history", pd.DataFrame([
        {"report_date": "2026-01-05", "account_id": "T", "total": 1000.0},
    ]))
    c = risk.concentration(conn)
    # Equity sleeve 75/25: HHI 0.625, effective N 1.6.
    assert math.isclose(c["hhi_equity"], 0.75**2 + 0.25**2)
    assert math.isclose(c["effective_n_equity"], 1 / 0.625)
    # Of NAV 60/20 plus 20% cash: cash dilutes concentration.
    assert math.isclose(c["cash_weight_nav"], 0.2)
    assert math.isclose(c["hhi_nav"], 0.6**2 + 0.2**2 + 0.2**2)
    assert c["effective_n_nav"] > c["effective_n_equity"]


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"  ok  {name}")
    print(f"{len(tests)} passed")
