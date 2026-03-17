"""
bls_ces.py
Fetches Current Employment Statistics (CES) for NY State from BLS API.
Produces employment levels by supersector; computes indexed series for
"Jobs Index by Industry" and "Change in Number of Jobs by Industry" charts.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))

import pandas as pd
import numpy as np
from datetime import datetime
from scripts.fetchers.utils import bls_post, bls_to_df, save_json
from config import BLS_API_KEY, CES_SERIES, OUTPUT_FILES

START_YEAR = 2018   # gives enough history for 5-yr index chart
END_YEAR   = datetime.now().year

def fetch():
    print("CES: fetching from BLS API...")
    series_ids = list(CES_SERIES.keys())
    raw = bls_post(series_ids, START_YEAR, END_YEAR, BLS_API_KEY)
    df  = bls_to_df(raw, CES_SERIES)

    if df.empty:
        print("  CES: no data returned")
        save_json([], OUTPUT_FILES["bls_ces"])
        return []

    # CES values are in thousands of jobs
    wide = df.pivot_table(index="time", columns="series", values="value", aggfunc="first")
    wide.columns.name = None

    # ── Index each series to its value at the reference date ────────────────
    # Reference: 5 years before latest data point (matching Tableau "Five Year" default)
    latest = wide.index.max()
    ref_date = latest - pd.DateOffset(years=5)
    # Find nearest available date ≥ ref_date
    available = wide.index[wide.index >= ref_date]
    ref_date = available.min() if len(available) > 0 else wide.index.min()

    industry_cols = [c for c in wide.columns if c not in ["Total Nonfarm","Total Private","Government"]]

    for col in wide.columns:
        ref_val = wide.loc[ref_date, col] if ref_date in wide.index else np.nan
        if pd.notna(ref_val) and ref_val != 0:
            wide[f"{col} Index"] = (wide[col] / ref_val) - 1.0
        else:
            wide[f"{col} Index"] = np.nan

    # ── Change in jobs: latest month vs same month prior year ───────────────
    change_records = []
    last_row_idx = wide.index.max()
    one_yr_ago   = last_row_idx - pd.DateOffset(months=12)
    avail_prior  = wide.index[wide.index <= one_yr_ago]
    prior_idx    = avail_prior.max() if len(avail_prior) > 0 else None

    if prior_idx is not None:
        for col in industry_cols:
            curr_val  = wide.loc[last_row_idx, col] if col in wide.columns else np.nan
            prior_val = wide.loc[prior_idx, col] if col in wide.columns else np.nan
            change_k  = curr_val - prior_val if (pd.notna(curr_val) and pd.notna(prior_val)) else None
            change_records.append({
                "industry": col,
                "current_value": curr_val * 1000 if pd.notna(curr_val) else None,
                "prior_value":   prior_val * 1000 if pd.notna(prior_val) else None,
                "change":        change_k * 1000 if change_k is not None else None,
                "as_of":         last_row_idx.strftime("%B %Y"),
            })

    wide = wide.reset_index()
    wide["time"] = wide["time"].dt.strftime("%Y-%m-%d")
    records = wide.replace({np.nan: None}).to_dict(orient="records")

    result = {
        "monthly": records,
        "changes": change_records,
        "reference_date": ref_date.strftime("%Y-%m-%d"),
        "latest_date": latest.strftime("%Y-%m-%d"),
    }
    save_json(result, OUTPUT_FILES["bls_ces"])
    print(f"  CES: {len(records)} monthly records, {len(change_records)} industry change records.")
    return result

if __name__ == "__main__":
    fetch()
