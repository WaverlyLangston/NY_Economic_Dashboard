"""
census_bfs.py
Fetches Business Formation Statistics for NY and US from Census Bureau CSV.
Calculates per capita values and 12-month moving averages.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",".."))

import pandas as pd
import numpy as np
from scripts.fetchers.utils import safe_get, save_json
from config import BFS_CSV_URL, NY_ABBREV, OUTPUT_FILES

MONTH_MAP = {
    "jan":"01","feb":"02","mar":"03","apr":"04","may":"05","jun":"06",
    "jul":"07","aug":"08","sep":"09","oct":"10","nov":"11","dec":"12"
}

def fetch(population_df=None):
    print("BFS: downloading CSV...")
    r = safe_get(BFS_CSV_URL)
    from io import StringIO
    df = pd.read_csv(StringIO(r.text))

    # Filter: seasonally adjusted, NY + US, business applications + high-propensity
    geos  = [NY_ABBREV, "US"]
    types = ["BA_BA", "BA_HBA"]
    df = df[(df["sa"] == "A") & (df["geo"].isin(geos)) & (df["series"].isin(types))
            & (df["naics_sector"] == "TOTAL")].copy()

    # Melt wide month columns → long format
    month_cols = [c for c in df.columns if c in MONTH_MAP]
    df = df.melt(id_vars=["series","geo","year"], value_vars=month_cols,
                 var_name="month_name", value_name="value")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df.dropna(subset=["value"], inplace=True)

    # Build datetime
    df["month"] = df["month_name"].map(MONTH_MAP)
    df["time"]  = pd.to_datetime(df["year"].astype(str) + "-" + df["month"])
    df["label"] = df["series"] + "_" + df["geo"]
    df = df.sort_values("time")

    # Pivot so each label is a column
    wide = df.pivot_table(index="time", columns="label", values="value", aggfunc="first")
    wide.columns.name = None
    wide = wide.rename(columns={
        "BA_BA_NY":  "NY Business Applications",
        "BA_BA_US":  "U.S. Business Applications",
        "BA_HBA_NY": "NY High Propensity Business Applications",
        "BA_HBA_US": "U.S. High Propensity Business Applications",
    })

    # Merge population for per-capita (if provided)
    if population_df is not None:
        pop = population_df.set_index("Geography")
        # Convert columns (years as str) to numeric
        pop.columns = pop.columns.astype(str)
        wide["year"] = wide.index.year.astype(str)
        ny_pop = pop.loc["New York"] if "New York" in pop.index else None
        us_pop = pop.loc["United States"] if "United States" in pop.index else None
        if ny_pop is not None:
            wide["NY_pop"] = wide["year"].map(lambda y: float(str(ny_pop.get(y, np.nan)).replace(",","")))
        if us_pop is not None:
            wide["US_pop"] = wide["year"].map(lambda y: float(str(us_pop.get(y, np.nan)).replace(",","")))
        wide.drop(columns=["year"], inplace=True)

        for app_type in ["Business Applications", "High Propensity Business Applications"]:
            if f"NY {app_type}" in wide.columns and "NY_pop" in wide.columns:
                pc = wide[f"NY {app_type}"] / wide["NY_pop"] * 1000
                wide[f"NY {app_type} Per Capita"] = pc
                wide[f"NY {app_type} Per Capita 12mo MA"] = pc.rolling(12).mean()
            if f"U.S. {app_type}" in wide.columns and "US_pop" in wide.columns:
                pc = wide[f"U.S. {app_type}"] / wide["US_pop"] * 1000
                wide[f"U.S. {app_type} Per Capita"] = pc
                wide[f"U.S. {app_type} Per Capita 12mo MA"] = pc.rolling(12).mean()
        wide.drop(columns=[c for c in ["NY_pop","US_pop"] if c in wide.columns], inplace=True)

    wide = wide.reset_index()
    wide["time"] = wide["time"].dt.strftime("%Y-%m-%d")

    result = wide.replace({np.nan: None}).to_dict(orient="records")
    save_json(result, OUTPUT_FILES["bfs"])
    print(f"  BFS: {len(result)} monthly records saved.")
    return result

if __name__ == "__main__":
    fetch()
