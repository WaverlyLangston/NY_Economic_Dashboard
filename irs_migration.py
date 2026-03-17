"""
irs_migration.py
Downloads IRS SOI state-to-state migration files and extracts NY flows.
Produces: net domestic migration by year (returns and individuals),
plus top origin/destination states.
No API key needed — direct file downloads.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))

import pandas as pd
import numpy as np
import requests
from io import StringIO
from scripts.fetchers.utils import save_json
from config import IRS_BASE_URL, IRS_YEARS, NY_FIPS_IRS, OUTPUT_FILES

def _download_flow(year_code, direction):
    """Download and return IRS migration CSV for one year and direction (inflow/outflow)."""
    fname = f"state{direction}{year_code}.csv"
    url   = f"{IRS_BASE_URL}/{fname}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text), encoding="latin-1", low_memory=False)
        return df
    except Exception as e:
        print(f"  IRS {direction} {year_code} warning: {e}")
        return None

def fetch():
    print("IRS: downloading migration files...")
    annual_net = []       # net migration by year for bar chart
    top_flows  = []       # top states flowing to/from NY for most recent year

    for year_code, year_label in IRS_YEARS:
        in_df  = _download_flow(year_code, "inflow")
        out_df = _download_flow(year_code, "outflow")

        if in_df is None or out_df is None:
            continue

        # Standardize column names (vary slightly across vintages)
        def clean_cols(df):
            df.columns = [c.strip().upper() for c in df.columns]
            return df
        in_df  = clean_cols(in_df)
        out_df = clean_cols(out_df)

        # Identify the FIPS columns (Y1 = origin, Y2 = destination)
        # Inflow: Y2 = NY (destination), Y1 = origin state
        # Outflow: Y1 = NY (origin), Y2 = destination state
        y2_col = next((c for c in in_df.columns if "Y2" in c and "FIPS" in c), None)
        y1_col = next((c for c in in_df.columns if "Y1" in c and "FIPS" in c), None)
        n1_col = next((c for c in in_df.columns if c == "N1"), "N1")  # returns
        n2_col = next((c for c in in_df.columns if c == "N2"), "N2")  # individuals

        if y2_col is None or y1_col is None:
            print(f"  IRS {year_code}: unexpected column names — skipping")
            continue

        # Filter: inflow to NY (Y2_STATEFIPS == 36), exclude totals (96-99, 57)
        exclude = {96, 97, 98, 99, 57}
        in_ny = in_df[
            (in_df[y2_col] == NY_FIPS_IRS) &
            (~in_df[y1_col].isin(exclude))
        ].copy()
        out_ny = out_df[
            (out_df[y1_col] == NY_FIPS_IRS) &
            (~out_df[y2_col].isin(exclude))
        ].copy()

        def to_num(s):
            return pd.to_numeric(s, errors="coerce").fillna(0)

        # Aggregates (suppress -1 coded values)
        in_n1  = to_num(in_ny[n1_col]).clip(lower=0).sum()
        out_n1 = to_num(out_ny[n1_col]).clip(lower=0).sum()
        net_n1 = in_n1 - out_n1

        in_n2  = to_num(in_ny[n2_col]).clip(lower=0).sum()
        out_n2 = to_num(out_ny[n2_col]).clip(lower=0).sum()
        net_n2 = in_n2 - out_n2

        annual_net.append({
            "year_label": year_label,
            "year": int("20" + year_code[2:4]),   # approximate end year
            "inflow_returns":    int(in_n1),
            "outflow_returns":   int(out_n1),
            "net_returns":       int(net_n1),
            "inflow_people":     int(in_n2),
            "outflow_people":    int(out_n2),
            "net_people":        int(net_n2),
            "source": "IRS",
        })

        # For the most recent year also compute top states
        if year_code == IRS_YEARS[-1][0]:
            name_col = next((c for c in in_ny.columns if "NAME" in c and "Y1" in c), None)
            if name_col:
                in_ny["net_n1"]  = to_num(in_ny[n1_col]).clip(lower=0)
                top_in = in_ny.nlargest(10, "net_n1")[[name_col,"net_n1"]].copy()
                top_in.columns = ["state","inflow_returns"]

                out_name_col = next((c for c in out_ny.columns if "NAME" in c and "Y2" in c), None)
                if out_name_col:
                    out_ny["net_n1"] = to_num(out_ny[n1_col]).clip(lower=0)
                    top_out = out_ny.nlargest(10,"net_n1")[[out_name_col,"net_n1"]].copy()
                    top_out.columns = ["state","outflow_returns"]
                    top_flows = {
                        "year": year_label,
                        "top_inflow":  top_in.to_dict(orient="records"),
                        "top_outflow": top_out.to_dict(orient="records"),
                    }

    result = {"annual_net": annual_net, "top_flows": top_flows}
    save_json(result, OUTPUT_FILES["irs_migration"])
    print(f"  IRS migration: {len(annual_net)} years saved.")
    return result

if __name__ == "__main__":
    fetch()
