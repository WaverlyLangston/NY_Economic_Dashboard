"""
build_page.py  –  Earthy minimal redesign
Color palette inspired by CoDatum: warm cream, rust, sage, tan, dusty blue.
All charts use consistent layout helpers that avoid duplicate-keyword errors.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from config import OUTPUT_FILES, DOCS_DIR
from datetime import datetime, timezone

os.makedirs(DOCS_DIR, exist_ok=True)

# ── Earthy colour palette ─────────────────────────────────────────────────────
CREAM        = "#F7F3EE"
WHITE        = "#FFFFFF"
TEXT_DARK    = "#2A2420"
TEXT_MID     = "#6E6460"
TEXT_LIGHT   = "#A09590"
BORDER       = "#E5DDD5"
PLOT_BG      = "#FDFAF7"

NY_RUST      = "#8B5E52"   # primary NY series
US_SAGE      = "#5C7A6A"   # primary US series
TAN          = "#B89A72"   # tertiary accent
DUSTY_BLUE   = "#7A9BAA"   # quaternary
WARM_BROWN   = "#9B7B6B"
DEEP_SAGE    = "#4A6B5A"
SAND         = "#C4A882"
STEEL        = "#6E8A9A"
MUTED_RED    = "#A05550"
OLIVE        = "#7A8C5A"

INDUSTRY_PALETTE = [
    NY_RUST, US_SAGE, TAN, DUSTY_BLUE, WARM_BROWN,
    DEEP_SAGE, SAND, STEEL, MUTED_RED, OLIVE,
    "#9B8B6B", "#7A9B8A",
]

PEER_COLORS = {
    "New York":      NY_RUST,
    "Massachusetts": DUSTY_BLUE,
    "New Jersey":    TAN,
    "Rhode Island":  US_SAGE,
    "United States": WARM_BROWN,
}

PLOTLY_CONFIG = {
    "displayModeBar": True,
    "responsive": True,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "toImage"],
    "displaylogo": False,
}

# ── Layout helpers ────────────────────────────────────────────────────────────
def base_layout(title="", height=420, bottom_margin=90):
    """
    Returns a mutable dict. Callers may freely overwrite any key
    (including 'legend') before passing **layout to update_layout().
    Never pass legend= as a separate kwarg alongside **base_layout().
    """
    return {
        "title":         dict(text=title, font=dict(size=15, color=TEXT_DARK,
                              family="Georgia, serif"), x=0.0, xanchor="left", pad=dict(b=4)),
        "paper_bgcolor": WHITE,
        "plot_bgcolor":  PLOT_BG,
        "font":          dict(family="'Segoe UI', Arial, sans-serif", size=11, color=TEXT_MID),
        "legend":        dict(orientation="h", yanchor="top", y=-0.18,
                              xanchor="center", x=0.5,
                              font=dict(size=10, color=TEXT_MID),
                              bgcolor="rgba(0,0,0,0)", borderwidth=0),
        "margin":        dict(l=55, r=25, t=55, b=bottom_margin),
        "height":        height,
        "hovermode":     "x unified",
        "xaxis":         dict(showgrid=False, linecolor=BORDER, tickcolor=BORDER,
                              tickfont=dict(color=TEXT_LIGHT, size=10)),
        "yaxis":         dict(gridcolor="#EDE8E3", gridwidth=1, linecolor="rgba(0,0,0,0)",
                              tickfont=dict(color=TEXT_LIGHT, size=10), zeroline=False),
        "hoverlabel":    dict(bgcolor=WHITE, bordercolor=BORDER,
                              font=dict(size=11, color=TEXT_DARK)),
    }

def src_ann(text, bottom_px=-0.22):
    """Source annotation placed below the chart area."""
    return dict(text=text, xref="paper", yref="paper",
                x=0, y=bottom_px, xanchor="left", yanchor="top",
                font=dict(size=9, color=TEXT_LIGHT), showarrow=False)

def dropdown(buttons, x=0.0, y=1.13, label_max_chars=32):
    """Compact, consistently-sized dropdown."""
    # Truncate long labels
    trimmed = []
    for b in buttons:
        nb = dict(b)
        if len(nb.get("label", "")) > label_max_chars:
            nb["label"] = nb["label"][:label_max_chars-1] + "…"
        trimmed.append(nb)
    return [dict(
        buttons=trimmed,
        direction="down",
        showactive=True,
        x=x, xanchor="left",
        y=y, yanchor="top",
        bgcolor=WHITE,
        bordercolor=BORDER,
        borderwidth=1,
        font=dict(size=10, color=TEXT_DARK),
        pad=dict(r=6, t=4, b=4, l=6),
    )]

def fig_to_html(fig, div_id=None):
    kw = dict(full_html=False, include_plotlyjs=False, config=PLOTLY_CONFIG)
    if div_id:
        kw["div_id"] = div_id
    return pio.to_html(fig, **kw)

def load(key):
    path = OUTPUT_FILES.get(key)
    if path and os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    print(f"  Missing data: {key} ({path})")
    return None

# ══════════════════════════════════════════════════════════════════════════════
#  BUSINESS FORMATION
# ══════════════════════════════════════════════════════════════════════════════
def chart_bfs():
    data = load("bfs")
    if not data:
        return "<p>BFS data unavailable.</p>", "<p>BFS data unavailable.</p>"

    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"])
    src = "U.S. Census Bureau, Business Formation Statistics"

    # Chart A – NY Application Levels
    fig_a = go.Figure()
    for col, color, name in [
        ("NY Business Applications",                 NY_RUST,    "Business Applications"),
        ("NY High Propensity Business Applications", DUSTY_BLUE, "High Propensity"),
    ]:
        if col in df.columns:
            fig_a.add_trace(go.Scatter(
                x=df["time"], y=df[col], name=name,
                line=dict(color=color, width=1.5),
                hovertemplate="%{x|%b %Y}: %{y:,.0f}<extra></extra>",
            ))
    lay = base_layout("New York Business Application Levels", bottom_margin=100)
    lay["xaxis"]["title"] = dict(text="Monthly, Seasonally Adjusted",
                                 font=dict(size=10, color=TEXT_LIGHT))
    lay["yaxis"]["title"] = dict(text="Applications", font=dict(size=10, color=TEXT_LIGHT))
    lay["annotations"]    = [src_ann(f"Source: {src}", -0.24)]
    fig_a.update_layout(**lay)

    # Chart B – Per Capita 12-mo MA with dropdown
    traces_ba, traces_hba = [], []
    for col, color, geo in [
        ("NY Business Applications Per Capita 12mo MA",   NY_RUST,  "New York"),
        ("U.S. Business Applications Per Capita 12mo MA", US_SAGE,  "United States"),
    ]:
        y = df[col].tolist() if col in df.columns else [None]*len(df)
        traces_ba.append(go.Scatter(x=df["time"], y=y, name=geo,
            line=dict(color=color, width=2), visible=True,
            hovertemplate=f"{geo}: %{{y:.3f}}<extra></extra>"))
    for col, color, geo in [
        ("NY High Propensity Business Applications Per Capita 12mo MA",   NY_RUST,  "New York"),
        ("U.S. High Propensity Business Applications Per Capita 12mo MA", US_SAGE,  "United States"),
    ]:
        y = df[col].tolist() if col in df.columns else [None]*len(df)
        traces_hba.append(go.Scatter(x=df["time"], y=y, name=geo,
            line=dict(color=color, width=2), visible=False,
            hovertemplate=f"{geo}: %{{y:.3f}}<extra></extra>"))

    n = len(traces_ba)
    fig_b = go.Figure(data=traces_ba + traces_hba)
    lay_b = base_layout("Business Applications per Capita (12-Mo. Moving Avg.)", bottom_margin=100)
    lay_b["xaxis"]["title"]  = dict(text="Monthly, Seasonally Adjusted",
                                    font=dict(size=10, color=TEXT_LIGHT))
    lay_b["yaxis"]["title"]  = dict(text="Per 1,000 People", font=dict(size=10, color=TEXT_LIGHT))
    lay_b["updatemenus"]     = dropdown([
        dict(label="Business Applications", method="update",
             args=[{"visible": [True]*n + [False]*n}]),
        dict(label="High Propensity",        method="update",
             args=[{"visible": [False]*n + [True]*n}]),
    ], x=0.0, y=1.12)
    lay_b["annotations"]     = [src_ann(f"Source: {src}", -0.24)]
    fig_b.update_layout(**lay_b)

    return fig_to_html(fig_a, "bfs_levels"), fig_to_html(fig_b, "bfs_percapita")


# ══════════════════════════════════════════════════════════════════════════════
#  GDP
# ══════════════════════════════════════════════════════════════════════════════
def _index_series(series, n_periods):
    n = min(n_periods, len(series))
    ref = series.iloc[-n]
    if pd.isna(ref) or ref == 0:
        return series * np.nan
    return (series / ref) - 1.0

def chart_gdp_peer():
    data = load("bea_gdp")
    if not data:
        return "<p>GDP data unavailable.</p>"

    df   = pd.DataFrame(data)
    peers = [c for c in df.columns if c != "time"]
    src  = "U.S. Bureau of Economic Analysis, Real GDP"

    def make_traces(n_periods):
        traces = []
        for state in peers:
            if state not in df.columns:
                continue
            series  = pd.to_numeric(df[state], errors="coerce")
            indexed = _index_series(series, n_periods)
            lw = 2.5 if state == "New York" else 1.5
            traces.append(go.Scatter(
                x=df["time"], y=indexed, name=state,
                line=dict(color=PEER_COLORS.get(state, TEXT_LIGHT), width=lw),
                hovertemplate=f"{state}: %{{y:.1%}}<extra></extra>",
            ))
        return traces

    t5, t10 = make_traces(20), make_traces(40)
    n = len(t5)
    fig = go.Figure(data=t5 + t10)
    for i in range(n, len(fig.data)):
        fig.data[i].visible = False
    fig.add_hline(y=0, line_dash="dot", line_color=BORDER, line_width=1)

    lay = base_layout("GDP Index by State", bottom_margin=100)
    lay["xaxis"]["title"] = dict(text="Quarterly", font=dict(size=10, color=TEXT_LIGHT))
    lay["yaxis"]["tickformat"] = ".0%"
    lay["yaxis"]["title"]  = dict(text="Change from Base", font=dict(size=10, color=TEXT_LIGHT))
    lay["updatemenus"]     = dropdown([
        dict(label="Five Year",  method="update", args=[{"visible": [True]*n  + [False]*n}]),
        dict(label="Ten Year",   method="update", args=[{"visible": [False]*n + [True]*n}]),
    ], x=0.0, y=1.12)
    lay["annotations"] = [src_ann(f"Source: {src}", -0.24)]
    fig.update_layout(**lay)
    return fig_to_html(fig, "gdp_peer")

def chart_gdp_industry_growth():
    data = load("bea_gdp_industry")
    if not data:
        return "<p>GDP industry data unavailable.</p>"
    qtr = data.get("quarterly_by_industry", {})
    if not qtr:
        return "<p>GDP quarterly industry data unavailable.</p>"

    skip = {"All industry total","Private industries","Government",
            "Administrative and support and waste management",
            "Management of companies and enterprises"}
    industries = [k for k in qtr.keys() if k not in skip]
    src = "U.S. Bureau of Economic Analysis, Real GDP"

    def make_traces(n_periods):
        out = []
        for i, ind in enumerate(industries):
            sd   = qtr[ind]
            vals = pd.Series(sd["values"])
            if len(vals) < 2:
                continue
            ref = vals.iloc[-min(n_periods, len(vals))]
            if pd.isna(ref) or ref == 0:
                continue
            out.append(go.Scatter(
                x=sd["times"], y=((vals / ref) - 1.0).tolist(),
                name=ind, line=dict(color=INDUSTRY_PALETTE[i % len(INDUSTRY_PALETTE)], width=1.5),
                hovertemplate=f"{ind}: %{{y:.1%}}<extra></extra>",
            ))
        return out

    t5, t10 = make_traces(20), make_traces(40)
    n = len(t5)
    fig = go.Figure(data=t5 + t10)
    for i in range(n, len(fig.data)):
        fig.data[i].visible = False
    fig.add_hline(y=0, line_dash="dot", line_color=BORDER, line_width=1)

    lay = base_layout("New York Industry GDP Growth", height=460, bottom_margin=130)
    lay["legend"]  = dict(orientation="h", yanchor="top", y=-0.22,
                          xanchor="center", x=0.5,
                          font=dict(size=9, color=TEXT_MID), bgcolor="rgba(0,0,0,0)")
    lay["xaxis"]["title"]     = dict(text="Quarterly", font=dict(size=10, color=TEXT_LIGHT))
    lay["yaxis"]["tickformat"] = ".0%"
    lay["yaxis"]["title"]     = dict(text="Change from Base", font=dict(size=10, color=TEXT_LIGHT))
    lay["updatemenus"]        = dropdown([
        dict(label="Five Year", method="update", args=[{"visible": [True]*n  + [False]*n}]),
        dict(label="Ten Year",  method="update", args=[{"visible": [False]*n + [True]*n}]),
    ], x=0.0, y=1.12)
    lay["annotations"] = [src_ann(f"Source: {src}", -0.30)]
    fig.update_layout(**lay)
    return fig_to_html(fig, "gdp_growth")

def chart_gdp_industry_bar():
    data = load("bea_gdp_industry")
    if not data:
        return "<p>GDP industry data unavailable.</p>"
    ann = data.get("annual_by_industry", {})
    if not ann or not isinstance(ann, dict) or "data" not in ann:
        return "<p>GDP industry annual data unavailable.</p>"

    year = ann.get("year", "")
    rows = [r for r in ann["data"] if r.get("DataValue") is not None]
    if not rows:
        return "<p>No industry GDP data.</p>"

    df = pd.DataFrame(rows)
    df["DataValue"] = pd.to_numeric(df["DataValue"], errors="coerce")
    df = df.dropna(subset=["DataValue"]).sort_values("DataValue", ascending=True)
    df["pct"]   = df["share"].map(lambda v: f"  {v:.1%}" if v else "")
    df["label"] = df.apply(
        lambda r: f"${r['DataValue']:,.0f}M{r['pct']}" if pd.notna(r["DataValue"]) else "", axis=1)

    # Colour bars by magnitude
    max_val = df["DataValue"].max()
    df["color"] = df["DataValue"].map(
        lambda v: NY_RUST if v / max_val > 0.5 else (TAN if v / max_val > 0.2 else DUSTY_BLUE))

    fig = go.Figure(go.Bar(
        x=df["DataValue"], y=df["industry"],
        orientation="h",
        text=df["label"], textposition="inside",
        textfont=dict(size=9, color=WHITE),
        marker_color=df["color"],
        hovertemplate="%{y}: $%{x:,.0f}M<extra></extra>",
    ))
    lay = base_layout(f"New York GDP by Industry — {year}", height=520, bottom_margin=70)
    lay["legend"]        = dict(orientation="h", y=-0.08, xanchor="center", x=0.5)
    lay["hovermode"]     = "y unified"
    lay["xaxis"]["title"] = dict(text="Real GDP (Millions USD, Chained 2017 $)",
                                  font=dict(size=10, color=TEXT_LIGHT))
    lay["yaxis"]["title"] = ""
    lay["annotations"]   = [src_ann("Source: U.S. Bureau of Economic Analysis, SAGDP9N", -0.12)]
    fig.update_layout(**lay)
    return fig_to_html(fig, "gdp_bar")


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
    src = "U.S. Census Bureau, American Community Survey (ACS 1-Year)"

    # Two separate figures stacked vertically in HTML — avoids subplot-title-before-section-header issue
    fig1 = go.Figure()
    for d, color, name in [(ny, NY_RUST, "New York"), (us, US_SAGE, "United States")]:
        fig1.add_trace(go.Scatter(
            x=d["year"], y=d["rental_vacancy_rate"],
            name=name, line=dict(color=color, width=2),
            hovertemplate=f"{name}: %{{y:.1%}}<extra></extra>",
        ))
    lay1 = base_layout("Rental Vacancy Rate", height=320, bottom_margin=90)
    lay1["yaxis"]["tickformat"] = ".1%"
    lay1["yaxis"]["title"] = dict(text="Rate", font=dict(size=10, color=TEXT_LIGHT))
    lay1["xaxis"]["title"] = dict(text="Year", font=dict(size=10, color=TEXT_LIGHT))
    fig1.update_layout(**lay1)

    fig2 = go.Figure()
    ny_yoy = ny.set_index("year")["total_units"].pct_change()
    us_yoy = us.set_index("year")["total_units"].pct_change()
    for yrs, yoy, color, name in [
        (ny["year"].values[1:], ny_yoy.dropna().values, NY_RUST,  "New York"),
        (us["year"].values[1:], us_yoy.dropna().values, US_SAGE,  "United States"),
    ]:
        fig2.add_trace(go.Scatter(
            x=yrs, y=yoy, name=name, line=dict(color=color, width=2),
            hovertemplate=f"{name}: %{{y:.2%}}<extra></extra>",
        ))
    lay2 = base_layout("Changes in Housing Stock, Year-Over-Year", height=320, bottom_margin=100)
    lay2["yaxis"]["tickformat"] = ".2%"
    lay2["yaxis"]["title"] = dict(text="YoY Change", font=dict(size=10, color=TEXT_LIGHT))
    lay2["xaxis"]["title"] = dict(text="Year", font=dict(size=10, color=TEXT_LIGHT))
    lay2["annotations"]    = [src_ann(f"Source: {src}", -0.24)]
    fig2.update_layout(**lay2)

    return fig_to_html(fig1, "housing_vacancy") + fig_to_html(fig2, "housing_stock")


# ══════════════════════════════════════════════════════════════════════════════
#  JOB OPENINGS (JOLTS)
# ══════════════════════════════════════════════════════════════════════════════
def chart_jolts():
    data = load("bls_jolts")
    if not data or not data.get("monthly"):
        return "<p>JOLTS data unavailable.</p>", "<p>JOLTS data unavailable.</p>"

    df = pd.DataFrame(data["monthly"])
    df["time"] = pd.to_datetime(df["time"])
    src = "U.S. Bureau of Labor Statistics, JOLTS"

    LEVELS = {
        "NY Job Openings Level":           ("Job Openings",         DUSTY_BLUE),
        "NY Hires Level":                  ("Hires",                NY_RUST),
        "NY Total Separations Level":      ("Total Separations",    US_SAGE),
        "NY Layoffs and Discharges Level": ("Layoffs & Discharges", TAN),
        "NY Quits Level":                  ("Quits",                WARM_BROWN),
    }
    fig_a = go.Figure()
    for col, (label, color) in LEVELS.items():
        if col in df.columns:
            fig_a.add_trace(go.Scatter(x=df["time"], y=df[col], name=label,
                line=dict(color=color, width=1.5),
                hovertemplate=f"{label}: %{{y:,.0f}}<extra></extra>"))
    lay_a = base_layout("New York Job Market Levels", bottom_margin=100)
    lay_a["xaxis"]["title"] = dict(text="Monthly, Seasonally Adjusted", font=dict(size=10, color=TEXT_LIGHT))
    lay_a["yaxis"]["title"] = dict(text="Workers", font=dict(size=10, color=TEXT_LIGHT))
    lay_a["annotations"]    = [src_ann(f"Source: {src}", -0.24)]
    fig_a.update_layout(**lay_a)

    RATES = {
        "Unemployed per Opening": ("NY Unemployed per Job Opening Ratio", "U.S. Unemployed per Job Opening Ratio"),
        "Job Openings Rate":      ("NY Job Openings Rate",                "U.S. Job Openings Rate"),
        "Hires Rate":             ("NY Hires Rate",                       "U.S. Hires Rate"),
        "Quits Rate":             ("NY Quits Rate",                       "U.S. Quits Rate"),
        "Layoffs Rate":           ("NY Layoffs and Discharges Rate",      "U.S. Layoffs and Discharges Rate"),
        "Separations Rate":       ("NY Total Separations Rate",           "U.S. Total Separations Rate"),
    }
    all_traces, buttons, idx = [], [], 0
    for metric, (ny_col, us_col) in RATES.items():
        is_first = (idx == 0)
        fmt = ".2f" if "Opening" in metric else ".1%"
        for col, color, geo in [(ny_col, NY_RUST, "New York"), (us_col, US_SAGE, "United States")]:
            y = df[col].tolist() if col in df.columns else [None]*len(df)
            all_traces.append(go.Scatter(x=df["time"], y=y, name=geo,
                line=dict(color=color, width=2), visible=is_first,
                hovertemplate=f"{geo}: %{{y:{fmt}}}<extra></extra>"))
        buttons.append(dict(label=metric, method="update",
            args=[{"visible": [i in [idx, idx+1] for i in range(len(RATES)*2)]}]))
        idx += 2

    fig_b = go.Figure(data=all_traces)
    lay_b = base_layout("New York and U.S. Job Market Rates", bottom_margin=100)
    lay_b["xaxis"]["title"] = dict(text="Monthly, Seasonally Adjusted", font=dict(size=10, color=TEXT_LIGHT))
    lay_b["yaxis"]["title"] = dict(text="Rate", font=dict(size=10, color=TEXT_LIGHT))
    lay_b["updatemenus"]    = dropdown(buttons, x=0.0, y=1.12)
    lay_b["annotations"]    = [src_ann(f"Source: {src}", -0.24)]
    fig_b.update_layout(**lay_b)

    return fig_to_html(fig_a, "jolts_levels"), fig_to_html(fig_b, "jolts_rates")


# ══════════════════════════════════════════════════════════════════════════════
#  EMPLOYMENT (CES)
# ══════════════════════════════════════════════════════════════════════════════
def chart_ces():
    data = load("bls_ces")
    if not data:
        return "<p>CES data unavailable.</p>", "<p>CES data unavailable.</p>", "<p>CES data unavailable.</p>"

    monthly  = pd.DataFrame(data.get("monthly", []))
    changes  = data.get("changes", [])
    ref_date = data.get("reference_date", "")
    src      = "U.S. Bureau of Labor Statistics, CES"

    if monthly.empty:
        return "<p>CES monthly data unavailable.</p>", "", ""
    monthly["time"] = pd.to_datetime(monthly["time"])

    industry_cols = [c for c in monthly.columns
                     if c.endswith(" Index") and c not in
                     ("Total Nonfarm Index","Total Private Index","Government Index")]

    # Chart A – Jobs Index by Industry
    fig_a = go.Figure()
    for i, col in enumerate(industry_cols):
        label = col.replace(" Index", "")
        fig_a.add_trace(go.Scatter(x=monthly["time"], y=monthly[col], name=label,
            line=dict(color=INDUSTRY_PALETTE[i % len(INDUSTRY_PALETTE)], width=1.5),
            hovertemplate=f"{label}: %{{y:.1%}}<extra></extra>"))
    fig_a.add_hline(y=0, line_dash="dot", line_color=BORDER, line_width=1)
    lay_a = base_layout("New York Jobs Index by Industry", height=440, bottom_margin=130)
    lay_a["legend"]  = dict(orientation="h", yanchor="top", y=-0.22,
                            xanchor="center", x=0.5,
                            font=dict(size=9, color=TEXT_MID), bgcolor="rgba(0,0,0,0)")
    lay_a["xaxis"]["title"] = dict(text="Monthly, Seasonally Adjusted", font=dict(size=10, color=TEXT_LIGHT))
    lay_a["yaxis"]["tickformat"] = ".0%"
    lay_a["yaxis"]["title"] = dict(text="Change from Base", font=dict(size=10, color=TEXT_LIGHT))
    lay_a["annotations"] = [src_ann(f"Source: {src} (base: {ref_date})", -0.30)]
    fig_a.update_layout(**lay_a)

    # Chart B – Government vs Total Private
    fig_b = go.Figure()
    for col, color, label in [
        ("Total Private Index", NY_RUST,    "Total Private"),
        ("Government Index",    DUSTY_BLUE, "Government"),
    ]:
        if col in monthly.columns:
            fig_b.add_trace(go.Scatter(x=monthly["time"], y=monthly[col], name=label,
                line=dict(color=color, width=2.5),
                hovertemplate=f"{label}: %{{y:.1%}}<extra></extra>"))
    fig_b.add_hline(y=0, line_dash="dot", line_color=BORDER, line_width=1)
    lay_b = base_layout("Government vs. Total Private Employment", bottom_margin=100)
    lay_b["xaxis"]["title"] = dict(text="Monthly, Seasonally Adjusted", font=dict(size=10, color=TEXT_LIGHT))
    lay_b["yaxis"]["tickformat"] = ".0%"
    lay_b["yaxis"]["title"] = dict(text="Change from Base", font=dict(size=10, color=TEXT_LIGHT))
    lay_b["annotations"] = [src_ann(f"Source: {src} (base: {ref_date})", -0.24)]
    fig_b.update_layout(**lay_b)

    # Chart C – Change in Jobs bar
    if not changes:
        html_c = ""
    else:
        df_c   = pd.DataFrame(changes).dropna(subset=["change"])
        df_c   = df_c[~df_c["industry"].isin(["Total Nonfarm","Total Private"])].sort_values("change")
        as_of  = df_c["as_of"].iloc[0] if not df_c.empty else ""
        colors = [NY_RUST if v >= 0 else US_SAGE for v in df_c["change"]]

        fig_c = go.Figure(go.Bar(
            x=df_c["industry"], y=df_c["change"],
            marker_color=colors,
            hovertemplate="%{x}: %{y:+,.0f} jobs<extra></extra>",
        ))
        lay_c = base_layout(f"Change in Number of Jobs by Industry — {as_of}", height=380, bottom_margin=110)
        lay_c["xaxis"]["tickangle"] = -30
        lay_c["xaxis"]["title"]     = ""
        lay_c["yaxis"]["title"]     = dict(text="Jobs", font=dict(size=10, color=TEXT_LIGHT))
        lay_c["annotations"]        = [src_ann(f"Source: {src}", -0.28)]
        fig_c.update_layout(**lay_c)
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
    src = "U.S. Bureau of Labor Statistics, LAUS"

    # Chart A – NY Levels (dual axis)
    fig_a = make_subplots(specs=[[{"secondary_y": True}]])
    for col, color, name in [
        ("NY Labor Force Level", DUSTY_BLUE, "Labor Force"),
        ("NY Employment Level",  NY_RUST,    "Employment"),
    ]:
        if col in df.columns:
            fig_a.add_trace(go.Scatter(x=df["time"], y=df[col], name=name,
                line=dict(color=color, width=2),
                hovertemplate=f"{name}: %{{y:,.0f}}<extra></extra>"), secondary_y=False)
    if "NY Unemployment Level" in df.columns:
        fig_a.add_trace(go.Scatter(x=df["time"], y=df["NY Unemployment Level"],
            name="Unemployment", line=dict(color=TAN, width=2),
            hovertemplate="Unemployment: %{y:,.0f}<extra></extra>"), secondary_y=True)

    fig_a.update_yaxes(title_text="Employment & Labor Force", secondary_y=False,
                       gridcolor="#EDE8E3", tickfont=dict(color=TEXT_LIGHT, size=10))
    fig_a.update_yaxes(title_text="Unemployed", secondary_y=True,
                       tickfont=dict(color=TEXT_LIGHT, size=10))
    fig_a.update_layout(
        title=dict(text="New York State Labor Force", font=dict(size=15, color=TEXT_DARK,
                   family="Georgia, serif"), x=0, xanchor="left"),
        paper_bgcolor=WHITE, plot_bgcolor=PLOT_BG,
        font=dict(family="'Segoe UI', Arial, sans-serif", size=11, color=TEXT_MID),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5,
                    font=dict(size=10, color=TEXT_MID), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=55, r=25, t=55, b=100),
        height=420, hovermode="x unified",
        xaxis=dict(title=dict(text="Monthly, Seasonally Adjusted",
                              font=dict(size=10, color=TEXT_LIGHT)),
                   showgrid=False, linecolor=BORDER, tickfont=dict(color=TEXT_LIGHT, size=10)),
        annotations=[src_ann(f"Source: {src}", -0.24)],
    )

    # Chart B – Rates dropdown
    RATE_METRICS = {
        "Unemployment Rate":              ("NY Unemployment Rate",              "U.S. Unemployment Rate"),
        "Labor Force Participation Rate": ("NY Labor Force Participation Rate", "U.S. Labor Force Participation Rate"),
        "Employment-Population Ratio":    ("NY Employment-Population Ratio",    "U.S. Employment-Population Ratio"),
    }
    all_traces, buttons, idx = [], [], 0
    for metric, (ny_col, us_col) in RATE_METRICS.items():
        is_first = (idx == 0)
        for col, color, geo in [(ny_col, NY_RUST, "New York"), (us_col, US_SAGE, "United States")]:
            y = df[col].tolist() if col in df.columns else [None]*len(df)
            all_traces.append(go.Scatter(x=df["time"], y=y, name=geo,
                line=dict(color=color, width=2), visible=is_first,
                hovertemplate=f"{geo}: %{{y:.1%}}<extra></extra>"))
        buttons.append(dict(label=metric, method="update",
            args=[{"visible": [i in [idx, idx+1] for i in range(len(RATE_METRICS)*2)]}]))
        idx += 2

    fig_b = go.Figure(data=all_traces)
    lay_b = base_layout("New York and U.S. Labor Force Rates", bottom_margin=100)
    lay_b["xaxis"]["title"]     = dict(text="Monthly, Seasonally Adjusted", font=dict(size=10, color=TEXT_LIGHT))
    lay_b["yaxis"]["tickformat"] = ".1%"
    lay_b["yaxis"]["title"]     = dict(text="Rate", font=dict(size=10, color=TEXT_LIGHT))
    lay_b["updatemenus"]        = dropdown(buttons, x=0.0, y=1.12)
    lay_b["annotations"]        = [src_ann(f"Source: {src}", -0.24)]
    fig_b.update_layout(**lay_b)

    return fig_to_html(fig_a, "laus_levels"), fig_to_html(fig_b, "laus_rates")


# ══════════════════════════════════════════════════════════════════════════════
#  POPULATION & MIGRATION
# ══════════════════════════════════════════════════════════════════════════════
def chart_population():
    pop_data = load("pep_population")
    mig_data = load("irs_migration")
    age_data = load("pep_age")
    charts   = []

    # Population line
    if pop_data:
        ny = pd.DataFrame(pop_data)
        ny = ny[ny["geography"] == "New York"].sort_values("year")
        if not ny.empty:
            fig = go.Figure(go.Scatter(x=ny["year"], y=ny["population"],
                line=dict(color=NY_RUST, width=2.5),
                fill="tozeroy", fillcolor=f"rgba(139,94,82,0.08)",
                hovertemplate="Year %{x}: %{y:,.0f}<extra></extra>"))
            lay = base_layout("New York State Population", height=320, bottom_margin=85)
            lay["yaxis"]["tickformat"] = ","
            lay["yaxis"]["title"] = dict(text="Population", font=dict(size=10, color=TEXT_LIGHT))
            lay["xaxis"]["title"] = dict(text="Year", font=dict(size=10, color=TEXT_LIGHT))
            lay["annotations"]    = [src_ann("Source: U.S. Census Bureau, Population Estimates", -0.22)]
            fig.update_layout(**lay)
            charts.append(fig_to_html(fig, "pop_total"))

    # Migration – grouped bar with inflow, outflow, net
    if mig_data and mig_data.get("annual_net"):
        net_df = pd.DataFrame(mig_data["annual_net"])
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Inflow",  x=net_df["year_label"],
            y=net_df["inflow_people"],  marker_color=US_SAGE,
            hovertemplate="%{x} Inflow: %{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Bar(name="Outflow", x=net_df["year_label"],
            y=[-v for v in net_df["outflow_people"]], marker_color=TAN,
            hovertemplate="%{x} Outflow: %{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Scatter(name="Net Migration", x=net_df["year_label"],
            y=net_df["net_people"], mode="lines+markers",
            line=dict(color=NY_RUST, width=2.5),
            marker=dict(color=NY_RUST, size=7),
            hovertemplate="%{x} Net: %{y:+,.0f}<extra></extra>"))
        fig.add_hline(y=0, line_color=BORDER, line_width=1)
        lay = base_layout("New York State Domestic Migration", height=360, bottom_margin=105)
        lay["barmode"]            = "relative"
        lay["yaxis"]["title"]     = dict(text="People", font=dict(size=10, color=TEXT_LIGHT))
        lay["xaxis"]["title"]     = dict(text="Year", font=dict(size=10, color=TEXT_LIGHT))
        lay["annotations"]        = [src_ann("Source: IRS Statistics of Income, State-to-State Migration", -0.26)]
        fig.update_layout(**lay)
        charts.append(fig_to_html(fig, "migration"))

    # Age stacked bar
    if age_data:
        age_df = pd.DataFrame(age_data)
        if not age_df.empty:
            age_order  = ["Under 5","5 To 13","14 To 17","18 To 24","25 To 44","45 To 64","65 And Over"]
            age_colors = ["#A0C878","#7A9BAA","#C4A882","#B89A72","#8B5E52","#5C7A6A","#2A2420"]
            fig = go.Figure()
            for age, color in zip(age_order, age_colors):
                grp = age_df[age_df["age_group"] == age].sort_values("year")
                if grp.empty:
                    continue
                fig.add_trace(go.Bar(x=grp["year"], y=grp["population"],
                    name=age, marker_color=color,
                    hovertemplate=f"{age}: %{{y:,.0f}}<extra></extra>"))
            lay = base_layout("Age Distribution of New York State Population", height=360, bottom_margin=100)
            lay["barmode"]            = "stack"
            lay["yaxis"]["tickformat"] = ","
            lay["yaxis"]["title"]     = dict(text="Population", font=dict(size=10, color=TEXT_LIGHT))
            lay["xaxis"]["title"]     = dict(text="Year", font=dict(size=10, color=TEXT_LIGHT))
            lay["annotations"]        = [src_ann("Source: U.S. Census Bureau, Population Estimates", -0.24)]
            fig.update_layout(**lay)
            charts.append(fig_to_html(fig, "pop_age"))

    return "".join(charts) if charts else "<p>Population data unavailable.</p>"


# ══════════════════════════════════════════════════════════════════════════════
#  POVERTY DEMOGRAPHICS
# ══════════════════════════════════════════════════════════════════════════════
def chart_poverty():
    data = load("acs_poverty")
    if not data:
        return "<p>Poverty data unavailable.</p>"

    df          = pd.DataFrame(data)
    latest_year = df["year"].max()
    df          = df[df["year"] == latest_year]
    ny          = df[df["geography"] == "New York"]
    us          = df[df["geography"] == "United States"]

    groups = [
        "White alone","Black or African American alone",
        "Some other race alone","Asian alone",
        "American Indian and Alaska Native alone",
        "Two or more races","Hispanic or Latino (of any race)",
        "Female","Male",
    ]
    ny_r, us_r = [], []
    for g in groups:
        nr = ny[ny["group"] == g];  ur = us[us["group"] == g]
        ny_r.append(nr["rate"].values[0] if not nr.empty else None)
        us_r.append(ur["rate"].values[0] if not ur.empty else None)

    ny_tr = ny[ny["group"]=="Total"]["rate"].values
    us_tr = us[us["group"]=="Total"]["rate"].values
    ny_total = ny_tr[0] if len(ny_tr) else None
    us_total = us_tr[0] if len(us_tr) else None

    fig = go.Figure()
    fig.add_trace(go.Bar(x=groups, y=ny_r, name="New York",
        marker_color=NY_RUST, hovertemplate="%{x}<br>NY: %{y:.1%}<extra></extra>"))
    fig.add_trace(go.Scatter(x=groups, y=us_r, name="United States",
        mode="markers", marker=dict(color=US_SAGE, size=12, symbol="circle"),
        hovertemplate="%{x}<br>U.S.: %{y:.1%}<extra></extra>"))

    anns = []
    if ny_total is not None:
        fig.add_hline(y=ny_total, line_color=NY_RUST, line_dash="dash", line_width=1, opacity=0.5)
        anns.append(dict(text=f"NY Total: {ny_total:.1%}", xref="paper", yref="y",
            x=0.01, y=ny_total, yshift=8, font=dict(size=9, color=NY_RUST), showarrow=False))
    if us_total is not None:
        fig.add_hline(y=us_total, line_color=US_SAGE, line_dash="dot", line_width=1, opacity=0.5)
        anns.append(dict(text=f"U.S. Total: {us_total:.1%}", xref="paper", yref="y",
            x=0.6, y=us_total, yshift=8, font=dict(size=9, color=US_SAGE), showarrow=False))
    anns.append(src_ann(f"Source: U.S. Census Bureau, {latest_year} 1-Year ACS", -0.28))

    lay = base_layout(f"Poverty Rate by Demographic Group — {latest_year}", height=420, bottom_margin=115)
    lay["xaxis"]["tickangle"] = -25
    lay["xaxis"]["title"]     = ""
    lay["yaxis"]["tickformat"] = ".0%"
    lay["yaxis"]["title"]     = dict(text="Poverty Rate", font=dict(size=10, color=TEXT_LIGHT))
    lay["annotations"]        = anns
    fig.update_layout(**lay)
    return fig_to_html(fig, "poverty")


# ══════════════════════════════════════════════════════════════════════════════
#  INCOME DEMOGRAPHICS
# ══════════════════════════════════════════════════════════════════════════════
def chart_income():
    data = load("acs_income")
    if not data:
        return "<p>Income data unavailable.</p>"

    df          = pd.DataFrame(data)
    latest_year = df["year"].max()
    df          = df[df["year"] == latest_year]
    ny          = df[df["geography"] == "New York"]
    us          = df[df["geography"] == "United States"]

    groups = [
        "White alone","Black or African American","Some other race","Asian",
        "American Indian and Alaska Native",
        "Two or more races","Hispanic or Latino (of any race)",
    ]
    ny_v, us_v, disp = [], [], []
    for g in groups:
        nr = ny[ny["group"].str.contains(g.split()[0], case=False, na=False)].head(1)
        ur = us[us["group"].str.contains(g.split()[0], case=False, na=False)].head(1)
        ny_v.append(float(nr["value"].values[0]) if not nr.empty and nr["value"].values[0] else None)
        us_v.append(float(ur["value"].values[0]) if not ur.empty and ur["value"].values[0] else None)
        disp.append(g)

    ny_tot = ny[ny["group"]=="All Households"]["value"].values
    us_tot = us[us["group"]=="All Households"]["value"].values
    ny_all = float(ny_tot[0]) if len(ny_tot) and ny_tot[0] else None
    us_all = float(us_tot[0]) if len(us_tot) and us_tot[0] else None

    fig = go.Figure()
    fig.add_trace(go.Bar(x=disp, y=ny_v, name="New York",
        marker_color=NY_RUST, hovertemplate="%{x}<br>NY: $%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=disp, y=us_v, name="United States",
        mode="markers", marker=dict(color=US_SAGE, size=12, symbol="circle"),
        hovertemplate="%{x}<br>U.S.: $%{y:,.0f}<extra></extra>"))

    anns = []
    if ny_all:
        fig.add_hline(y=ny_all, line_color=NY_RUST, line_dash="dash", line_width=1, opacity=0.5)
        anns.append(dict(text=f"NY Median: ${ny_all:,.0f}", xref="paper", yref="y",
            x=0.01, y=ny_all, yshift=8, font=dict(size=9, color=NY_RUST), showarrow=False))
    if us_all:
        fig.add_hline(y=us_all, line_color=US_SAGE, line_dash="dot", line_width=1, opacity=0.5)
        anns.append(dict(text=f"U.S. Median: ${us_all:,.0f}", xref="paper", yref="y",
            x=0.55, y=us_all, yshift=8, font=dict(size=9, color=US_SAGE), showarrow=False))
    anns.append(src_ann(f"Source: U.S. Census Bureau, {latest_year} 1-Year ACS", -0.28))

    lay = base_layout(f"Median Household Income by Demographic Group — {latest_year}", height=420, bottom_margin=115)
    lay["xaxis"]["tickangle"] = -25
    lay["xaxis"]["title"]     = ""
    lay["yaxis"]["tickprefix"] = "$"
    lay["yaxis"]["tickformat"] = ","
    lay["yaxis"]["title"]     = dict(text="Median HH Income", font=dict(size=10, color=TEXT_LIGHT))
    lay["annotations"]        = anns
    fig.update_layout(**lay)
    return fig_to_html(fig, "income_demog")


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE ASSEMBLY
# ══════════════════════════════════════════════════════════════════════════════
def build():
    print("\nBuilding HTML page...")
    meta    = load("metadata") or {}
    updated = meta.get("last_updated_display", "Unknown")

    print("  Generating Business Formation...")
    bfs_a, bfs_b = chart_bfs()

    print("  Generating GDP...")
    gdp_peer = chart_gdp_peer()
    gdp_ind  = chart_gdp_industry_growth()
    gdp_bar  = chart_gdp_industry_bar()

    print("  Generating Housing...")
    housing  = chart_housing()

    print("  Generating JOLTS...")
    jolts_l, jolts_r = chart_jolts()

    print("  Generating CES...")
    ces_a, ces_b, ces_c = chart_ces()

    print("  Generating LAUS...")
    laus_a, laus_b = chart_laus()

    print("  Generating Population & Migration...")
    pop_html = chart_population()

    print("  Generating Poverty...")
    poverty  = chart_poverty()

    print("  Generating Income...")
    income_d = chart_income()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>New York State Economic Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  :root {{
    --cream:      #F7F3EE;
    --white:      #FFFFFF;
    --text-dark:  #2A2420;
    --text-mid:   #6E6460;
    --text-light: #A09590;
    --border:     #E5DDD5;
    --rust:       #8B5E52;
    --sage:       #5C7A6A;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    background: var(--cream);
    color: var(--text-dark);
    line-height: 1.5;
  }}

  /* ── NAV ── */
  header {{
    background: var(--white);
    border-bottom: 1px solid var(--border);
    padding: 0 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky; top: 0; z-index: 100;
    height: 56px;
  }}
  .site-title {{
    font-family: Georgia, serif;
    font-size: 1rem;
    font-weight: normal;
    color: var(--text-dark);
    letter-spacing: 0.5px;
  }}
  .site-title span {{ color: var(--rust); }}
  .updated {{
    font-size: 0.72rem;
    color: var(--text-light);
  }}

  nav {{
    background: var(--white);
    border-bottom: 1px solid var(--border);
    padding: 0 40px;
    display: flex;
    flex-wrap: wrap;
    gap: 0;
    position: sticky; top: 56px; z-index: 99;
  }}
  nav a {{
    color: var(--text-light);
    text-decoration: none;
    font-size: 0.75rem;
    letter-spacing: 0.4px;
    text-transform: uppercase;
    padding: 10px 16px;
    border-bottom: 2px solid transparent;
    transition: all 0.15s;
  }}
  nav a:hover {{
    color: var(--rust);
    border-bottom-color: var(--rust);
  }}

  /* ── LAYOUT ── */
  main {{
    max-width: 1280px;
    margin: 0 auto;
    padding: 48px 40px 80px;
  }}

  /* ── SECTION ── */
  .section {{
    margin-bottom: 64px;
  }}
  .section-title {{
    font-family: Georgia, serif;
    font-size: 1.4rem;
    font-weight: normal;
    color: var(--text-dark);
    margin-bottom: 4px;
  }}
  .section-subtitle {{
    font-size: 0.78rem;
    color: var(--text-light);
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 24px;
  }}
  .section-divider {{
    width: 32px;
    height: 2px;
    background: var(--rust);
    margin-bottom: 28px;
    opacity: 0.6;
  }}

  /* ── CHART GRIDS ── */
  .grid-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 32px;
  }}
  .grid-1 {{
    display: grid;
    grid-template-columns: 1fr;
  }}
  .chart-wrap {{
    background: var(--white);
    border-radius: 4px;
    padding: 8px 4px 4px;
  }}
  .chart-full {{
    background: var(--white);
    border-radius: 4px;
    padding: 8px 4px 4px;
    margin-top: 32px;
  }}

  /* ── PLOTLY OVERRIDES ── */
  .js-plotly-plot {{ width: 100% !important; }}

  /* ── RESPONSIVE ── */
  @media (max-width: 860px) {{
    .grid-2 {{ grid-template-columns: 1fr; gap: 20px; }}
    main {{ padding: 32px 20px 60px; }}
    header, nav {{ padding: 0 20px; }}
  }}
</style>
</head>
<body>

<header>
  <div class="site-title"><span>NY</span> Economic Dashboard</div>
  <div class="updated">Updated {updated}</div>
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

<!-- BUSINESS FORMATION -->
<div class="section" id="bfs">
  <div class="section-subtitle">Census Bureau</div>
  <h2 class="section-title">Business Formation Statistics</h2>
  <div class="section-divider"></div>
  <div class="grid-2">
    <div class="chart-wrap">{bfs_a}</div>
    <div class="chart-wrap">{bfs_b}</div>
  </div>
</div>

<!-- GDP -->
<div class="section" id="gdp">
  <div class="section-subtitle">Bureau of Economic Analysis</div>
  <h2 class="section-title">Gross Domestic Product</h2>
  <div class="section-divider"></div>
  <div class="grid-2">
    <div class="chart-wrap">{gdp_peer}</div>
    <div class="chart-wrap">{gdp_ind}</div>
  </div>
  <div class="chart-full">{gdp_bar}</div>
</div>

<!-- HOUSING -->
<div class="section" id="housing">
  <div class="section-subtitle">Census Bureau, American Community Survey</div>
  <h2 class="section-title">Housing</h2>
  <div class="section-divider"></div>
  <div class="grid-2">
    <div class="chart-wrap">{housing}</div>
  </div>
</div>

<!-- JOB OPENINGS -->
<div class="section" id="jolts">
  <div class="section-subtitle">Bureau of Labor Statistics</div>
  <h2 class="section-title">Job Openings &amp; Labor Turnover</h2>
  <div class="section-divider"></div>
  <div class="grid-2">
    <div class="chart-wrap">{jolts_l}</div>
    <div class="chart-wrap">{jolts_r}</div>
  </div>
</div>

<!-- EMPLOYMENT -->
<div class="section" id="ces">
  <div class="section-subtitle">Bureau of Labor Statistics, Current Employment Statistics</div>
  <h2 class="section-title">Employment by Industry</h2>
  <div class="section-divider"></div>
  <div class="grid-2">
    <div class="chart-wrap">{ces_a}</div>
    <div class="chart-wrap">{ces_b}</div>
  </div>
  <div class="chart-full">{ces_c}</div>
</div>

<!-- LABOR FORCE -->
<div class="section" id="laus">
  <div class="section-subtitle">Bureau of Labor Statistics, LAUS</div>
  <h2 class="section-title">Labor Force &amp; Unemployment</h2>
  <div class="section-divider"></div>
  <div class="grid-2">
    <div class="chart-wrap">{laus_a}</div>
    <div class="chart-wrap">{laus_b}</div>
  </div>
</div>

<!-- POPULATION -->
<div class="section" id="population">
  <div class="section-subtitle">Census Bureau &amp; IRS Statistics of Income</div>
  <h2 class="section-title">Population &amp; Migration</h2>
  <div class="section-divider"></div>
  {pop_html}
</div>

<!-- POVERTY -->
<div class="section" id="poverty">
  <div class="section-subtitle">Census Bureau, American Community Survey</div>
  <h2 class="section-title">Poverty Demographics</h2>
  <div class="section-divider"></div>
  <div class="grid-1">
    <div class="chart-wrap">{poverty}</div>
  </div>
</div>

<!-- INCOME -->
<div class="section" id="income">
  <div class="section-subtitle">Census Bureau, American Community Survey</div>
  <h2 class="section-title">Median Household Income</h2>
  <div class="section-divider"></div>
  <div class="grid-1">
    <div class="chart-wrap">{income_d}</div>
  </div>
</div>

</main>

<footer style="border-top:1px solid var(--border); background:var(--white);
               padding:24px 40px; text-align:center;
               font-size:0.75rem; color:var(--text-light);">
  New York State Economic Dashboard &mdash;
  Data from U.S. Census Bureau, Bureau of Labor Statistics, Bureau of Economic Analysis, and IRS.
  Updated daily via GitHub Actions.
</footer>

</body>
</html>"""

    out_path = os.path.join(DOCS_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n  ✓ Page written → {out_path}  ({os.path.getsize(out_path)//1024} KB)")

if __name__ == "__main__":
    build()
