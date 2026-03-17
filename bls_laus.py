"""
bls_laus.py
Fetches LAUS and national CPS labor force data for NY and US from BLS API.
Produces: NY labor force levels + unemployment levels (dual axis chart),
and NY vs US rates (unemployment rate, LFPR, E-P ratio) with dropdown.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))

import pandas as pd
import numpy as np
from datetime import datetime
from scripts.fetchers.utils import bls_post, bls_to_df, save_json
from config import BLS_API_KEY, LAUS_SERIES, OUTPUT_FILES

START_YEAR = 2016
END_YEAR   = datetime.now().year

def fetch():
    print("LAUS: fetching from BLS API...")
    series_ids = list(LAUS_SERIES.keys())
    raw = bls_post(series_ids, START_YEAR, END_YEAR, BLS_API_KEY)
    df  = bls_to_df(raw, LAUS_SERIES)

    if df.empty:
        print("  LAUS: no data returned")
        save_json([], OUTPUT_FILES["bls_laus"])
        return []

    # Pivot to wide format for easy charting
    wide = df.pivot_table(index="time", columns="series", values="value", aggfunc="first")
    wide.columns.name = None

    # Convert rates from whole-number percent → decimal (match original script)
    rate_cols = [c for c in wide.columns if any(k in c for k in
                 ["Rate","Ratio","Participation"])]
    for c in rate_cols:
        if c in wide.columns:
            wide[c] = wide[c] / 100.0

    # Convert levels to actual numbers (LAUS reports in units, not thousands)
    # Employment-Population Ratio and LFPR are already ratios after /100

    wide = wide.reset_index()
    wide["time"] = wide["time"].dt.strftime("%Y-%m-%d")

    records = wide.replace({np.nan: None}).to_dict(orient="records")
    save_json(records, OUTPUT_FILES["bls_laus"])
    print(f"  LAUS: {len(records)} monthly records saved.")
    return records

if __name__ == "__main__":
    fetch()
