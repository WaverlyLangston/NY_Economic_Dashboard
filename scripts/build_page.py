"""
build_page.py
Reads pre-fetched JSON files and builds a single-file docs/index.html
with all interactive Plotly charts embedded inline.

Usage:
    python scripts/build_page.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from config import OUTPUT_FILES, DOCS_DIR

os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(os.path.join(DOCS_DIR, "data"), exist_ok=True)

# ── Brand colours ──────────────────────────────────────────────────────────────
NY_BLUE   = "#1a3a5c"
NY_DARK   = "#0d2340"
US_ORANGE = "#e05a2b"
LIGHT_BLUE = "#5b9bd5"
ACCENT_GREEN = "#2e7d32"
ACCENT_TEAL  = "#00838f"
GREY      = "#8e9aaf"

INDUSTRY_PALETTE = [
    "#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd",
    "#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf",
    "#aec7e8","#ffbb78",
]

PLOTLY_CONFIG = {"displayModeBar": True, "responsive": True,
                 "modeBarButtonsToRemove": ["select2d","lasso2d"]}

def load(key):
    path = OUTPUT_FILES.get(key)
    if path and os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    print(f"  Missing data: {key} ({path})")
    return None

def fig_to_html(fig, div_id=None):
    kwargs = dict(full_html=False, include_plotlyjs=False,
                  config=PLOTLY_CONFIG)
    if div_id:
        kwargs["div_id"] = div_id
    return pio.to_html(fig, **kwargs)

def base_layout(title="", height=420):
    return dict(
        title=dict(text=title, font=dict(size=16, color=NY_DARK), x=0.0, xanchor="left"),
        paper_bgcolor="white", plot_bgcolor="#f8f9fa",
        font=dict(family="Segoe UI, Arial, sans-serif", size=12, color="#333"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=40, t=80, b=60),
        height=height,
        hovermode="x unified",
    )

# ══════════════════════════════════════════════════════════════════════════════
#  BUSINESS FORMATION STATISTICS
# ══════════════════════════════════════════════════════════════════════════════
def chart_bfs():
    data = load("bfs")
    if not data:
        return "<p>BFS data unavailable.</p>", "<p>BFS data unavailable.</p>"

    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"])

    # Chart A: NY Application Levels (both BA and HBA on one plot)
    fig_a = go.Figure()
    for col, color, name in [
        ("NY Business Applications", NY_BLUE, "Business Applications"),
        ("NY High Propensity Business Applications", LIGHT_BLUE, "High Propensity Applications"),
    ]:
        if col in df.columns:
            fig_a.add_trace(go.Scatter(
                x=df["time"], y=df[col], name=name, line=dict(color=color, width=1.5),
                hovertemplate="%{x|%b %Y}: %{y:,.0f}<extra></extra>",
            ))
    fig_a.update_layout(**base_layout("New York Business Application Levels"),
                        xaxis_title="Monthly, Seasonally Adjusted",
                        yaxis_title="Number of Applications",
                        annotations=[dict(
                            text="Source: U.S. Census Bureau, Business Formation Statistics",
                            xref="paper", yref="paper", x=0, y=-0.15,
                            font=dict(size=10, color=GREY), showarrow=False)])

    # Chart B: Per Capita 12-Month Moving Average with dropdown (BA vs HBA)
    # Build traces for each type and use updatemenus
    traces_ba, traces_hba = [], []
    for col, color, geo in [
        ("NY Business Applications Per Capita 12mo MA", NY_BLUE, "New York"),
        ("U.S. Business Applications Per Capita 12mo MA", US_ORANGE, "United States"),
    ]:
        vis = col in df.columns
        traces_ba.append(go.Scatter(
            x=df["time"], y=df.get(col, [None]*len(df)),
            name=geo, line=dict(color=color, width=2), visible=True,
            hovertemplate=f"{geo}: %{{y:.3f}}<extra></extra>",
        ))
    for col, color, geo in [
        ("NY High Propensity Business Applications Per Capita 12mo MA", NY_BLUE, "New York"),
        ("U.S. High Propensity Business Applications Per Capita 12mo MA", US_ORANGE, "United States"),
    ]:
        traces_hba.append(go.Scatter(
            x=df["time"], y=df.get(col, [None]*len(df)),
            name=geo, line=dict(color=color, width=2), visible=False,
            hovertemplate=f"{geo}: %{{y:.3f}}<extra></extra>",
        ))

    fig_b = go.Figure(data=traces_ba + traces_hba)
    n = len(traces_ba)
    fig_b.update_layout(
        **base_layout("New York and U.S. Business Applications per Capita"),
        xaxis_title="Monthly, Seasonally Adjusted",
        yaxis_title="Applications per 1,000 People (12-Month Moving Avg.)",
        updatemenus=[dict(
            buttons=[
                dict(label="Business Applications",
                     method="update",
                     args=[{"visible": [True]*n + [False]*n},
                           {"title": {"text": "NY and U.S. Business Applications per Capita"}}]),
                dict(label="High Propensity Applications",
                     method="update",
                     args=[{"visible": [False]*n + [True]*n},
                           {"title": {"text": "NY and U.S. High Propensity Applications per Capita"}}]),
            ],
            direction="down", showactive=True,
            x=0.0, xanchor="left", y=1.15, yanchor="top",
            bgcolor="white", bordercolor="#ccc",
        )],
        annotations=[dict(
            text="Source: U.S. Census Bureau, Business Formation Statistics",
            xref="paper", yref="paper", x=0, y=-0.15,
            font=dict(size=10, color=GREY), showarrow=False)])
    return fig_to_html(fig_a, "bfs_levels"), fig_to_html(fig_b, "bfs_percapita")

# ══════════════════════════════════════════════════════════════════════════════
#  GDP
# ══════════════════════════════════════════════════════════════════════════════
def _index_series(series: pd.Series, ref_date=None, n_periods=None):
    """Return % change from a reference point."""
    if n_periods:
        ref_val = series.iloc[-n_periods] if len(series) >= n_periods else series.iloc[0]
    elif ref_date and ref_date in series.index:
        ref_val = series[ref_date]
    else:
        ref_val = series.iloc[0]
    if pd.isna(ref_val) or ref_val == 0:
        return series * np.nan
    return (series / ref_val) - 1.0

PEER_COLORS = {
    "New York":     NY_BLUE,
    "Massachusetts": LIGHT_BLUE,
    "New Jersey":   "#f5a623",
    "Rhode Island": "#e94e77",
    "United States": US_ORANGE,
}

def chart_gdp_peer():
    data = load("bea_gdp")
    if not data:
        return "<p>GDP data unavailable.</p>"

    df = pd.DataFrame(data)
    peers = [c for c in df.columns if c != "time"]

    def make_fig(n_periods, label):
        fig = go.Figure()
        for state in peers:
            if state not in df.columns:
                continue
            series = pd.to_numeric(df[state], errors="coerce")
            indexed = _index_series(series, n_periods=n_periods)
            lw = 3 if state == "New York" else 1.5
            fig.add_trace(go.Scatter(
                x=df["time"], y=indexed,
                name=state,
                line=dict(color=PEER_COLORS.get(state, GREY), width=lw),
                hovertemplate=f"{state}: %{{y:.1%}}<extra></extra>",
            ))
        fig.add_hline(y=0, line_dash="dot", line_color=GREY, line_width=1)
        fig.update_layout(
            **base_layout(f"GDP Index by State"),
            xaxis_title="Quarterly",
            yaxis=dict(title="Percent Change from Base Period", tickformat=".0%"),
            annotations=[dict(
                text="Source: U.S. Bureau of Economic Analysis, Real GDP",
                xref="paper", yref="paper", x=0, y=-0.15,
                font=dict(size=10, color=GREY), showarrow=False)])
        return fig

    # Two time-frame options via dropdown
    fig1 = make_fig(20, "Five Year")  # 20 quarters = 5 years
    fig5 = make_fig(40, "Ten Year")   # 40 quarters = 10 years

    # Build combined figure with updatemenus
    traces_5yr = list(fig1.data)
    traces_10yr = list(fig5.data)
    n = len(traces_5yr)

    fig = go.Figure(data=list(traces_5yr) + list(traces_10yr))
    for i in range(n, 2*n):
        fig.data[i].visible = False

    fig.update_layout(
        **base_layout("GDP Index by State"),
        xaxis_title="Quarterly",
        yaxis=dict(title="Percent Change from Base Period", tickformat=".0%"),
        updatemenus=[dict(
            buttons=[
                dict(label="Five Year", method="update",
                     args=[{"visible": [True]*n + [False]*n}]),
                dict(label="Ten Year", method="update",
                     args=[{"visible": [False]*n + [True]*n}]),
            ],
            direction="down", showactive=True,
            x=1.0, xanchor="right", y=1.15, yanchor="top",
            bgcolor="white", bordercolor="#ccc",
        )],
        annotations=[dict(
            text="Source: U.S. Bureau of Economic Analysis, Real GDP",
            xref="paper", yref="paper", x=0, y=-0.15,
            font=dict(size=10, color=GREY), showarrow=False)])
    return fig_to_html(fig, "gdp_peer")

def chart_gdp_industry_growth():
    data = load("bea_gdp_industry")
    if not data:
        return "<p>GDP industry data unavailable.</p>"

    qtr = data.get("quarterly_by_industry", {})
    if not qtr:
        return "<p>GDP industry growth data unavailable.</p>"

    # Select industries to display (exclude aggregates)
    skip = {"All industry total", "Private industries", "Government",
            "Administrative and support and waste management",
            "Management of companies and enterprises"}

    industries = [k for k in qtr.keys() if k not in skip]

    def make_indexed_traces(n_periods):
        traces = []
        for i, ind in enumerate(industries):
            series_data = qtr[ind]
            times  = series_data["times"]
            vals   = pd.Series(series_data["values"])
            if len(vals) < n_periods:
                continue
            ref_val = vals.iloc[-n_periods]
            if pd.isna(ref_val) or ref_val == 0:
                continue
            indexed = (vals / ref_val) - 1.0
            traces.append(go.Scatter(
                x=times, y=indexed.tolist(),
                name=ind, line=dict(color=INDUSTRY_PALETTE[i % len(INDUSTRY_PALETTE)], width=1.5),
                hovertemplate=f"{ind}: %{{y:.1%}}<extra></extra>",
            ))
        return traces

    t5 = make_indexed_traces(20)
    t10 = make_indexed_traces(40)
    n = len(t5)

    fig = go.Figure(data=t5 + t10)
    for i in range(n, len(fig.data)):
        fig.data[i].visible = False

    fig.add_hline(y=0, line_dash="dot", line_color=GREY, line_width=1)
    fig.update_layout(
        **base_layout("New York Highest and Lowest Industry GDP Growth"),
        xaxis_title="Quarterly",
        yaxis=dict(title="Percent Change from Base Period", tickformat=".0%"),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.01, font=dict(size=10)),
        margin=dict(l=60, r=200, t=80, b=60),
        height=450,
        updatemenus=[dict(
            buttons=[
                dict(label="Five Year", method="update",
                     args=[{"visible": [True]*n + [False]*n}]),
                dict(label="Ten Year", method="update",
                     args=[{"visible": [False]*n + [True]*n}]),
            ],
            direction="down", showactive=True,
            x=1.0, xanchor="right", y=1.15, yanchor="top",
            bgcolor="white", bordercolor="#ccc",
        )],
        annotations=[dict(
            text="Source: U.S. Bureau of Economic Analysis, Real GDP",
            xref="paper", yref="paper", x=0, y=-0.18,
            font=dict(size=10, color=GREY), showarrow=False)])
    return fig_to_html(fig, "gdp_industry_growth")

def chart_gdp_industry_bar():
    data = load("bea_gdp_industry")
    if not data:
        return "<p>GDP industry bar data unavailable.</p>"

    ann = data.get("annual_by_industry", {})
    if not ann or "data" not in ann:
        return "<p>GDP industry annual data unavailable.</p>"

    year = ann.get("year", "")
    rows = [r for r in ann["data"]
            if r.get("industry") not in ("All industry total","Private industries")]
    if not rows:
        return "<p>No industry GDP data.</p>"

    df = pd.DataFrame(rows).sort_values("DataValue", ascending=True).dropna(subset=["DataValue"])
    df["DataValue"] = pd.to_numeric(df["DataValue"], errors="coerce").dropna()
    df["share_pct"] = df["share"].map(lambda v: f"{v:.1%}" if v else "")
    df["label"] = df.apply(
        lambda r: f"${r['DataValue']:,.0f}M, {r['share_pct']}" if r.get("DataValue") else "", axis=1)

    fig = go.Figure(go.Bar(
        x=df["DataValue"], y=df["industry"],
        orientation="h",
        text=df["label"], textposition="inside",
        marker=dict(color=df["DataValue"], colorscale=[
            [0, "#c8d8e8"], [0.5, "#5b9bd5"], [1, NY_BLUE]
        ]),
        hovertemplate="%{y}: $%{x:,.0f}M<extra></extra>",
    ))
    fig.update_layout(
        **base_layout(f"New York GDP by Industry ({year}, Real GDP, $M)"),
        xaxis=dict(title="Real GDP (Millions USD, Chained 2017 $)"),
        yaxis=dict(title=""),
        height=550,
        hovermode="y unified",
        annotations=[dict(
            text="Source: U.S. Bureau of Economic Analysis, SAGDP9N",
            xref="paper", yref="paper", x=0, y=-0.08,
            font=dict(size=10, color=GREY), showarrow=False)])
    return fig_to_html(fig, "gdp_industry_bar")

# ══════════════════════════════════════════════════════════════════════════════
#  HOUSING
# ══════════════════════════════════════════════════════════════════════════════
def chart_housing():
    data = load("acs_housing")
    if not data:
        return "<p>Housing data unavailable.</p>"

    df = pd.DataFrame(data)
    ny = df[df["geography"] == "New York"].sort_values("year")
    us = df[df["geography"] == "United States"].sort_values("year")

    fig = make_subplots(rows=2, cols=1, subplot_titles=(
        "Rental Vacancy Rate (Annual)",
        "Changes in Housing Stock, Year-Over-Year"
    ), vertical_spacing=0.15)

    # Rental vacancy rate
    for d, color, name in [(ny, NY_BLUE, "New York"), (us, US_ORANGE, "United States")]:
        fig.add_trace(go.Scatter(
            x=d["year"], y=d["rental_vacancy_rate"],
            name=name, line=dict(color=color, width=2),
            hovertemplate=f"{name}: %{{y:.1%}}<extra></extra>",
            legendgroup=name,
        ), row=1, col=1)

    # Year-over-year change in housing stock
    ny_yoy = ny.set_index("year")["total_units"].pct_change()
    us_yoy = us.set_index("year")["total_units"].pct_change()

    fig.add_trace(go.Scatter(
        x=ny.year[1:], y=ny_yoy.dropna().values,
        name="New York", line=dict(color=NY_BLUE, width=2),
        hovertemplate="NY: %{y:.2%}<extra></extra>",
        legendgroup="New York", showlegend=False,
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=us.year[1:], y=us_yoy.dropna().values,
        name="United States", line=dict(color=US_ORANGE, width=2),
        hovertemplate="U.S.: %{y:.2%}<extra></extra>",
        legendgroup="United States", showlegend=False,
    ), row=2, col=1)

    fig.update_yaxes(tickformat=".1%", row=1, col=1, title_text="Rental Vacancy Rate")
    fig.update_yaxes(tickformat=".2%", row=2, col=1, title_text="Year-over-Year Change")
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="#f8f9fa",
        font=dict(family="Segoe UI, Arial, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5),
        margin=dict(l=60, r=40, t=80, b=80), height=600,
        annotations=[dict(
            text="Source: U.S. Census Bureau, American Community Survey (ACS 1-Year)",
            xref="paper", yref="paper", x=0, y=-0.15,
            font=dict(size=10, color=GREY), showarrow=False)])
    return fig_to_html(fig, "housing")

# ══════════════════════════════════════════════════════════════════════════════
#  JOB OPENINGS (JOLTS)
# ══════════════════════════════════════════════════════════════════════════════
def chart_jolts():
    data = load("bls_jolts")
    if not data or not data.get("monthly"):
        return "<p>JOLTS data unavailable.</p>", "<p>JOLTS data unavailable.</p>"

    df = pd.DataFrame(data["monthly"])
    df["time"] = pd.to_datetime(df["time"])

    LEVEL_COLS = {
        "NY Job Openings Level":         ("Job Openings", LIGHT_BLUE),
        "NY Hires Level":                ("Hires", NY_BLUE),
        "NY Total Separations Level":    ("Total Separations", "#e94e77"),
        "NY Layoffs and Discharges Level":("Layoffs & Discharges", US_ORANGE),
        "NY Quits Level":                ("Quits", "#f5a623"),
    }

    # Chart A: NY Levels
    fig_a = go.Figure()
    for col, (label, color) in LEVEL_COLS.items():
        if col in df.columns:
            fig_a.add_trace(go.Scatter(
                x=df["time"], y=df[col], name=label,
                line=dict(color=color, width=1.5),
                hovertemplate=f"{label}: %{{y:,.0f}}<extra></extra>",
            ))
    # Also show unemployed per opening as a table-style annotation using latest value
    latest = df.dropna(subset=["NY Unemployed per Job Opening Ratio"]).tail(1)
    us_latest = df.dropna(subset=["U.S. Unemployed per Job Opening Ratio"]).tail(1)

    fig_a.update_layout(
        **base_layout("New York Job Market Levels"),
        xaxis_title="Monthly, Seasonally Adjusted",
        yaxis_title="Number of Workers",
        annotations=[dict(
            text="Source: U.S. Bureau of Labor Statistics, JOLTS",
            xref="paper", yref="paper", x=0, y=-0.15,
            font=dict(size=10, color=GREY), showarrow=False)])

    # Chart B: NY and U.S. Rates — dropdown selector
    RATE_METRICS = {
        "Unemployed per Job Opening Ratio": ("NY Unemployed per Job Opening Ratio", "U.S. Unemployed per Job Opening Ratio"),
        "Job Openings Rate":   ("NY Job Openings Rate",   "U.S. Job Openings Rate"),
        "Hires Rate":          ("NY Hires Rate",           "U.S. Hires Rate"),
        "Quits Rate":          ("NY Quits Rate",           "U.S. Quits Rate"),
        "Layoffs Rate":        ("NY Layoffs and Discharges Rate", "U.S. Layoffs and Discharges Rate"),
        "Total Separations Rate": ("NY Total Separations Rate", "U.S. Total Separations Rate"),
    }

    all_traces_b = []
    buttons_b = []
    trace_idx = 0
    for metric, (ny_col, us_col) in RATE_METRICS.items():
        vis_arr = [False] * (len(RATE_METRICS) * 2)
        for col, color, geo in [(ny_col, NY_BLUE, "New York"), (us_col, US_ORANGE, "United States")]:
            y_data = df[col].tolist() if col in df.columns else [None]*len(df)
            fmt = ".2f" if "Ratio" in metric else ".1%"
            all_traces_b.append(go.Scatter(
                x=df["time"], y=y_data, name=geo,
                line=dict(color=color, width=2),
                visible=(metric == "Unemployed per Job Opening Ratio"),
                hovertemplate=f"{geo}: %{{y:{fmt}}}<extra></extra>",
            ))
        vis_arr[trace_idx] = True
        vis_arr[trace_idx+1] = True
        buttons_b.append(dict(
            label=metric, method="update",
            args=[{"visible": [i in [trace_idx, trace_idx+1]
                               for i in range(len(RATE_METRICS)*2)]}]
        ))
        trace_idx += 2

    fig_b = go.Figure(data=all_traces_b)
    fig_b.update_layout(
        **base_layout("New York and U.S. Job Market Rates"),
        xaxis_title="Monthly, Seasonally Adjusted",
        yaxis_title="Rate",
        updatemenus=[dict(
            buttons=buttons_b,
            direction="down", showactive=True,
            x=0.0, xanchor="left", y=1.15, yanchor="top",
            bgcolor="white", bordercolor="#ccc",
        )],
        annotations=[dict(
            text="Source: U.S. Bureau of Labor Statistics, JOLTS",
            xref="paper", yref="paper", x=0, y=-0.15,
            font=dict(size=10, color=GREY), showarrow=False)])

    return fig_to_html(fig_a, "jolts_levels"), fig_to_html(fig_b, "jolts_rates")

# ══════════════════════════════════════════════════════════════════════════════
#  JOBS (CES)
# ══════════════════════════════════════════════════════════════════════════════
def chart_ces():
    data = load("bls_ces")
    if not data:
        return "<p>CES data unavailable.</p>", "<p>CES data unavailable.</p>", "<p>CES data unavailable.</p>"

    monthly  = pd.DataFrame(data.get("monthly", []))
    changes  = data.get("changes", [])
    ref_date = data.get("reference_date", "")

    if monthly.empty:
        return "<p>CES monthly data unavailable.</p>", "", ""

    monthly["time"] = pd.to_datetime(monthly["time"])

    industry_cols = [c for c in monthly.columns
                     if c.endswith(" Index") and c not in
                     ("Total Nonfarm Index","Total Private Index","Government Index")]

    # Chart A: Jobs Index by Industry
    layout_a = base_layout("New York Jobs Index by Industry")
    layout_a["legend"] = dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.01, font=dict(size=10))
    layout_a["margin"] = dict(l=60, r=200, t=80, b=60)
    layout_a["height"] = 450
    layout_a["xaxis_title"] = "Monthly, Seasonally Adjusted"
    layout_a["yaxis"] = dict(title="Change from Base Period", tickformat=".0%")
    layout_a["annotations"] = [dict(
        text=f"Source: U.S. Bureau of Labor Statistics, CES (base: {ref_date})",
        xref="paper", yref="paper", x=0, y=-0.1,
        font=dict(size=10, color=GREY), showarrow=False)]

    fig_a = go.Figure()
    for i, col in enumerate(industry_cols):
        label = col.replace(" Index","")
        fig_a.add_trace(go.Scatter(
            x=monthly["time"], y=monthly[col], name=label,
            line=dict(color=INDUSTRY_PALETTE[i % len(INDUSTRY_PALETTE)], width=1.5),
            hovertemplate=f"{label}: %{{y:.1%}}<extra></extra>",
        ))
    fig_a.add_hline(y=0, line_dash="dot", line_color=GREY, line_width=1)
    fig_a.update_layout(**layout_a)

    # Chart B: Government vs Total Private Index
    fig_b = go.Figure()
    for col, color, label in [
        ("Total Private Index", LIGHT_BLUE, "Total Private"),
        ("Government Index", NY_BLUE, "Government"),
    ]:
        if col in monthly.columns:
            fig_b.add_trace(go.Scatter(
                x=monthly["time"], y=monthly[col], name=label,
                line=dict(color=color, width=2.5),
                hovertemplate=f"{label}: %{{y:.1%}}<extra></extra>",
            ))
    fig_b.add_hline(y=0, line_dash="dot", line_color=GREY, line_width=1)
    fig_b.update_layout(
        **base_layout("New York Jobs Index: Government vs. Total Private"),
        xaxis_title="Monthly, Seasonally Adjusted",
        yaxis=dict(title="Change from Base Period", tickformat=".0%"),
        annotations=[dict(
            text=f"Source: U.S. Bureau of Labor Statistics, CES (base: {ref_date})",
            xref="paper", yref="paper", x=0, y=-0.15,
            font=dict(size=10, color=GREY), showarrow=False)])

    # Chart C: Change in Number of Jobs by Industry
    if not changes:
        html_c = "<p>Industry change data unavailable.</p>"
    else:
        df_c = pd.DataFrame(changes).dropna(subset=["change"])
        df_c = df_c[~df_c["industry"].isin(["Total Nonfarm","Total Private"])].copy()
        df_c = df_c.sort_values("change")
        colors_c = [US_ORANGE if v >= 0 else "#c0392b" for v in df_c["change"]]
        as_of = df_c["as_of"].iloc[0] if not df_c.empty else ""

        fig_c = go.Figure(go.Bar(
            x=df_c["industry"], y=df_c["change"],
            marker_color=colors_c,
            hovertemplate="%{x}: %{y:+,.0f} jobs<extra></extra>",
        ))
        fig_c.update_layout(
            **base_layout("Change in Number of Jobs by Industry"),
            xaxis=dict(title="", tickangle=-30),
            yaxis_title="Change in Number of Jobs",
            height=420,
            annotations=[
                dict(text=f"As of {as_of}", xref="paper", yref="paper",
                     x=0.5, y=1.05, font=dict(size=12, color="#555"), showarrow=False),
                dict(text="Source: U.S. Bureau of Labor Statistics, CES",
                     xref="paper", yref="paper", x=0, y=-0.2,
                     font=dict(size=10, color=GREY), showarrow=False)])
        html_c = fig_to_html(fig_c, "ces_change")

    return fig_to_html(fig_a, "ces_index"), fig_to_html(fig_b, "ces_gov_priv"), html_c
    
# ══════════════════════════════════════════════════════════════════════════════
#  LABOR FORCE (LAUS)
# ══════════════════════════════════════════════════════════════════════════════
def chart_laus():
    data = load("bls_laus")
    if not data:
        return "<p>LAUS data unavailable.</p>", "<p>LAUS data unavailable.</p>"

    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"])

    # Get most recent values for headline KPIs
    latest = df.dropna().tail(1).iloc[0] if not df.empty else {}

    # Chart A: NY Labor Force and Employment levels (left axis) + Unemployment level (right)
    fig_a = make_subplots(specs=[[{"secondary_y": True}]])
    for col, color, name in [
        ("NY Labor Force Level", LIGHT_BLUE, "Labor Force"),
        ("NY Employment Level", NY_BLUE, "Employment"),
    ]:
        if col in df.columns:
            fig_a.add_trace(go.Scatter(
                x=df["time"], y=df[col], name=name,
                line=dict(color=color, width=2),
                hovertemplate=f"{name}: %{{y:,.0f}}<extra></extra>",
            ), secondary_y=False)

    if "NY Unemployment Level" in df.columns:
        fig_a.add_trace(go.Scatter(
            x=df["time"], y=df["NY Unemployment Level"], name="Unemployment",
            line=dict(color=US_ORANGE, width=2),
            hovertemplate="Unemployment: %{y:,.0f}<extra></extra>",
        ), secondary_y=True)

    fig_a.update_yaxes(title_text="Employment & Labor Force", secondary_y=False)
    fig_a.update_yaxes(title_text="Unemployed Workers", secondary_y=True)
    fig_a.update_layout(
        **base_layout("New York State Labor Force"),
        xaxis_title="Monthly, Seasonally Adjusted",
        annotations=[dict(
            text="Source: U.S. Bureau of Labor Statistics, LAUS",
            xref="paper", yref="paper", x=0, y=-0.15,
            font=dict(size=10, color=GREY), showarrow=False)])

    # Chart B: Rates — NY vs US with dropdown
    RATE_METRICS_LAUS = {
        "Unemployment Rate": ("NY Unemployment Rate", "U.S. Unemployment Rate"),
        "Labor Force Participation Rate": ("NY Labor Force Participation Rate", "U.S. Labor Force Participation Rate"),
        "Employment-Population Ratio": ("NY Employment-Population Ratio", "U.S. Employment-Population Ratio"),
    }

    all_traces = []
    buttons = []
    trace_idx = 0
    for metric, (ny_col, us_col) in RATE_METRICS_LAUS.items():
        for col, color, geo in [(ny_col, NY_BLUE, "New York"), (us_col, US_ORANGE, "United States")]:
            y = df[col].tolist() if col in df.columns else [None]*len(df)
            all_traces.append(go.Scatter(
                x=df["time"], y=y, name=geo,
                line=dict(color=color, width=2),
                visible=(metric == "Unemployment Rate"),
                hovertemplate=f"{geo}: %{{y:.1%}}<extra></extra>",
            ))
        visible_arr = [i in [trace_idx, trace_idx+1] for i in range(len(RATE_METRICS_LAUS)*2)]
        buttons.append(dict(
            label=metric, method="update",
            args=[{"visible": visible_arr}]
        ))
        trace_idx += 2

    fig_b = go.Figure(data=all_traces)
    fig_b.update_layout(
        **base_layout("New York and U.S. Labor Force Rates"),
        xaxis_title="Monthly, Seasonally Adjusted",
        yaxis=dict(title="Rate", tickformat=".1%"),
        updatemenus=[dict(
            buttons=buttons,
            direction="down", showactive=True,
            x=0.0, xanchor="left", y=1.15, yanchor="top",
            bgcolor="white", bordercolor="#ccc",
        )],
        annotations=[dict(
            text="Source: U.S. Bureau of Labor Statistics, LAUS",
            xref="paper", yref="paper", x=0, y=-0.15,
            font=dict(size=10, color=GREY), showarrow=False)])

    return fig_to_html(fig_a, "laus_levels"), fig_to_html(fig_b, "laus_rates")

# ══════════════════════════════════════════════════════════════════════════════
#  POPULATION & MIGRATION
# ══════════════════════════════════════════════════════════════════════════════
def chart_population():
    pop_data = load("pep_population")
    mig_data = load("irs_migration")
    age_data = load("pep_age")

    charts = []

    # Population over time (NY only)
    if pop_data:
        df = pd.DataFrame(pop_data)
        ny_pop = df[df["geography"] == "New York"].sort_values("year")
        if not ny_pop.empty:
            fig = go.Figure(go.Scatter(
                x=ny_pop["year"], y=ny_pop["population"],
                line=dict(color=NY_BLUE, width=2.5),
                fill="tozeroy", fillcolor="rgba(26,58,92,0.08)",
                hovertemplate="Year %{x}: %{y:,.0f}<extra></extra>",
            ))
            fig.update_layout(
                **base_layout("New York State Population Over Time"),
                xaxis_title="Year",
                yaxis=dict(title="Population", tickformat=","),
                annotations=[dict(
                    text="Source: U.S. Census Bureau, Population Estimates",
                    xref="paper", yref="paper", x=0, y=-0.15,
                    font=dict(size=10, color=GREY), showarrow=False)])
            charts.append(fig_to_html(fig, "pop_total"))

    # Net domestic migration (IRS)
    if mig_data and mig_data.get("annual_net"):
        net_df = pd.DataFrame(mig_data["annual_net"])
        fig = go.Figure()
        colors_mig = [NY_BLUE if v >= 0 else US_ORANGE for v in net_df["net_people"]]
        fig.add_trace(go.Bar(
            x=net_df["year_label"], y=net_df["net_people"],
            name="IRS Net Migration", marker_color=colors_mig,
            hovertemplate="%{x}: %{y:+,.0f} people<extra></extra>",
        ))
        fig.add_hline(y=0, line_color=GREY, line_width=1)
        fig.update_layout(
            **base_layout("New York State Net Domestic Migration (IRS Data)"),
            xaxis_title="Year",
            yaxis_title="Net Domestic Migration (People)",
            legend=dict(orientation="h", y=-0.2),
            annotations=[dict(
                text="Source: IRS Statistics of Income, State-to-State Migration",
                xref="paper", yref="paper", x=0, y=-0.2,
                font=dict(size=10, color=GREY), showarrow=False)])
        charts.append(fig_to_html(fig, "migration"))

    # Age breakdown stacked bar
    if age_data:
        age_df = pd.DataFrame(age_data)
        if not age_df.empty:
            age_order = ["Under 5","5 To 13","14 To 17","18 To 24","25 To 44","45 To 64","65 And Over"]
            age_colors = {
                "Under 5":     "#00c853",
                "5 To 13":     "#aa00ff",
                "14 To 17":    "#e91e63",
                "18 To 24":    "#ff9800",
                "25 To 44":    "#ff5722",
                "45 To 64":    "#29b6f6",
                "65 And Over": NY_DARK,
            }
            fig = go.Figure()
            for age in age_order:
                grp = age_df[age_df["age_group"] == age].sort_values("year")
                if grp.empty:
                    continue
                fig.add_trace(go.Bar(
                    x=grp["year"], y=grp["population"],
                    name=age, marker_color=age_colors.get(age, GREY),
                    hovertemplate=f"{age}: %{{y:,.0f}}<extra></extra>",
                ))
            fig.update_layout(
                **base_layout("Age of New York State Population Over Time"),
                barmode="stack",
                xaxis_title="Year",
                yaxis=dict(title="Population", tickformat=","),
                annotations=[dict(
                    text="Source: U.S. Census Bureau, Population Estimates",
                    xref="paper", yref="paper", x=0, y=-0.15,
                    font=dict(size=10, color=GREY), showarrow=False)])
            charts.append(fig_to_html(fig, "pop_age"))

    return tuple(charts) if charts else ("<p>Population data unavailable.</p>",)

# ══════════════════════════════════════════════════════════════════════════════
#  POVERTY DEMOGRAPHICS
# ══════════════════════════════════════════════════════════════════════════════
def chart_poverty():
    data = load("acs_poverty")
    if not data:
        return "<p>Poverty data unavailable.</p>"

    df = pd.DataFrame(data)
    latest_year = df["year"].max()
    df = df[df["year"] == latest_year]

    ny = df[df["geography"] == "New York"]
    us = df[df["geography"] == "United States"]

    # Groups to display (match original Tableau order)
    groups = [
        "White alone","Black or African American alone",
        "Some other race alone","Asian alone",
        "American Indian and Alaska Native alone",
        "Native Hawaiian and Other Pacific Islander alone",
        "Two or more races","Hispanic or Latino (of any race)",
        "Female","Male",
    ]

    ny_rates, us_rates = [], []
    for g in groups:
        ny_row = ny[ny["group"] == g]
        us_row = us[us["group"] == g]
        ny_rates.append(ny_row["rate"].values[0] if not ny_row.empty else None)
        us_rates.append(us_row["rate"].values[0] if not us_row.empty else None)

    ny_total = ny[ny["group"]=="Total"]["rate"].values
    us_total = us[us["group"]=="Total"]["rate"].values
    ny_total_rate = ny_total[0] if len(ny_total) else None
    us_total_rate = us_total[0] if len(us_total) else None

    fig = go.Figure()

    # NY bars
    fig.add_trace(go.Bar(
        x=groups, y=ny_rates, name="New York",
        marker_color=NY_BLUE,
        hovertemplate="%{x}<br>NY: %{y:.1%}<extra></extra>",
    ))

    # US dots
    fig.add_trace(go.Scatter(
        x=groups, y=us_rates, name="United States",
        mode="markers", marker=dict(color=US_ORANGE, size=12, symbol="circle"),
        hovertemplate="%{x}<br>U.S.: %{y:.1%}<extra></extra>",
    ))

    # Reference lines
    annotations = []
    if ny_total_rate is not None:
        fig.add_hline(y=ny_total_rate, line_color=LIGHT_BLUE, line_dash="dash", line_width=1.5)
        annotations.append(dict(
            text=f"NY Total Poverty Rate = {ny_total_rate:.1%}",
            xref="paper", yref="y", x=0.01, y=ny_total_rate,
            font=dict(size=10, color=LIGHT_BLUE), showarrow=False, yshift=8))
    if us_total_rate is not None:
        fig.add_hline(y=us_total_rate, line_color=US_ORANGE, line_dash="dot", line_width=1.5)
        annotations.append(dict(
            text=f"U.S. Total Poverty Rate = {us_total_rate:.1%}",
            xref="paper", yref="y", x=0.6, y=us_total_rate,
            font=dict(size=10, color=US_ORANGE), showarrow=False, yshift=8))

    annotations.append(dict(
        text=f"Source: U.S. Census Bureau, {latest_year} 1-Year ACS",
        xref="paper", yref="paper", x=0, y=-0.25,
        font=dict(size=10, color=GREY), showarrow=False))

    fig.update_layout(
        **base_layout(f"Poverty Rate by Demographic Group, {latest_year}"),
        xaxis=dict(title="", tickangle=-25),
        yaxis=dict(title="Poverty Rate", tickformat=".0%"),
        barmode="group",
        height=450,
        annotations=annotations)
    return fig_to_html(fig, "poverty")

# ══════════════════════════════════════════════════════════════════════════════
#  WAGE / INCOME DEMOGRAPHICS
# ══════════════════════════════════════════════════════════════════════════════
def chart_income_demographics():
    data = load("acs_income")
    if not data:
        return "<p>Income data unavailable.</p>"

    df = pd.DataFrame(data)
    latest_year = df["year"].max()
    df = df[df["year"] == latest_year]

    ny = df[df["geography"] == "New York"]
    us = df[df["geography"] == "United States"]

    groups = [
        "White alone","Black or African American","Some other race","Asian",
        "American Indian and Alaska Native",
        "Native Hawaiian and Other Pacific Islander",
        "Two or more races","Hispanic or Latino (of any race)",
    ]
    # Map from ACS label → display label
    label_map = {
        "White alone": "White alone",
        "Black or African American": "Black or African American",
        "Some other race": "Some other race",
        "Asian": "Asian",
        "American Indian and Alaska Native": "American Indian and Alaska Native",
        "Native Hawaiian and Other Pacific Islander": "Native Hawaiian and Other Pacific Islander",
        "Two or more races": "Two or more races",
        "Hispanic or Latino (of any race)": "Hispanic or Latino (of any race)",
    }

    ny_vals, us_vals, disp_groups = [], [], []
    for g in groups:
        ny_row = ny[ny["group"].str.contains(g.split()[0], case=False, na=False)].head(1)
        us_row = us[us["group"].str.contains(g.split()[0], case=False, na=False)].head(1)
        ny_val = float(ny_row["value"].values[0]) if not ny_row.empty else None
        us_val = float(us_row["value"].values[0]) if not us_row.empty else None
        ny_vals.append(ny_val)
        us_vals.append(us_val)
        disp_groups.append(g)

    ny_total_row = ny[ny["group"] == "All Households"]
    us_total_row = us[us["group"] == "All Households"]
    ny_total = float(ny_total_row["value"].values[0]) if not ny_total_row.empty else None
    us_total = float(us_total_row["value"].values[0]) if not us_total_row.empty else None

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=disp_groups, y=ny_vals, name="New York",
        marker_color=NY_BLUE,
        hovertemplate="%{x}<br>NY: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=disp_groups, y=us_vals, name="United States",
        mode="markers", marker=dict(color=US_ORANGE, size=12, symbol="circle"),
        hovertemplate="%{x}<br>U.S.: $%{y:,.0f}<extra></extra>",
    ))

    annotations = []
    if ny_total:
        fig.add_hline(y=ny_total, line_color=LIGHT_BLUE, line_dash="dash", line_width=1.5)
        annotations.append(dict(
            text=f"NY Median HH Income = ${ny_total:,.0f}",
            xref="paper", yref="y", x=0.01, y=ny_total,
            font=dict(size=10, color=LIGHT_BLUE), showarrow=False, yshift=8))
    if us_total:
        fig.add_hline(y=us_total, line_color=US_ORANGE, line_dash="dot", line_width=1.5)
        annotations.append(dict(
            text=f"U.S. Median HH Income = ${us_total:,.0f}",
            xref="paper", yref="y", x=0.55, y=us_total,
            font=dict(size=10, color=US_ORANGE), showarrow=False, yshift=8))

    annotations.append(dict(
        text=f"Source: U.S. Census Bureau, {latest_year} 1-Year ACS",
        xref="paper", yref="paper", x=0, y=-0.25,
        font=dict(size=10, color=GREY), showarrow=False))

    fig.update_layout(
        **base_layout(f"Median Household Income by Demographic Group, {latest_year}"),
        xaxis=dict(title="", tickangle=-25),
        yaxis=dict(title="Median Household Income", tickprefix="$", tickformat=","),
        height=450,
        annotations=annotations)
    return fig_to_html(fig, "income_demog")

# ══════════════════════════════════════════════════════════════════════════════
#  ASSEMBLE HTML PAGE
# ══════════════════════════════════════════════════════════════════════════════
def build():
    print("\nBuilding HTML page...")
    meta = load("metadata") or {}
    updated = meta.get("last_updated_display", "Unknown")

    print("  Generating Business Formation charts...")
    bfs_a, bfs_b = chart_bfs()

    print("  Generating GDP charts...")
    gdp_peer   = chart_gdp_peer()
    gdp_ind    = chart_gdp_industry_growth()
    gdp_bar    = chart_gdp_industry_bar()

    print("  Generating Housing charts...")
    housing    = chart_housing()

    print("  Generating JOLTS charts...")
    jolts_l, jolts_r = chart_jolts()

    print("  Generating CES charts...")
    ces_a, ces_b, ces_c = chart_ces()

    print("  Generating LAUS charts...")
    laus_a, laus_b = chart_laus()

    print("  Generating Population & Migration charts...")
    pop_charts = chart_population()
    pop_html   = "".join(pop_charts)

    print("  Generating Poverty chart...")
    poverty    = chart_poverty()

    print("  Generating Income demographics chart...")
    income_d   = chart_income_demographics()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>New York State Economic Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  :root {{
    --ny-blue: #1a3a5c;
    --accent:  #5b9bd5;
    --bg:      #f4f6f9;
    --white:   #ffffff;
    --border:  #dde2ea;
    --text:    #2c3e50;
    --subtext: #6b7c93;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: var(--bg); color: var(--text); }}

  /* ── TOP NAV ────────────────────────────────────────────── */
  header {{
    background: var(--ny-blue);
    color: white;
    padding: 18px 32px;
    position: sticky; top: 0; z-index: 100;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  }}
  header h1 {{ font-size: 1.25rem; font-weight: 700; letter-spacing: 0.5px; }}
  header .updated {{ font-size: 0.8rem; opacity: 0.75; }}
  nav {{
    background: #122a42;
    display: flex; flex-wrap: wrap; gap: 2px; padding: 0 24px;
    position: sticky; top: 60px; z-index: 99;
    box-shadow: 0 2px 4px rgba(0,0,0,0.15);
  }}
  nav a {{
    color: rgba(255,255,255,0.8); text-decoration: none;
    padding: 10px 14px; font-size: 0.82rem; font-weight: 500;
    border-bottom: 3px solid transparent; transition: all 0.2s;
  }}
  nav a:hover {{ color: white; border-bottom-color: var(--accent); }}

  /* ── MAIN LAYOUT ────────────────────────────────────────── */
  main {{ max-width: 1400px; margin: 0 auto; padding: 24px 24px 60px; }}

  section {{
    background: var(--white); border-radius: 8px;
    border: 1px solid var(--border);
    margin-bottom: 28px; overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }}
  .section-header {{
    background: linear-gradient(135deg, var(--ny-blue) 0%, #2a4f78 100%);
    color: white; padding: 14px 24px;
    display: flex; align-items: center; gap: 10px;
  }}
  .section-header h2 {{ font-size: 1.05rem; font-weight: 600; letter-spacing: 0.3px; }}
  .section-header .icon {{ font-size: 1.2rem; }}

  .charts-grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 0;
  }}
  .charts-grid .chart-panel {{ border-right: 1px solid var(--border); }}
  .charts-grid .chart-panel:last-child {{ border-right: none; }}
  .chart-panel {{ padding: 20px 16px 12px; }}
  .chart-full  {{ padding: 20px 16px 12px; }}

  /* Plotly chart containers */
  .js-plotly-plot {{ width: 100% !important; }}

  /* ── KPIS ─────────────────────────────────────────────── */
  .kpi-row {{
    display: flex; flex-wrap: wrap; gap: 12px;
    padding: 16px 24px; border-bottom: 1px solid var(--border);
    background: #fafbfc;
  }}
  .kpi {{
    flex: 1; min-width: 150px;
    background: white; border: 1px solid var(--border); border-radius: 6px;
    padding: 12px 16px; text-align: center;
  }}
  .kpi .label {{ font-size: 0.72rem; color: var(--subtext); text-transform: uppercase;
                  letter-spacing: 0.5px; margin-bottom: 4px; }}
  .kpi .value {{ font-size: 1.5rem; font-weight: 700; color: var(--ny-blue); }}
  .kpi .sub   {{ font-size: 0.72rem; color: var(--subtext); margin-top: 2px; }}

  /* ── RESPONSIVE ───────────────────────────────────────── */
  @media (max-width: 900px) {{
    .charts-grid {{ grid-template-columns: 1fr; }}
    .charts-grid .chart-panel {{ border-right: none; border-bottom: 1px solid var(--border); }}
  }}
</style>
</head>
<body>

<header>
  <h1>🗽 New York State Economic Dashboard</h1>
  <span class="updated">Data updated: {updated}</span>
</header>

<nav>
  <a href="#bfs">Business Formation</a>
  <a href="#gdp">GDP</a>
  <a href="#housing">Housing</a>
  <a href="#jolts">Job Openings</a>
  <a href="#ces">Employment</a>
  <a href="#laus">Labor Force</a>
  <a href="#population">Population</a>
  <a href="#poverty">Poverty</a>
  <a href="#income">Income</a>
</nav>

<main>

<!-- ══ BUSINESS FORMATION ═══════════════════════════════════════════════════ -->
<section id="bfs">
  <div class="section-header">
    <span class="icon">📊</span>
    <h2>Business Formation Statistics</h2>
  </div>
  <div class="charts-grid">
    <div class="chart-panel">{bfs_a}</div>
    <div class="chart-panel">{bfs_b}</div>
  </div>
</section>

<!-- ══ GDP ═══════════════════════════════════════════════════════════════════ -->
<section id="gdp">
  <div class="section-header">
    <span class="icon">📈</span>
    <h2>Gross Domestic Product</h2>
  </div>
  <div class="charts-grid">
    <div class="chart-panel">{gdp_peer}</div>
    <div class="chart-panel">{gdp_ind}</div>
  </div>
  <div class="chart-full" style="border-top:1px solid var(--border)">{gdp_bar}</div>
</section>

<!-- ══ HOUSING ════════════════════════════════════════════════════════════════ -->
<section id="housing">
  <div class="section-header">
    <span class="icon">🏠</span>
    <h2>Housing</h2>
  </div>
  <div class="chart-full">{housing}</div>
</section>

<!-- ══ JOB OPENINGS ══════════════════════════════════════════════════════════ -->
<section id="jolts">
  <div class="section-header">
    <span class="icon">💼</span>
    <h2>Job Openings and Labor Turnover (JOLTS)</h2>
  </div>
  <div class="charts-grid">
    <div class="chart-panel">{jolts_l}</div>
    <div class="chart-panel">{jolts_r}</div>
  </div>
</section>

<!-- ══ EMPLOYMENT ════════════════════════════════════════════════════════════ -->
<section id="ces">
  <div class="section-header">
    <span class="icon">🏭</span>
    <h2>Employment by Industry (CES)</h2>
  </div>
  <div class="charts-grid">
    <div class="chart-panel">{ces_a}</div>
    <div class="chart-panel">{ces_b}</div>
  </div>
  <div class="chart-full" style="border-top:1px solid var(--border)">{ces_c}</div>
</section>

<!-- ══ LABOR FORCE ════════════════════════════════════════════════════════════ -->
<section id="laus">
  <div class="section-header">
    <span class="icon">👷</span>
    <h2>Labor Force and Unemployment</h2>
  </div>
  <div class="charts-grid">
    <div class="chart-panel">{laus_a}</div>
    <div class="chart-panel">{laus_b}</div>
  </div>
</section>

<!-- ══ POPULATION & MIGRATION ════════════════════════════════════════════════ -->
<section id="population">
  <div class="section-header">
    <span class="icon">👥</span>
    <h2>Population and Migration</h2>
  </div>
  <div class="chart-full">{pop_html}</div>
</section>

<!-- ══ POVERTY ════════════════════════════════════════════════════════════════ -->
<section id="poverty">
  <div class="section-header">
    <span class="icon">📉</span>
    <h2>Poverty Demographics</h2>
  </div>
  <div class="chart-full">{poverty}</div>
</section>

<!-- ══ INCOME ═════════════════════════════════════════════════════════════════ -->
<section id="income">
  <div class="section-header">
    <span class="icon">💰</span>
    <h2>Wage Demographics (Median Household Income)</h2>
  </div>
  <div class="chart-full">{income_d}</div>
</section>

</main>

<footer style="text-align:center; padding:20px; color:var(--subtext); font-size:0.8rem; border-top:1px solid var(--border);">
  New York State Economic Dashboard &mdash; Data from U.S. Census Bureau, BLS, BEA, and IRS.
  Updated daily via GitHub Actions.
</footer>

</body>
</html>"""

    out_path = os.path.join(DOCS_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    size_kb = os.path.getsize(out_path) // 1024
    print(f"\n  ✓ Page written → {out_path}  ({size_kb} KB)")

if __name__ == "__main__":
    build()
