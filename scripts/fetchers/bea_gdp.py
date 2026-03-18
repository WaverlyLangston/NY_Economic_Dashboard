"""
bea_gdp.py  –  BEA Real GDP fetcher (fixed)
Uses LineCode=All to get all industries in ONE API call instead of looping,
which avoids rate-limit errors and the missing-Results-key crash.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
import numpy as np
from scripts.fetchers.utils import safe_get, save_json
from config import (BEA_BASE_URL, BEA_API_KEY, PEER_STATES_BEA,
                    NY_GEO_BEA, OUTPUT_FILES)

def _bea(params):
    params["UserID"]       = BEA_API_KEY
    params["ResultFormat"] = "JSON"
    try:
        r    = safe_get(BEA_BASE_URL, params=params)
        body = r.json().get("BEAAPI", {}).get("Results", {})
        if "Error" in body:
            print(f"  BEA error: {body['Error']}")
            return []
        return body.get("Data", [])
    except Exception as e:
        print(f"  BEA request warning: {e}")
        return []

# ── 1. Peer-state quarterly real GDP ─────────────────────────────────────────
def fetch_peer_gdp():
    print("BEA: fetching peer-state quarterly GDP (SQGDP9)...")
    geo = ",".join(PEER_STATES_BEA.keys())
    data = _bea({"method": "GetData", "datasetname": "Regional",
                 "TableName": "SQGDP9", "LineCode": "1",
                 "Year": "ALL", "GeoFips": geo})
    if not data:
        return []

    df = pd.DataFrame(data)
    df = df[df["GeoFips"].isin(PEER_STATES_BEA.keys())].copy()
    df["GeoName"]   = df["GeoFips"].map(PEER_STATES_BEA)
    df["DataValue"] = pd.to_numeric(df["DataValue"].str.replace(",", ""), errors="coerce")

    # Convert "2023Q3" → datetime safely
    def parse_quarter(s):
        try:
            yr, q = s.split("Q")
            month = (int(q) - 1) * 3 + 1
            return pd.Timestamp(year=int(yr), month=month, day=1)
        except Exception:
            return pd.NaT

    df["time"] = df["TimePeriod"].apply(parse_quarter)
    df = df.dropna(subset=["time", "DataValue"])

    wide = df.pivot_table(index="time", columns="GeoName",
                          values="DataValue", aggfunc="first").sort_index()
    wide = wide.reset_index()
    wide["time"] = wide["time"].dt.to_period("Q").astype(str)  # "2023Q3"
    records = wide.replace({np.nan: None}).to_dict(orient="records")
    print(f"  BEA peer GDP: {len(records)} quarterly records")
    return records

# ── 2. NY quarterly GDP by industry  (LineCode=All → one API call) ───────────
def fetch_ny_industry_gdp():
    print("BEA: fetching NY quarterly GDP by industry (SQGDP9, LineCode=All)...")
    data = _bea({"method": "GetData", "datasetname": "Regional",
                 "TableName": "SQGDP9", "LineCode": "All",
                 "Year": "LAST10", "GeoFips": NY_GEO_BEA})
    if not data:
        print("  BEA quarterly industry: no data returned")
        return {}

    df = pd.DataFrame(data)
    df["DataValue"] = pd.to_numeric(df["DataValue"].str.replace(",", ""), errors="coerce")

    def parse_quarter(s):
        try:
            yr, q = s.split("Q")
            month = (int(q) - 1) * 3 + 1
            return pd.Timestamp(year=int(yr), month=month, day=1)
        except Exception:
            return pd.NaT

    df["time"] = df["TimePeriod"].apply(parse_quarter)
    df = df.dropna(subset=["time", "DataValue"])

    # Skip aggregates and very noisy rows
    skip = {"All industry total", "Private industries"}
    result = {}
    for desc, grp in df.groupby("Description"):
        if desc.strip() in skip:
            continue
        grp = grp.sort_values("time")
        result[desc.strip()] = {
            "times":  [t.to_period("Q").strftime("%YQ%q") for t in grp["time"]],
            "values": grp["DataValue"].tolist(),
        }
    print(f"  BEA NY quarterly by industry: {len(result)} industries")
    return result

# ── 3. NY annual GDP by industry  (LineCode=All → one API call) ──────────────
def fetch_ny_annual_industry():
    print("BEA: fetching NY annual GDP by industry (SAGDP9N, LineCode=All)...")
    data = _bea({"method": "GetData", "datasetname": "Regional",
                 "TableName": "SAGDP9N", "LineCode": "All",
                 "Year": "LAST5", "GeoFips": NY_GEO_BEA})
    if not data:
        print("  BEA annual industry: no data returned")
        return {}

    df = pd.DataFrame(data)
    df["DataValue"] = pd.to_numeric(df["DataValue"].str.replace(",", ""), errors="coerce")
    df["year"]      = pd.to_numeric(df["TimePeriod"], errors="coerce")
    df              = df.dropna(subset=["year", "DataValue"])
    df["year"]      = df["year"].astype(int)

    latest_year = df["year"].max()
    latest      = df[df["year"] == latest_year].copy()
    latest["industry"] = latest["Description"].str.strip()

    total_row = latest[latest["industry"] == "All industry total"]
    if not total_row.empty:
        total_val      = float(total_row["DataValue"].values[0])
        latest["share"] = latest["DataValue"] / total_val
    else:
        latest["share"] = np.nan

    # Drop pure aggregates for the bar chart
    skip = {"All industry total", "Private industries"}
    latest = latest[~latest["industry"].isin(skip)]
    latest = latest.sort_values("DataValue", ascending=False)

    records = latest[["industry", "DataValue", "share"]].replace({np.nan: None}).to_dict(orient="records")
    print(f"  BEA annual industry: {len(records)} industries for {latest_year}")
    return {"year": int(latest_year), "data": records}

# ── Orchestrator ──────────────────────────────────────────────────────────────
def fetch():
    peer   = fetch_peer_gdp()
    ny_q   = fetch_ny_industry_gdp()
    ny_ann = fetch_ny_annual_industry()

    save_json(peer, OUTPUT_FILES["bea_gdp"])
    save_json({"quarterly_by_industry": ny_q, "annual_by_industry": ny_ann},
              OUTPUT_FILES["bea_gdp_industry"])
    print("  BEA: all GDP data saved.")
    return peer

if __name__ == "__main__":
    fetch()
