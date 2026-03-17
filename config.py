"""
config.py
Central configuration for NY Economic Dashboard.
All API keys are loaded from environment variables.
"""
import os

# ─── API KEYS (set as GitHub Actions secrets or local env vars) ───────────────
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")
BLS_API_KEY    = os.environ.get("BLS_API_KEY", "")
BEA_API_KEY    = os.environ.get("BEA_API_KEY", "")

# ─── STATE IDENTIFIERS ────────────────────────────────────────────────────────
NY_FIPS      = "36"
NY_ABBREV    = "NY"
NY_GEO_BEA   = "36000"
US_GEO_BEA   = "00000"

PEER_STATES_BEA = {
    "36000": "New York",
    "25000": "Massachusetts",
    "34000": "New Jersey",
    "44000": "Rhode Island",
    "00000": "United States",
}

# ─── BEA ─────────────────────────────────────────────────────────────────────
BEA_BASE_URL = "https://apps.bea.gov/api/data"
BEA_TABLES = {
    "quarterly_real": "SQGDP9",
    "annual_real":    "SAGDP9N",
    "annual_nom":     "SAGDP2N",
}
BEA_INDUSTRY_CODES = {
    "1":  "All industry total",
    "6":  "Agriculture, forestry, fishing and hunting",
    "10": "Mining, quarrying, and oil and gas extraction",
    "11": "Utilities",
    "12": "Construction",
    "13": "Manufacturing",
    "17": "Wholesale trade",
    "18": "Retail trade",
    "19": "Transportation and warehousing",
    "20": "Information",
    "21": "Finance and insurance",
    "22": "Real estate and rental and leasing",
    "23": "Professional, scientific, and technical services",
    "24": "Management of companies and enterprises",
    "25": "Administrative and support and waste management",
    "26": "Educational services",
    "27": "Health care and social assistance",
    "28": "Arts, entertainment, and recreation",
    "29": "Accommodation and food services",
    "30": "Other services (except government)",
    "32": "Government",
    "35": "Federal civilian",
    "36": "Military",
    "37": "State and local",
}

# ─── BLS BASE ─────────────────────────────────────────────────────────────────
BLS_BASE_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# LAUS — New York State + National
LAUS_SERIES = {
    "LASST360000000000003": "NY Unemployment Rate",
    "LASST360000000000004": "NY Unemployment Level",
    "LASST360000000000005": "NY Employment Level",
    "LASST360000000000006": "NY Labor Force Level",
    "LASST360000000000007": "NY Employment-Population Ratio",
    "LASST360000000000008": "NY Labor Force Participation Rate",
    "LNS14000000":          "U.S. Unemployment Rate",
    "LNS11300000":          "U.S. Labor Force Participation Rate",
    "LNS12300000":          "U.S. Employment-Population Ratio",
}

# CES — New York State supersectors
CES_SERIES = {
    "SMS36000000000000001": "Total Nonfarm",
    "SMS36000000500000001": "Total Private",
    "SMS36000001500000001": "Mining, Logging and Construction",
    "SMS36000003000000001": "Manufacturing",
    "SMS36000004000000001": "Trade, Transportation, and Utilities",
    "SMS36000005000000001": "Information",
    "SMS36000005500000001": "Financial Activities",
    "SMS36000006000000001": "Professional and Business Services",
    "SMS36000006500000001": "Private Education and Health Services",
    "SMS36000007000000001": "Leisure and Hospitality",
    "SMS36000008000000001": "Other Services",
    "SMS36000009000000001": "Government",
}

# JOLTS — New York State + National
JOLTS_SERIES = {
    "JTS000000360000000JOL": "NY Job Openings Level",
    "JTS000000360000000JOR": "NY Job Openings Rate",
    "JTS000000360000000HIL": "NY Hires Level",
    "JTS000000360000000HIR": "NY Hires Rate",
    "JTS000000360000000QUL": "NY Quits Level",
    "JTS000000360000000QUR": "NY Quits Rate",
    "JTS000000360000000LDL": "NY Layoffs and Discharges Level",
    "JTS000000360000000LDR": "NY Layoffs and Discharges Rate",
    "JTS000000360000000TSL": "NY Total Separations Level",
    "JTS000000360000000TSR": "NY Total Separations Rate",
    "JTS000000360000000UOR": "NY Unemployed per Job Opening Ratio",
    "JTS000000000000000JOR": "U.S. Job Openings Rate",
    "JTS000000000000000HIR": "U.S. Hires Rate",
    "JTS000000000000000QUR": "U.S. Quits Rate",
    "JTS000000000000000LDR": "U.S. Layoffs and Discharges Rate",
    "JTS000000000000000TSR": "U.S. Total Separations Rate",
    "JTS000000000000000UOR": "U.S. Unemployed per Job Opening Ratio",
}

# ─── CENSUS BASE ──────────────────────────────────────────────────────────────
CENSUS_BASE_URL = "https://api.census.gov/data"
BFS_CSV_URL     = "https://www.census.gov/econ/bfs/csv/bfs_monthly.csv"

PEP_URLS = {
    "2000_2010": "https://www2.census.gov/programs-surveys/popest/tables/2000-2010/intercensal/state/st-est00int-01.csv",
    "2010_2020": "https://www2.census.gov/programs-surveys/popest/tables/2010-2020/state/totals/nst-est2020.xlsx",
    "2020_2023": "https://www2.census.gov/programs-surveys/popest/tables/2020-2023/state/totals/NST-EST2023-POP.xlsx",
}

# ─── IRS MIGRATION ────────────────────────────────────────────────────────────
IRS_BASE_URL = "https://www.irs.gov/pub/irs-soi"
IRS_YEARS = [
    ("1314", "2013-2014"),
    ("1415", "2014-2015"),
    ("1516", "2015-2016"),
    ("1617", "2016-2017"),
    ("1718", "2017-2018"),
    ("1819", "2018-2019"),
    ("1920", "2019-2020"),
    ("2021", "2020-2021"),
    ("2122", "2021-2022"),
]
NY_FIPS_IRS = 36

# ─── OUTPUT PATHS ─────────────────────────────────────────────────────────────
DATA_DIR = "data"
DOCS_DIR = "docs"
OUTPUT_FILES = {
    "bfs":              f"{DATA_DIR}/bfs.json",
    "bea_gdp":          f"{DATA_DIR}/bea_gdp.json",
    "bea_gdp_industry": f"{DATA_DIR}/bea_gdp_industry.json",
    "bls_laus":         f"{DATA_DIR}/bls_laus.json",
    "bls_ces":          f"{DATA_DIR}/bls_ces.json",
    "bls_jolts":        f"{DATA_DIR}/bls_jolts.json",
    "acs_income":       f"{DATA_DIR}/acs_income.json",
    "acs_poverty":      f"{DATA_DIR}/acs_poverty.json",
    "acs_housing":      f"{DATA_DIR}/acs_housing.json",
    "pep_population":   f"{DATA_DIR}/pep_population.json",
    "pep_age":          f"{DATA_DIR}/pep_age.json",
    "irs_migration":    f"{DATA_DIR}/irs_migration.json",
    "metadata":         f"{DATA_DIR}/metadata.json",
}
