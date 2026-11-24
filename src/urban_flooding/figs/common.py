"""Shared loaders, style and helpers for the publication figures (outputs/full)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

PROC = Path("data/processed/full")
RAW = Path("data/raw/full")
OUT = Path("outputs/full")
FIG = OUT / "figures"
TAB = OUT / "tables"
for d in (FIG, TAB):
    d.mkdir(parents=True, exist_ok=True)

# Validated categorical order (dataviz reference palette, light mode).
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
SEQ = "Blues"
SEQ_HOT = LinearSegmentedColormap.from_list("hot1", ["#fbf1e9", "#f5b48f", "#eb6834", "#a8360c", "#5a1a04"])
DIV = "RdBu_r"

# Variable groups used consistently across figures.
GROUPS = {
    "Topography": ["elev_p10", "elev_mean", "relief", "slope_mean", "tpi_mean", "tpi_p10", "twi_p90",
                   "dep_frac", "dep_depth_mean", "dist_shore_m"],
    "Built form": ["impervious", "building_cov", "road_frac", "far_cell", "floors_mean", "yearbuilt_med",
                   "lu_res", "lu_comm", "lu_ind", "lu_open"],
    "Greenness": ["canopy", "grass", "green"],
    "Drainage": ["cb_density", "cb_per_road_ha", "cb_nn_dist_m", "ms4_frac", "gi_density"],
    "Population / reporting": ["pop", "rpl_themes", "minority_rate", "poverty_rate", "noveh_rate"],
}
GROUP_COLOR = dict(zip(GROUPS, [C[0], C[1], C[2], C[6], C[4]]))
LABEL = {
    "elev_p10": "Elevation (10th pct, m)", "elev_mean": "Mean elevation (m)", "relief": "Relief (m)",
    "slope_mean": "Mean slope (°)", "tpi_mean": "Topographic position (m)", "tpi_p10": "TPI 10th pct (m)",
    "twi_p90": "TWI 90th pct", "dep_frac": "Depression area share", "dep_depth_mean": "Depression depth (m)",
    "dist_shore_m": "Distance to shore (m)", "impervious": "Impervious share", "building_cov": "Building coverage",
    "road_frac": "Road share", "far_cell": "Floor-area ratio", "floors_mean": "Mean floors",
    "yearbuilt_med": "Median year built", "lu_res": "Residential land share", "lu_comm": "Commercial land share",
    "lu_ind": "Industrial land share", "lu_open": "Open-space land share", "canopy": "Tree canopy share",
    "grass": "Grass/shrub share", "green": "Green share", "cb_density": "Catch basins per km²",
    "cb_per_road_ha": "Catch basins per road ha", "cb_nn_dist_m": "Mean distance to catch basin (m)",
    "ms4_frac": "MS4 (separate sewer) share", "gi_density": "Green infra. per km²", "pop": "Population",
    "rpl_themes": "Social vulnerability (SVI)", "minority_rate": "Minority share", "poverty_rate": "Poverty (<150%) share",
    "noveh_rate": "No-vehicle households",
}
RAIN_BINS = [0, 3, 6, 12, 20, np.inf]
RAIN_LABELS = ["<3", "3–6", "6–12", "12–20", "≥20"]


def style():
    plt.rcParams.update({
        "font.family": "Helvetica", "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7,
        "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5, "axes.linewidth": 0.6,
        "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
        "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False, "grid.color": GRID,
        "grid.linewidth": 0.5, "legend.frameon": False, "figure.dpi": 150, "savefig.dpi": 300,
        "lines.linewidth": 1.4, "pdf.fonttype": 42, "svg.fonttype": "none", "axes.titleweight": "bold",
        "axes.titlelocation": "left",
    })


def panel(ax, letter, title=None, x=-0.02, y=1.04):
    ax.text(x, y, letter, transform=ax.transAxes, fontsize=9, fontweight="bold", va="bottom", ha="right")
    if title:
        ax.set_title(title, pad=4)


def save(fig, name):
    for ext in ("png", "pdf", "svg"):
        fig.savefig(FIG / f"{name}.{ext}", bbox_inches="tight", dpi=300 if ext == "png" else None)
    plt.close(fig)
    print("saved", name)


def write_stats(name, d):
    (TAB / f"{name}_stats.json").write_text(json.dumps(d, indent=2, default=lambda o: float(o) if np.isscalar(o) else str(o)))


# ----------------------------------------------------------------- loaders --
def grid():
    return gpd.read_file(PROC / "grid.gpkg")


def static():
    return pd.read_parquet(PROC / "static.parquet")


def boroughs():
    b = gpd.read_file(RAW / "boundaries/boroughs.geojson").to_crs("EPSG:26918")
    return b


def storms():
    s = pd.read_parquet(PROC / "storms.parquet")
    s["rain_class"] = pd.cut(s.max1h_mm, RAIN_BINS, labels=RAIN_LABELS, right=False)
    return s


def reports(kind="street_flooding"):
    r = pd.read_parquet(PROC / "reports.parquet")
    r = r[r.in_grid]
    return r if kind is None else r[r.kind == kind]


def panel_df():
    return pd.read_parquet(PROC / "panel_storm_cell.parquet")


def cell_table():
    """Grid geometry + static features + whole-period storm-report summary."""
    g = grid().merge(static(), on="cell_id", how="left")
    pan = panel_df(); s = storms()
    n = len(s)
    agg = pan.groupby("cell_id").agg(storm_reports=("n_reports", "sum"),
                                     storms_hit=("n_reports", lambda v: (v > 0).sum()))
    g = g.merge(agg, on="cell_id", how="left")
    g["p_storm"] = g.storms_hit / n                     # P(>=1 report | storm)
    g["rate_km2"] = g.storm_reports / g.land_km2 / n * 100   # reports per km² per 100 storms
    r = reports()
    g["all_reports"] = g.cell_id.map(r.cell_id.value_counts()).fillna(0)
    return g


def basemap(ax, b=None, fc="#f3f2ef", ec="#b9b8b2", lw=0.35):
    b = boroughs() if b is None else b
    b.plot(ax=ax, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=0)
    ax.set_axis_off(); ax.set_aspect("equal")


def scalebar(ax, x0, y0, km=5):
    ax.plot([x0, x0 + km * 1000], [y0, y0], color=INK, lw=1.2, solid_capstyle="butt")
    ax.text(x0 + km * 500, y0 + 500, f"{km} km", ha="center", va="bottom", fontsize=6, color=INK)


def binned_rate(df, x, y, bins, w=None):
    """Mean of y within bins of x with Wilson/normal 95% CI (y binary or count)."""
    d = df[[x, y]].dropna().copy()
    d["b"] = pd.cut(d[x], bins, include_lowest=True)
    g = d.groupby("b", observed=True)[y].agg(["mean", "count", "std"])
    g["lo"] = g["mean"] - 1.96 * g["std"] / np.sqrt(g["count"])
    g["hi"] = g["mean"] + 1.96 * g["std"] / np.sqrt(g["count"])
    g["mid"] = d.groupby("b", observed=True)[x].median()
    return g.reset_index()


def cluster_boot(df, stat, cluster, n=300, seed=0):
    """Cluster bootstrap CI of stat(df) resampling whole clusters."""
    rng = np.random.default_rng(seed)
    ids = df[cluster].unique()
    groups = {k: v for k, v in df.groupby(cluster)}
    vals = []
    for _ in range(n):
        pick = rng.choice(ids, len(ids), replace=True)
        vals.append(stat(pd.concat([groups[k] for k in pick])))
    return np.nanpercentile(vals, [2.5, 97.5])
