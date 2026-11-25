"""
Bulk fetch of fundamentals and prices for the whole screening universe.

Separate from `universe.py` (which resolves and verifies peer membership)
because this is the slow part: yfinance is a per-ticker API, so roughly a
hundred and fifty symbols times four requests each is minutes, not
seconds. Keeping it in its own entry point means the verification step
stays cheap to re-run.

Only verified peers are fetched. Resolving membership first and fetching
second means no time is spent downloading statements for a ticker that
turns out to be an ETF or to sit in the wrong sector.

Prices go through market_data.get_holding_price_history, which applies the
same mis-scaled-print filter used everywhere else in the project -- the
one that was added after two bad days in the TOPIX benchmark inflated its
volatility from 1.3% to 43%. A screening universe of a hundred and fifty
tickers is far more likely to contain such a print than six holdings are.

Run directly:
    python src/screener/fetch_universe.py
"""

from __future__ import annotations

import sys

import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data import fundamentals, market_data  # noqa: E402
from screener import universe  # noqa: E402
from storage import db  # noqa: E402

# Five years, not two. A 12-1 momentum signal measured as of a date one
# year in the past needs two years of prices *before* that date plus the
# forward year, so the cross-sectional validation in validate.py needs
# three years minimum. Fetching two silently left momentum unavailable for
# 130 of 132 names and withheld every composite that includes it.
PRICE_PERIOD = "5y"


def screen_universe(conn, sector: str | None = None) -> list[str]:
    """Holdings plus their verified peers, de-duplicated -- or, with
    `sector`, that sector screen's verified names."""
    groups, _ = (universe.verified_sector(conn, sector) if sector
                 else universe.verified_peers(conn))
    # Peer groups are keyed by a holding (a ticker); sector groups by an
    # industry name, which is not a ticker.
    symbols: set[str] = set() if sector else set(groups)
    for peers in groups.values():
        symbols |= set(peers)
    return sorted(symbols)


def main(what: str = "all", sector: str | None = None) -> None:
    """`what` is "all", "fundamentals" or "prices" -- the two halves take
    minutes each and are usually re-run for different reasons.

    With `sector`, only that screen's names that have nothing stored yet
    are fetched. Names it shares with the holdings' universe (the shipping
    peers) keep the data the holdings' screen was run on, so running a
    sector screen never moves the holdings' results."""
    conn = db.connect()
    try:
        symbols = screen_universe(conn, sector)
        if not symbols:
            print("No verified peer groups. Run src/screener/universe.py first.")
            return
        if sector:
            have = set(db.read_table(conn, "fundamentals")["symbol"]) \
                & set(db.read_table(conn, "screen_prices")["symbol"])
            print(f"{len(set(symbols) & have)} of {len(symbols)} already stored; "
                  "fetching the rest.")
            symbols = [s for s in symbols if s not in have]
            if not symbols:
                return

        print(f"Screening universe: {len(symbols)} symbols\n")

        f = pd.DataFrame()
        if what in ("all", "fundamentals"):
            print("Fetching annual fundamentals...")
            f = fundamentals.get_fundamentals(symbols)
            if not f.empty:
                n = db.upsert_df(conn, "fundamentals", f)
                print(f"\nfundamentals  {n:>6} rows  "
                      f"({f['symbol'].nunique()} of {len(symbols)} symbols)")

        if what in ("all", "prices"):
            print(f"\nFetching price history ({PRICE_PERIOD}, spike-filtered)...")
            prices = market_data.get_holding_price_history(symbols, period=PRICE_PERIOD)
            if not prices.empty:
                n = db.upsert_df(conn, "screen_prices", prices)
                print(f"screen_prices {n:>6} rows  "
                      f"({prices['symbol'].nunique()} of {len(symbols)} symbols)")

        if not f.empty:
            missing = sorted(set(symbols) - set(f["symbol"].unique()))
            if missing:
                print(f"\nNo fundamentals returned for {len(missing)}: "
                      f"{', '.join(missing)}")
    finally:
        conn.close()


if __name__ == "__main__":
    # python src/screener/fetch_universe.py [all|fundamentals|prices] [--sector NAME]
    args = sys.argv[1:]
    sector = None
    if "--sector" in args:
        i = args.index("--sector")
        sector = args[i + 1]
        del args[i:i + 2]
    main(args[0] if args else "all", sector)
