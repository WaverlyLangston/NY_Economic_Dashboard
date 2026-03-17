"""Shared helpers: retry logic, BLS batch POST, safe JSON save."""
import json, time, os, requests
from datetime import datetime

def safe_get(url, params=None, retries=3, delay=2):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r
        except Exception as e:
            if attempt < retries - 1:
                print(f"  Retry {attempt+1}/{retries-1} after error: {e}")
                time.sleep(delay * (attempt + 1))
            else:
                raise

def bls_post(series_ids, start_year, end_year, api_key, annual=True):
    """POST to BLS v2 API; handles >50-series chunking automatically."""
    import json, requests
    headers = {"Content-type": "application/json"}
    all_results = {}
    chunk_size = 50
    for i in range(0, len(series_ids), chunk_size):
        chunk = series_ids[i:i + chunk_size]
        payload = {
            "seriesid": chunk,
            "startyear": str(start_year),
            "endyear":   str(end_year),
            "catalog":   False,
            "calculations": False,
            "annualaverage": annual,
        }
        if api_key:
            payload["registrationkey"] = api_key
        resp = requests.post(
            "https://api.bls.gov/publicAPI/v2/timeseries/data/",
            data=json.dumps(payload), headers=headers, timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "REQUEST_SUCCEEDED":
            print(f"  BLS warning: {data.get('message', data.get('status'))}")
        for series in data.get("Results", {}).get("series", []):
            all_results[series["seriesID"]] = series["data"]
        time.sleep(0.5)          # stay under 50-req/10-sec limit
    return all_results

def bls_to_df(raw_results, series_name_map):
    """Convert raw BLS result dict → tidy DataFrame with Time column."""
    import pandas as pd
    rows = []
    for sid, records in raw_results.items():
        name = series_name_map.get(sid, sid)
        for rec in records:
            period = rec["period"]
            if period.startswith("M") and period != "M13":   # M13 = annual avg
                month = period[1:]
                time_str = f"{rec['year']}-{month}"
                rows.append({"time": time_str, "series": name, "value": float(rec["value"])})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)
    return df

def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)
    print(f"  Saved → {path}")

def load_json(path):
    with open(path) as f:
        return json.load(f)

def now_str():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
