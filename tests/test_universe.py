"""
Checks on sector-screen verification in src/screener/universe.py.

Run with pytest, or directly:
    python tests/test_universe.py
"""

import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from screener import universe  # noqa: E402
from storage import db  # noqa: E402

SCREEN = {
    "toy": {
        "label": "Toy transport",
        "sector": "Industrials",
        "industries": ["Railroads", "Trucking"],
        "candidates": ["RAIL1", "RAIL2", "TRUCK", "MACH", "ETF", "BANK", "GONE"],
    },
}

META = pd.DataFrame([
    # symbol, sector, industry, quote_type
    ("RAIL1", "Industrials", "Railroads", "EQUITY"),
    ("RAIL2", "Industrials", "Railroads", "EQUITY"),
    ("TRUCK", "Industrials", "Trucking", "EQUITY"),
    ("MACH", "Industrials", "Specialty Industrial Machinery", "EQUITY"),
    ("ETF", "Industrials", "Railroads", "ETF"),
    ("BANK", "Financial Services", "Banks - Regional", "EQUITY"),
], columns=["symbol", "sector", "industry", "quote_type"]).assign(
    short_name="x", currency="USD", financial_currency="USD", fetched_at="2026-11-25")


def _verify():
    original = universe.peer_config.SECTOR_SCREENS
    universe.peer_config.SECTOR_SCREENS = SCREEN
    try:
        with tempfile.TemporaryDirectory() as tmp:
            conn = db.connect(Path(tmp) / "t.db")
            db.upsert_df(conn, "security_meta", META)
            groups, rejected = universe.verified_sector(conn, "toy")
            conn.close()
    finally:
        universe.peer_config.SECTOR_SCREENS = original
    return groups, rejected.set_index("symbol")["reason"]


def test_groups_are_the_reported_industries():
    groups, _ = _verify()
    assert {k: sorted(v) for k, v in groups.items()} == {
        "Railroads": ["RAIL1", "RAIL2"], "Trucking": ["TRUCK"]}


def test_right_sector_wrong_industry_is_dropped():
    # "Industrials" alone would admit a machinery maker into a transport screen.
    _, reasons = _verify()
    assert "outside the screen" in reasons["MACH"]


def test_every_other_failure_is_reported():
    _, reasons = _verify()
    assert "not an equity" in reasons["ETF"]
    assert "sector 'Financial Services'" in reasons["BANK"]
    assert reasons["GONE"] == "unresolved"
    assert len(reasons) == 4


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"{len(tests)} passed")
