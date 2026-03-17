"""
bea_gdp.py
Fetches BEA Real GDP data:
 1. Peer-state quarterly GDP (SQGDP9) for NY, MA, NJ, RI, US — indexed to base period
 2. NY quarterly GDP by industry (SQGDP9, all line codes) — highest/lowest growth chart
 3. NY annual GDP by industry (SAGDP9N) — most recent year for stacked bar chart
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))

import pandas as pd
import numpy as np
import time
from scripts.fetchers.utils import safe_get, save_json
from config import (BEA_BASE_URL, BEA_API_KEY, PEER_STATES_BEA,
                    NY_GEO_BEA, BEA_INDUSTRY_CODES, OUTPUT_FILES)

def _bea_get(params):
    params["UserID"] = BEA_API_KEY
    params["ResultFormat"] = "JSON"
    try:
        r = safe_get(BEA_BASE_URL, params=params)
        body = r.json()["BEAAPI"]["Results"]
        if "Error" in body:
            print(f"  BEA error: {body['Error']}")
            return []
        return body.get("Data", [])
    except Exception as e:
        print(f"  BEA request warning: {e}")
        return []

def fetch_peer_gdp():
    """Quarterly real GDP for peer states — indexed to 5 years prior."""
    print("BEA: fetching peer-state quarterly GDP (SQGDP9)...")
    geo_list = ",".join(PEER_STATES_BEA.keys())
    data = _bea_get({
        "method":      "GetData",
        "datasetname": "Regional",
        "TableName":   "SQGDP9",
        "LineCode":    "1",
        "Year":        "ALL",
        "GeoFips":     geo_list,
    })
    if not data:
        return []

    df = pd.DataFrame(data)
    df = df[df["GeoFips"].isin(PEER_STATES_BEA.keys())].copy()
    df["GeoName"] = df["GeoFips"].map(PEER_STATES_BEA)
    df["DataValue"] = pd.to_numeric(df["DataValue"].str.replace(",",""), errors="coerce")
    df["time"] = pd.to_datetime(df["TimePeriod"])   # e.g. "2023Q3" → auto-parsed

    # Calculate percent change vs 5-years-ago (20 quarters)
    wide = df.pivot_table(index="time", columns="GeoName", values="DataValue", aggfunc="first")
    wide = wide.sort_index()

    # Index: % change from start of each time-frame window
    # We'll provide raw values; the chart builder will compute the index
    wide = wide.reset_index()
    wide["time"] = wide["time"].dt.to_period("Q").astype(str)   # "2023Q3"

    records = wide.replace({np.nan: None}).to_dict(orient="records")
    print(f"  BEA peer GDP: {len(records)} quarterly records")
    return records

def fetch_ny_industry_gdp():
    """Quarterly real GDP for NY by all industry line codes — for growth chart."""
    print("BEA: fetching NY quarterly GDP by industry (SQGDP9)...")
    records_by_industry = {}

    for lc, label in BEA_INDUSTRY_CODES.items():
        data = _bea_get({
            "method":      "GetData",
            "datasetname": "Regional",
            "TableName":   "SQGDP9",
            "LineCode":    lc,
            "Year":        "LAST10",
            "GeoFips":     NY_GEO_BEA,
        })
        if data:
            df = pd.DataFrame(data)
            df["DataValue"] = pd.to_numeric(df["DataValue"].str.replace(",",""), errors="coerce")
            df["time"] = pd.to_datetime(df["TimePeriod"])
            df = df.sort_values("time").dropna(subset=["DataValue"])
            series = df.set_index("time")["DataValue"]
            records_by_industry[label] = {
                "times": [t.to_period("Q").strftime("%YQ%q") for t in series.index],
                "values": series.tolist(),
            }
        time.sleep(0.7)   # stay under BEA 100-req/min limit

    print(f"  BEA NY industry quarterly: {len(records_by_industry)} industries")
    return records_by_industry

def fetch_ny_annual_industry():
    """Annual real GDP for NY by all industry — most recent year, for stacked bar."""
    print("BEA: fetching NY annual GDP by industry (SAGDP9N)...")
    all_data = []
    for lc, label in BEA_INDUSTRY_CODES.items():
        data = _bea_get({
            "method":      "GetData",
            "datasetname": "Regional",
            "TableName":   "SAGDP9N",
            "LineCode":    lc,
            "Year":        "LAST5",
            "GeoFips":     NY_GEO_BEA,
        })
        if data:
            df = pd.DataFrame(data)
            df["DataValue"] = pd.to_numeric(df["DataValue"].str.replace(",",""), errors="coerce")
            df["year"] = df["TimePeriod"].astype(int)
            df["industry"] = label
            all_data.append(df[["year","industry","DataValue"]].dropna())
        time.sleep(0.7)

    if not all_data:
        return []
    combined = pd.concat(all_data, ignore_index=True)
    latest_year = combined["year"].max()
    latest = combined[combined["year"] == latest_year].copy()

    # Calculate share of total
    total_row = latest[latest["industry"] == "All industry total"]
    if not total_row.empty:
        total_val = float(total_row["DataValue"].values[0])
        latest["share"] = latest["DataValue"] / total_val
    else:
        latest["share"] = np.nan

    latest = latest.sort_values("DataValue", ascending=False)
    records = latest.replace({np.nan: None}).to_dict(orient="records")
    print(f"  BEA NY annual industry: {len(records)} industries for {latest_year}")
    return {"year": int(latest_year), "data": records}

def fetch():
    peer    = fetch_peer_gdp()
    ny_ind  = fetch_ny_industry_gdp()
    ny_ann  = fetch_ny_annual_industry()

    save_json(peer,   OUTPUT_FILES["bea_gdp"])
    save_json({"quarterly_by_industry": ny_ind, "annual_by_industry": ny_ann},
              OUTPUT_FILES["bea_gdp_industry"])
    print("  BEA: all GDP data saved.")
    return peer

if __name__ == "__main__":
    fetch()
