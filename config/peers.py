"""
Peer groups for the sector-neutral screen (Phase 4c).

A composite score is only meaningful against comparable companies. Gross
profitability of 0.08 is poor for a software company and unremarkable for
a shipping line; a price-to-book of 0.95 is cheap for a semiconductor
maker and ordinary for a Japanese regional bank. Ranking the whole book
on one list would mostly rank sectors. So each holding is scored against
its own peer group, and the composite never compares across groups.

**These lists are candidates, not the universe.** Every ticker is
verified against the issuer's own reported sector and industry in
`screener/universe.py` before it is used: anything that fails to resolve,
or that resolves into a different industry from the holding it is meant to
sit beside, is dropped and reported. Curating by hand and verifying
mechanically is deliberate -- a mistyped or repurposed ticker would
otherwise sit silently in a peer group and shift every percentile in it.

Groups are drawn from each holding's own listing market where the sector
is well populated there (Japanese banks, Japanese tyre and auto-parts
makers), and extended internationally where it is not (marine shipping is
a global industry with few Tokyo-listed names).

Survivorship bias applies to all of it: these are companies that exist
today, so any historical ranking built on them excludes the ones that
failed. That overstates the health of every peer group and is why the
backtest in 4d is a demonstration rather than evidence.
"""

# Each holding -> the candidate peers it should be ranked against.
#
# Tickers removed after verification, kept here as a record rather than
# silently deleted:
#
#   Delisted or reorganised, no price data at all --
#     9613.T, 4726.T, 4449.T, 4435.T, 6201.T, HMM.KS, and five Japanese
#     regional banks (8355.T Shizuoka, 8369.T Kyoto, 8379.T Hiroshima,
#     8382.T Chugoku, 8385.T Iyo), all of which reorganised into holding
#     companies under new tickers. Their successors are included below.
#
#   Ticker reused by a different instrument --
#     EGLE was Eagle Bulk Shipping until Star Bulk acquired it and is now
#     a Global X S&P 500 ETF; GOGL was Golden Ocean until the CMB.TECH
#     merger and is now a 2x leveraged Google ETF. Both still return live
#     prices. Only the instrument type gives them away.
#
#   Classified outside the holding's sector --
#     3659.T, 4751.T, 3774.T, 2371.T (Communication Services), 2432.T
#     (Industrials), 4385.T, ETSY, EBAY (Consumer Cyclical), 4588.T
#     (Healthcare), PYPL (Financial Services), APP (Communication
#     Services). Several were my own misclassification; the rest are
#     cases where the business is adjacent but the sector is not.
PEER_GROUPS: dict[str, list[str]] = {
    # Appier Group: Tokyo-listed software. Japanese software, SaaS and the
    # larger system integrators. The thinnest group of the six -- much of
    # the Japanese internet sector classifies as Communication Services
    # rather than Technology, which legitimately removes it from a
    # sector-neutral comparison.
    "4180.T": [
        "3994.T", "4478.T", "4443.T", "4684.T", "4704.T", "4307.T",
        "2317.T", "4477.T", "3844.T", "4725.T", "4397.T",
        "9719.T", "3626.T", "2327.T", "4768.T", "4475.T", "4485.T",
        "4194.T", "4493.T", "3760.T", "4053.T", "3639.T",
    ],
    # Toyo Tire: tyre makers first, then the wider Japanese auto-parts
    # complex, then the global tyre and parts names.
    "5105.T": [
        "5108.T", "5101.T", "5110.T", "7259.T", "6902.T", "5991.T",
        "7276.T", "7282.T", "7313.T", "3116.T", "7240.T",
        "GT", "APTV", "BWA", "LEA", "MGA", "ALV", "GNTX", "VC",
        "DAN", "THRM",
    ],
    # Mitsubishi UFJ: Japanese banking, megabanks through regionals, plus
    # the holding companies that several regionals reorganised into. Kept
    # domestic -- bank accounting and regulation do not travel well across
    # jurisdictions.
    "8306.T": [
        "8316.T", "8411.T", "8308.T", "7182.T", "8309.T", "8304.T",
        "8331.T", "8358.T", "8359.T", "8377.T", "8386.T", "8388.T",
        "8418.T", "7186.T", "7167.T", "8334.T", "8524.T",
        "5831.T", "5844.T", "7337.T", "5832.T", "5830.T",
    ],
    # Nippon Yusen: marine shipping is global and thinly listed in Tokyo,
    # so the group spans Japanese, US, Greek and Danish listings. Dry bulk
    # and tankers are both included; the industry is cyclical in different
    # phases but the accounting is comparable.
    "9101.T": [
        "9104.T", "9107.T", "9110.T", "9115.T", "9119.T",
        "ZIM", "MATX", "SBLK", "DAC", "GSL", "CMRE", "NMM", "GNK",
        "KEX", "SFL", "MAERSK-B.CO", "2343.HK", "1919.HK",
        "TNK", "INSW", "DHT", "FRO", "STNG", "NAT", "PANL",
    ],
    # NVIDIA: US-listed semiconductors, designers and equipment makers.
    "NVDA": [
        "AMD", "INTC", "AVGO", "QCOM", "TXN", "MU", "ADI", "MRVL",
        "NXPI", "ON", "SWKS", "MCHP", "AMAT", "LRCX", "KLAC", "TSM",
        "ARM", "MPWR", "QRVO", "LSCC", "RMBS", "CRUS",
    ],
    # Shopify: application and infrastructure software. The e-commerce
    # marketplaces Shopify is often compared to (Etsy, eBay) classify as
    # Consumer Cyclical and are correctly excluded from a sector-neutral
    # group, however close the businesses look.
    "SHOP": [
        "CRM", "NOW", "INTU", "ADBE", "WDAY", "HUBS", "TEAM", "DDOG",
        "SNOW", "ZM", "DOCU", "BILL", "TOST", "WIX", "GDDY",
        "MNDY", "PCTY", "PAYC",
        "VEEV", "ZS", "OKTA", "TWLO", "NET", "MDB", "ESTC", "PATH",
    ],
}


# Sector screens: the same two-stage screen run over a sector the book does
# not hold, rather than over a holding's peers. Kept apart from PEER_GROUPS
# so running one never changes the holdings' universe or its results.
#
# Verification is stricter than for PEER_GROUPS. "Industrials" alone would
# admit machinery, defence and staffing firms, so a candidate must also
# report one of the listed industries. The groups the screen ranks within
# are those reported industries, not anything assigned here: a railroad is
# ranked against railroads, an airline against airlines.
#
# Scope follows the GICS Transportation industry group (air freight and
# logistics, airlines, marine, ground transport, transport infrastructure).
# US and Japanese listings, plus the European logistics majors; ADRs are
# listed only where the company reports in dollars, since the screen
# withholds any name whose reporting and trading currencies differ.
SECTOR_SCREENS: dict[str, dict] = {
    "transport": {
        "label": "Transport & logistics",
        "sector": "Industrials",
        "industries": [
            "Railroads", "Trucking", "Integrated Freight & Logistics",
            "Airlines", "Airports & Air Services", "Marine Shipping",
        ],
        "candidates": [
            # Railroads: US and Canadian Class I, JR group, Japanese private railways.
            "UNP", "CSX", "NSC", "CP", "CNI",
            "9020.T", "9021.T", "9022.T", "9142.T", "9005.T", "9001.T",
            "9007.T", "9008.T", "9009.T", "9041.T", "9042.T", "9044.T", "9048.T",
            # Trucking and parcel.
            "ODFL", "SAIA", "XPO", "KNX", "JBHT", "WERN", "ARCB", "SNDR",
            "HTLD", "MRTN", "TFII",
            "9064.T", "9143.T", "9076.T", "9075.T", "9069.T", "9090.T",
            "9072.T", "9070.T", "9068.T", "9066.T", "9065.T",
            # Freight forwarding, contract logistics, warehousing.
            "UPS", "FDX", "CHRW", "EXPD", "GXO", "HUBG", "FWRD", "RLGT",
            "9147.T", "9301.T", "9302.T", "9303.T", "9364.T",
            "DSV.CO", "DHL.DE", "KNIN.SW",
            # Airlines and airports.
            "DAL", "UAL", "LUV", "AAL", "ALK", "JBLU", "SKYW", "ALGT",
            "9201.T", "9202.T", "9706.T",
            # Marine shipping: Nippon Yusen and its existing peer group.
            "9101.T", *PEER_GROUPS["9101.T"],
        ],
    },
}


def sector_universe(name: str) -> list[str]:
    """Every candidate ticker in one sector screen."""
    return sorted(set(SECTOR_SCREENS[name]["candidates"]))


def universe() -> list[str]:
    """Every ticker the screen touches: holdings plus all candidate peers."""
    out: set[str] = set(PEER_GROUPS)
    for peers in PEER_GROUPS.values():
        out |= set(peers)
    return sorted(out)
