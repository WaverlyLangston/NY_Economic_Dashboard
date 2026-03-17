"""
census_pep.py
Fetches Census Population Estimates for NY and US.
Outputs: (1) annual population totals, (2) age-group breakdown by year.
Stitches together 2000-2010, 2010-2020, 2020-2023 vintages.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))

import pandas as pd
import numpy as np
import requests
from io import BytesIO
from scripts.fetchers.utils import safe_get, save_json
from config import PEP_URLS, CENSUS_BASE_URL, CENSUS_API_KEY, OUTPUT_FILES

KEEP_STATES = ["New York", "United States"]

def _clean_pop_col(s):
    return pd.to_numeric(s.astype(str).str.replace(",","").str.strip(), errors="coerce")

def fetch_population_totals():
    """Return wide DataFrame: index=Geography, columns=year strings."""
    dfs = []

    # ── 2000-2010 intercensal CSV ─────────────────────────────────
    print("PEP: downloading 2000-2010 CSV...")
    try:
        r = safe_get(PEP_URLS["2000_2010"])
        d00 = pd.read_csv(BytesIO(r.content), header=3, encoding="latin-1")
        d00.rename(columns={"Unnamed: 0": "Geography"}, inplace=True)
        d00["Geography"] = d00["Geography"].str.replace(".", "", regex=False).str.strip()
        d00 = d00[d00["Geography"].isin(KEEP_STATES)].copy()
        year_cols = [c for c in d00.columns if str(c).isdigit() and 2001 <= int(c) <= 2009]
        d00 = d00[["Geography"] + year_cols]
        for c in year_cols:
            d00[c] = _clean_pop_col(d00[c])
        dfs.append(d00)
    except Exception as e:
        print(f"  PEP 2000-2010 warning: {e}")

    # ── 2010-2020 Excel ───────────────────────────────────────────
    print("PEP: downloading 2010-2020 Excel...")
    try:
        r = safe_get(PEP_URLS["2010_2020"])
        d10 = pd.read_excel(BytesIO(r.content), header=3)
        d10.rename(columns={"Unnamed: 0": "Geography"}, inplace=True)
        d10["Geography"] = d10["Geography"].str.replace(".", "", regex=False).str.strip()
        d10 = d10[d10["Geography"].isin(KEEP_STATES)].copy()
        year_cols = [c for c in d10.columns if str(c).isdigit() and 2010 <= int(c) <= 2019]
        d10 = d10[["Geography"] + year_cols]
        for c in year_cols:
            d10[c] = _clean_pop_col(d10[c])
        dfs.append(d10)
    except Exception as e:
        print(f"  PEP 2010-2020 warning: {e}")

    # ── 2020-2023 Excel ───────────────────────────────────────────
    print("PEP: downloading 2020-2023 Excel...")
    try:
        r = safe_get(PEP_URLS["2020_2023"])
        d20 = pd.read_excel(BytesIO(r.content), header=3)
        d20.rename(columns={"Unnamed: 0": "Geography"}, inplace=True)
        d20["Geography"] = d20["Geography"].str.replace(".", "", regex=False).str.strip()
        d20 = d20[d20["Geography"].isin(KEEP_STATES)].copy()
        year_cols = [c for c in d20.columns if str(c).isdigit() and 2020 <= int(c) <= 2023]
        d20 = d20[["Geography"] + year_cols]
        for c in year_cols:
            d20[c] = _clean_pop_col(d20[c])
        dfs.append(d20)
    except Exception as e:
        print(f"  PEP 2020-2023 warning: {e}")

    if not dfs:
        return pd.DataFrame()

    merged = dfs[0]
    for d in dfs[1:]:
        merged = merged.merge(d, on="Geography", how="outer")
    merged = merged.sort_values("Geography").reset_index(drop=True)
    return merged

def fetch_age_breakdown():
    """
    Fetch age-group population by year for NY from PEP API.
    Returns list of dicts: {year, age_group, population}
    Age groups match original Tableau: Under 5, 5-13, 14-17, 18-24, 25-44, 45-64, 65+
    """
    print("PEP: fetching age breakdown from API...")
    age_records = []

    # Use PEPAGESEX dataset for historical age/sex estimates
    # Vintage 2019 for 2010-2019, vintage 2023 for 2020-2023
    vintages = [
        ("2019", "pep/charv", range(2010, 2020)),
        ("2023", "pep/charv", range(2020, 2024)),
    ]

    for vintage, endpoint, years in vintages:
        url = f"{CENSUS_BASE_URL}/{vintage}/{endpoint}"
        for year in years:
            params = {
                "get": "POP,AGEGROUP,NAME",
                "for": "state:36",
                "YEAR": year,
            }
            if CENSUS_API_KEY:
                params["key"] = CENSUS_API_KEY
            try:
                r = safe_get(url, params=params)
                data = r.json()
                cols = data[0]
                for row in data[1:]:
                    rec = dict(zip(cols, row))
                    pop_val = int(rec.get("POP", 0) or 0)
                    ag = int(rec.get("AGEGROUP", -1) or -1)
                    if ag < 0 or pop_val <= 0:
                        continue
                    # AGEGROUP codes: 0=all, 1=0-4, 2=5-9, 3=10-14, 4=15-19,
                    # 5=20-24, 6=25-29, 7=30-34, 8=35-39, 9=40-44, 10=45-49,
                    # 11=50-54, 12=55-59, 13=60-64, 14=65-69, 15=70-74,
                    # 16=75-79, 17=80-84, 18=85+, 99=all ages
                    age_records.append({"year": year, "agegroup_code": ag, "population": pop_val})
            except Exception as e:
                print(f"  PEP age {year} warning: {e}")

    # Aggregate into the 7 Tableau age buckets
    bucket_map = {
        1: "Under 5",
        2: "5 To 13", 3: "5 To 13",
        4: "14 To 17",
        5: "18 To 24", 6: "18 To 24",  # partial, but best approximation
        7: "25 To 44", 8: "25 To 44", 9: "25 To 44", 10: "25 To 44",
        11: "45 To 64", 12: "45 To 64", 13: "45 To 64", 14: "45 To 64",
        15: "65 And Over", 16: "65 And Over", 17: "65 And Over", 18: "65 And Over",
    }
    df = pd.DataFrame(age_records)
    if df.empty:
        return []
    df = df[df["agegroup_code"].isin(bucket_map)]
    df["age_group"] = df["agegroup_code"].map(bucket_map)
    agg = df.groupby(["year","age_group"])["population"].sum().reset_index()
    return agg.to_dict(orient="records")

def fetch():
    pop_df = fetch_population_totals()

    # Save population totals as long-format list of records
    pop_records = []
    if not pop_df.empty:
        year_cols = [c for c in pop_df.columns if c != "Geography"]
        for _, row in pop_df.iterrows():
            geo = row["Geography"]
            for yr in year_cols:
                val = row[yr]
                if pd.notna(val) and val > 0:
                    pop_records.append({"geography": geo, "year": int(yr), "population": int(val)})
    save_json(pop_records, OUTPUT_FILES["pep_population"])
    print(f"  PEP population: {len(pop_records)} records")

    # Save age breakdown
    age_records = fetch_age_breakdown()
    save_json(age_records, OUTPUT_FILES["pep_age"])
    print(f"  PEP age: {len(age_records)} records")

    return pop_df  # return wide DF for other fetchers to use

if __name__ == "__main__":
    fetch()
