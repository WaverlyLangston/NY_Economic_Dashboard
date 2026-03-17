# New York State Economic Dashboard

An interactive economic dashboard for New York State, published to GitHub Pages and updated automatically every day via GitHub Actions.

## Live Dashboard

**[View Dashboard →](https://YOUR-GITHUB-USERNAME.github.io/ny-economic-dashboard/)**

## Data Sources

| Section | Source | API |
|---|---|---|
| Business Formation | U.S. Census Bureau, BFS | Direct CSV download |
| GDP | Bureau of Economic Analysis | BEA API |
| Housing | U.S. Census Bureau, ACS | Census API |
| Job Openings | Bureau of Labor Statistics, JOLTS | BLS API |
| Employment by Industry | Bureau of Labor Statistics, CES | BLS API |
| Labor Force | Bureau of Labor Statistics, LAUS | BLS API |
| Population | U.S. Census Bureau, PEP | Direct file download + Census API |
| Migration | IRS Statistics of Income | Direct CSV download |
| Poverty / Income | U.S. Census Bureau, ACS | Census API |

## Repository Structure

```
ny-economic-dashboard/
├── .github/workflows/
│   └── refresh-data.yml      # Daily GitHub Actions job
├── scripts/
│   ├── fetch_all_data.py     # Orchestrator: runs all fetchers
│   ├── build_page.py         # Builds docs/index.html from JSON
│   └── fetchers/
│       ├── bea_gdp.py
│       ├── bls_ces.py
│       ├── bls_jolts.py
│       ├── bls_laus.py
│       ├── census_acs.py
│       ├── census_bfs.py
│       ├── census_pep.py
│       ├── irs_migration.py
│       └── utils.py
├── data/                     # Pre-fetched JSON files (auto-updated)
├── docs/
│   └── index.html            # Generated dashboard page
├── config.py                 # All series IDs, API settings
├── requirements.txt
└── README.md
```

## Setup

### 1. Fork or clone this repository

### 2. Get free API keys
| API | Registration URL |
|---|---|
| Census Bureau | https://api.census.gov/data/key_signup.html |
| BLS | https://data.bls.gov/registrationEngine/ |
| BEA | https://apps.bea.gov/API/signup/ |

### 3. Add secrets to your GitHub repository
Go to **Settings → Secrets and variables → Actions → New repository secret**:
- `CENSUS_API_KEY`
- `BLS_API_KEY`
- `BEA_API_KEY`

### 4. Enable GitHub Pages
Go to **Settings → Pages → Source: Deploy from branch → Branch: main, Folder: /docs**

### 5. Run locally (optional)

```bash
# Install dependencies
pip install -r requirements.txt

# Set API keys
export CENSUS_API_KEY="your_key_here"
export BLS_API_KEY="your_key_here"
export BEA_API_KEY="your_key_here"

# Fetch data
python scripts/fetch_all_data.py

# Build the page
python scripts/build_page.py

# Open docs/index.html in your browser
```

### 6. Trigger the first run
Go to **Actions → Refresh Economic Data → Run workflow**

After the workflow completes (~10–15 minutes), your dashboard will be live at:
`https://YOUR-GITHUB-USERNAME.github.io/ny-economic-dashboard/`

## Data Refresh

Data refreshes automatically every day at 8:00 AM UTC (4:00 AM ET) via GitHub Actions. The workflow:
1. Fetches fresh data from all APIs
2. Saves pre-processed JSON files to `data/`
3. Rebuilds `docs/index.html`
4. Commits and pushes the updated files

The static HTML page loads JSON data at build time — no API calls happen in the browser, keeping page loads fast.

## Visualizations

| Dashboard Section | Charts |
|---|---|
| Business Formation | NY application levels; NY + U.S. per capita moving averages |
| GDP | Peer-state GDP index; Industry growth rates; GDP share by industry |
| Housing | Rental vacancy rate; Housing stock growth |
| Job Openings | NY JOLTS levels; NY + U.S. JOLTS rates |
| Employment | Jobs index by industry; Gov vs Private; Change in jobs |
| Labor Force | NY labor force levels; NY + U.S. rates |
| Population | Total population over time; Net migration; Age distribution |
| Poverty | Poverty rate by race/ethnicity/sex, NY vs U.S. |
| Income | Median household income by race/ethnicity/sex, NY vs U.S. |
