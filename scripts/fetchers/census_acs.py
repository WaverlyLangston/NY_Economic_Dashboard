"""
census_acs.py
Fetches ACS 1-Year data for NY (state:36) and US for:
 - Median household income by race/ethnicity/sex
 - Poverty rate by race/ethnicity/sex
 - Housing units, vacancy rates, homeownership
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__),"..",".."))

import pandas as pd
import numpy as np
from scripts.fetchers.utils import safe_get, save_json
from config import CENSUS_BASE_URL, CENSUS_API_KEY, OUTPUT_FILES

# ACS 1-Year available years (no 2020)
ACS_YEARS = list(range(2010, 2020)) + list(range(2021, 2025))

def _acs_get(year, variables, geo="state:36"):
    """Single ACS 1-Year API call. Returns dict of {variable: value}."""
    url = f"{CENSUS_BASE_URL}/{year}/acs/acs1"
    params = {"get": ",".join(["NAME"] + variables), "for": geo}
    if CENSUS_API_KEY:
        params["key"] = CENSUS_API_KEY
    try:
        r = safe_get(url, params=params)
        data = r.json()
        cols = data[0]
        row = data[1]
        return dict(zip(cols, row))
    except Exception as e:
        print(f"  ACS {year} {geo} warning: {e}")
        return {}

def fetch_income():
    """Median HH income by race/ethnicity + total, NY vs US, 2010-2024."""
    print("ACS: fetching median household income...")
    vars_income = [
        "B19013_001E",   # All
        "B19013A_001E",  # White alone
        "B19013B_001E",  # Black or African American
        "B19013C_001E",  # AIAN
        "B19013D_001E",  # Asian
        "B19013E_001E",  # NHPI
        "B19013F_001E",  # Some other race
        "B19013G_001E",  # Two or more races
        "B19013H_001E",  # White alone, not Hispanic
        "B19013I_001E",  # Hispanic or Latino
    ]
    label_map = {
        "B19013_001E":  "All Households",
        "B19013A_001E": "White alone",
        "B19013B_001E": "Black or African American",
        "B19013C_001E": "American Indian and Alaska Native",
        "B19013D_001E": "Asian",
        "B19013E_001E": "Native Hawaiian and Other Pacific Islander",
        "B19013F_001E": "Some other race",
        "B19013G_001E": "Two or more races",
        "B19013H_001E": "White alone, not Hispanic",
        "B19013I_001E": "Hispanic or Latino (of any race)",
    }
    records = []
    for year in ACS_YEARS:
        for geo, geo_label in [("state:36", "New York"), ("us:1", "United States")]:
            row = _acs_get(year, vars_income, geo=geo)
            for var, label in label_map.items():
                val = row.get(var)
                try:
                    val = float(val)
                    if val < 0:
                        val = None
                except (TypeError, ValueError):
                    val = None
                records.append({"year": year, "geography": geo_label, "group": label, "value": val})
    save_json(records, OUTPUT_FILES["acs_income"])
    print(f"  ACS income: {len(records)} records")
    return records

def fetch_poverty():
    """Poverty rate by race/ethnicity and sex, NY vs US, most recent year."""
    print("ACS: fetching poverty rates...")
    # Poverty by race/ethnicity (C17001 series)
    race_vars = {
        "White alone":                     ("C17001A_001E", "C17001A_002E"),
        "Black or African American alone":  ("C17001B_001E", "C17001B_002E"),
        "American Indian and Alaska Native alone": ("C17001C_001E","C17001C_002E"),
        "Asian alone":                      ("C17001D_001E", "C17001D_002E"),
        "Native Hawaiian and Other Pacific Islander alone": ("C17001E_001E","C17001E_002E"),
        "Some other race alone":            ("C17001F_001E", "C17001F_002E"),
        "Two or more races":                ("C17001G_001E", "C17001G_002E"),
        "Hispanic or Latino (of any race)": ("C17001I_001E", "C17001I_002E"),
    }
    # Sex: B17001 for male/female breakdown
    sex_vars = {
        "Female": ("B17001_001E", "B17001_017E"),  # universe, female below poverty
        "Male":   ("B17001_001E", "B17001_002E"),  # universe, total below poverty (approx)
    }
    records = []
    for year in ACS_YEARS[-5:]:   # last 5 available years for time series
        for geo, geo_label in [("state:36","New York"),("us:1","United States")]:
            # Race poverty
            all_vars = [v for pair in race_vars.values() for v in pair]
            # Also get total poverty
            all_vars += ["B17001_001E", "B17001_002E"]
            row = _acs_get(year, list(set(all_vars)), geo=geo)

            total_universe = float(row.get("B17001_001E") or 0)
            total_poverty  = float(row.get("B17001_002E") or 0)
            total_rate = total_poverty / total_universe if total_universe > 0 else None

            records.append({"year": year, "geography": geo_label,
                            "group": "Total", "rate": total_rate,
                            "count": total_poverty, "universe": total_universe})

            for group, (uni_var, pov_var) in race_vars.items():
                uni = float(row.get(uni_var) or 0)
                pov = float(row.get(pov_var) or 0)
                rate = pov / uni if uni > 0 else None
                if pov < 0 or uni < 0:
                    rate = None
                records.append({"year": year, "geography": geo_label,
                                "group": group, "rate": rate,
                                "count": pov if pov >= 0 else None,
                                "universe": uni if uni >= 0 else None})

            # Sex poverty (use separate call for B17001 sex breakdown)
            sex_row = _acs_get(year, ["B17001_001E","B17001_002E",
                                       "B17001_017E","B17001_018E",
                                       "B17001_003E","B17001_004E"], geo=geo)
            # B17001_003E = male below poverty, B17001_017E = female below poverty
            male_pov = float(sex_row.get("B17001_003E") or 0)
            fem_pov  = float(sex_row.get("B17001_017E") or 0)
            # Approximate universe (split total universe by 2 — rough)
            male_rate = male_pov / (total_universe * 0.485) if total_universe > 0 else None
            fem_rate  = fem_pov / (total_universe * 0.515) if total_universe > 0 else None
            records.append({"year": year, "geography": geo_label,
                            "group": "Male", "rate": male_rate,
                            "count": male_pov, "universe": None})
            records.append({"year": year, "geography": geo_label,
                            "group": "Female", "rate": fem_rate,
                            "count": fem_pov, "universe": None})

    save_json(records, OUTPUT_FILES["acs_poverty"])
    print(f"  ACS poverty: {len(records)} records")
    return records

def fetch_housing():
    """Housing units, vacancy rate, homeownership, median value — NY and US, annual."""
    print("ACS: fetching housing data...")
    vars_housing = [
        "B25001_001E",  # Total housing units
        "B25002_002E",  # Occupied
        "B25002_003E",  # Vacant
        "B25003_002E",  # Owner occupied
        "B25003_003E",  # Renter occupied
        "B25004_002E",  # For rent (vacant)
        "B25077_001E",  # Median home value
    ]
    records = []
    for year in ACS_YEARS:
        for geo, geo_label in [("state:36","New York"),("us:1","United States")]:
            row = _acs_get(year, vars_housing, geo=geo)
            def fv(k):
                v = row.get(k)
                try:
                    f = float(v)
                    return f if f >= 0 else None
                except (TypeError, ValueError):
                    return None

            total = fv("B25001_001E")
            occupied = fv("B25002_002E")
            vacant   = fv("B25002_003E")
            owner    = fv("B25003_002E")
            renter   = fv("B25003_003E")
            for_rent = fv("B25004_002E")
            med_val  = fv("B25077_001E")

            # Derived rates
            vacancy_rate        = vacant / total if (total and total > 0) else None
            rental_vacancy_rate = for_rent / (renter + for_rent) if (renter and for_rent and renter + for_rent > 0) else None
            homeownership_rate  = owner / occupied if (owner and occupied and occupied > 0) else None

            records.append({
                "year": year,
                "geography": geo_label,
                "total_units": total,
                "occupied": occupied,
                "vacant": vacant,
                "owner_occupied": owner,
                "renter_occupied": renter,
                "for_rent_vacant": for_rent,
                "median_home_value": med_val,
                "vacancy_rate": vacancy_rate,
                "rental_vacancy_rate": rental_vacancy_rate,
                "homeownership_rate": homeownership_rate,
            })
    save_json(records, OUTPUT_FILES["acs_housing"])
    print(f"  ACS housing: {len(records)} records")
    return records

def fetch():
    fetch_income()
    fetch_poverty()
    fetch_housing()

if __name__ == "__main__":
    fetch()
