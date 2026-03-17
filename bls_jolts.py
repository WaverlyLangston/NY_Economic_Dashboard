"""
bls_jolts.py
Fetches JOLTS data for NY State and US from BLS API.
Produces: NY levels chart + NY/US rates chart with dropdown.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))

import pandas as pd
import numpy as np
from datetime import datetime
from scripts.fetchers.utils import bls_post, bls_to_df, save_json
from config import BLS_API_KEY, JOLTS_SERIES, OUTPUT_FILES

START_YEAR = 2016
END_YEAR   = datetime.now().year

RATE_COLS = [c for c in JOLTS_SERIES.values() if "Rate" in c or "Ratio" in c]
LEVEL_COLS = [c for c in JOLTS_SERIES.values() if "Level" in c]

def fetch():
    print("JOLTS: fetching from BLS API...")
    series_ids = list(JOLTS_SERIES.keys())
    raw = bls_post(series_ids, START_YEAR, END_YEAR, BLS_API_KEY)
    df  = bls_to_df(raw, JOLTS_SERIES)

    if df.empty:
        print("  JOLTS: no data returned — NY state JOLTS may be limited; saving empty.")
        save_json({"monthly": [], "note": "NY state JOLTS data not available for this period."}, OUTPUT_FILES["bls_jolts"])
        return {}

    wide = df.pivot_table(index="time", columns="series", values="value", aggfunc="first")
    wide.columns.name = None

    # Rates are in percent → convert to decimal
    for c in RATE_COLS:
        if c in wide.columns:
            wide[c] = wide[c] / 100.0

    # Levels are in thousands → convert to actual counts
    for c in LEVEL_COLS:
        if c in wide.columns:
            wide[c] = wide[c] * 1000

    wide = wide.reset_index()
    wide["time"] = wide["time"].dt.strftime("%Y-%m-%d")
    records = wide.replace({np.nan: None}).to_dict(orient="records")

    result = {"monthly": records}
    save_json(result, OUTPUT_FILES["bls_jolts"])
    print(f"  JOLTS: {len(records)} monthly records saved.")
    return result

if __name__ == "__main__":
    fetch()
