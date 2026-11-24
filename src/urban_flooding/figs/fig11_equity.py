"""Fig. 11 - Hazard x exposure x vulnerability x infrastructure (311 hazard, model hazard, DEP stormwater map,
CDC SVI, population, catch basins, green infrastructure, hospitals/schools/subway). J19-J21, J24, RQ49-53."""
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from .common import *  # noqa
from .strat import agg_table

style()
g = cell_table()
a = agg_table()
heavy = a[a.rain_class.isin(["6–12", "12–20", "≥20"])].groupby("cell_id").agg(h=("hits", "sum"), n=("n", "sum"))
# empirical-Bayes (beta-binomial) shrinkage of the heavy-storm hit rate
p0 = heavy.h.sum() / heavy.n.sum(); k = 30
heavy["p_eb"] = (heavy.h + k * p0) / (heavy.n + k)
g = g.merge(heavy[["p_eb"]], on="cell_id", how="left")
dz = pd.read_csv(TAB / "fig10_design_storm_hazard.csv").rename(columns={"p": "p_model"})
g = g.merge(dz, on="cell_id", how="left")
g["swm"] = g.swm_extreme_deep + g.swm_extreme_nuisance
g = g[g.p_eb.notna() & g.p_model.notna() & g.rpl_themes.notna()].copy()   # urban street cells with SVI
for c in ["p_eb", "p_model", "swm", "rpl_themes", "pop", "cb_per_road_ha"]:
    g[c + "_pct"] = g[c].rank(pct=True)
g["hazard"] = g[["p_eb_pct", "p_model_pct", "swm_pct"]].mean(1)
g["hazard_pct"] = g.hazard.rank(pct=True)
g["hz3"] = pd.qcut(g.hazard_pct, 3, labels=[0, 1, 2]).astype(int)
g["sv3"] = pd.qcut(g.rpl_themes.rank(method="first"), 3, labels=[0, 1, 2]).astype(int)
# NTA names (largest-overlap tract)
tr = gpd.read_file(PROC / "tracts.gpkg")[["ntaname", "geometry"]]
ov = gpd.overlay(g[["cell_id", "geometry"]], tr, how="intersection", keep_geom_type=True)
ov["a"] = ov.area; g["nta"] = g.cell_id.map(ov.sort_values("a").groupby("cell_id").ntaname.last())

# bivariate palette (hazard: orange axis, vulnerability: blue axis) - 3x3
BIV = np.array([["#e8e8e8", "#b5c0da", "#6c83b5"],
                ["#e9c9a8", "#b4a9a6", "#6b7697"],
                ["#e3955d", "#ad7f62", "#61536d"]])   # rows: hazard 0..2, cols: SVI 0..2

fig = plt.figure(figsize=(7.2, 7.6))
gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.5, height_ratios=[1.25, 1])

# (a) bivariate map
ax = fig.add_subplot(gs[0, :2]); basemap(ax)
g["biv"] = [BIV[h, v] for h, v in zip(g.hz3, g.sv3)]
g.plot(ax=ax, color=g.biv, linewidth=0, zorder=1)
ax.set_xlim(560000, 612000); ax.set_ylim(4482000, 4532000); scalebar(ax, 565000, 4485000)
lg = ax.inset_axes([0.04, 0.62, 0.17, 0.2])
for h in range(3):
    for v in range(3):
        lg.add_patch(Rectangle((v, h), 1, 1, color=BIV[h, v]))
lg.set_xlim(0, 3); lg.set_ylim(0, 3); lg.set_xticks([]); lg.set_yticks([])
lg.set_xlabel("Social vuln. (low to high)", fontsize=5.5, labelpad=1); lg.set_ylabel("Hazard (low to high)", fontsize=5.5, labelpad=1)
for sp_ in lg.spines.values(): sp_.set_visible(False)
both = g[(g.hz3 == 2) & (g.sv3 == 2)]
ax.text(0.04, 0.55, f"High–high cells: {len(both)}\n{both['pop'].sum() / 1e6:.2f} M residents", transform=ax.transAxes, fontsize=5.8, va="top")
panel(ax, "a", "Hazard × social vulnerability (J19)", x=0.02, y=0.93)

# (b) robustness: mean hazard percentile by SVI decile for each hazard measure
ax = fig.add_subplot(gs[0, 2])
g["svd"] = pd.qcut(g.rpl_themes.rank(method="first"), 10, labels=False) + 1
for col, c_, lab in [("p_eb_pct", C[1], "311 heavy-storm rate"), ("p_model_pct", INK, "Model, design storm"), ("swm_pct", C[0], "DEP stormwater map")]:
    t = g.groupby("svd")[col].agg(["mean", "std", "count"])
    se = t["std"] / np.sqrt(t["count"])
    ax.errorbar(t.index, t["mean"] * 100, yerr=1.96 * se * 100, fmt="-o", ms=2.5, lw=1.2, capsize=0, color=c_, label=lab)
ax.axhline(50, color=MUTED, lw=0.6, ls="--")
ax.set_xlabel("SVI decile (1 = least vulnerable)"); ax.set_ylabel("Mean hazard percentile"); ax.set_xticks(range(1, 11))
ax.legend(fontsize=5.3, loc="upper left")
panel(ax, "b", "Hazard by vulnerability")

# (c) population exposure by hazard tercile and SVI tercile
ax = fig.add_subplot(gs[1, 0])
popt = g.groupby(["hz3", "sv3"])["pop"].sum().unstack() / 1e6
bottom = np.zeros(3)
for v in range(3):
    ax.bar(range(3), popt[v], bottom=bottom, color=BIV[2, v], width=0.65, label=["Low SVI", "Mid SVI", "High SVI"][v], edgecolor="white", linewidth=0.6)
    bottom += popt[v].values
ax.set_xticks(range(3)); ax.set_xticklabels(["Low", "Mid", "High"]); ax.set_xlabel("Flood-hazard tercile")
ax.set_ylabel("Residents (millions)"); ax.legend(fontsize=5.4, loc="upper left")
panel(ax, "c", "Population exposure")

# (d) J21 green infrastructure vs need
ax = fig.add_subplot(gs[1, 1])
gi = g.groupby(["hz3", "sv3"]).apply(lambda d: d.gi_count.sum() / d.land_km2.sum()).unstack()
w = 0.26
for v in range(3):
    ax.bar(np.arange(3) + (v - 1) * w, gi[v], width=w - 0.02, color=BIV[2, v], label=["Low SVI", "Mid SVI", "High SVI"][v])
ax.set_xticks(range(3)); ax.set_xticklabels(["Low", "Mid", "High"]); ax.set_xlabel("Flood-hazard tercile")
ax.set_ylabel("Green-infrastructure assets per km²"); ax.legend(fontsize=5.4, loc="upper left")
panel(ax, "d", "Green infra. vs need (J21)")

# (e) J24 critical infrastructure in the top hazard decile
ax = fig.add_subplot(gs[1, 2])
top = g.hazard_pct >= 0.9
items = [("Land area", "land_km2"), ("Population", "pop"), ("Hospitals", "n_hospitals"), ("Schools", "n_schools"),
         ("Subway stations\n(underground)", "n_subway_ug")]
sh = [(lab, g.loc[top, c].sum() / g[c].sum() * 100, int(g.loc[top, c].sum())) for lab, c in items]
ax.barh(range(len(sh))[::-1], [x[1] for x in sh], color=[MUTED, MUTED, C[7], C[3], C[6]], height=0.6)
for yy, (lab, v, n) in zip(range(len(sh))[::-1], sh):
    ax.text(v + 0.3, yy, f"{v:.1f}% (n={n:,})" if lab not in ("Land area", "Population") else f"{v:.1f}%", va="center", fontsize=5.6)
ax.axvline(10, color=INK2, lw=0.6, ls=":")
ax.set_yticks(range(len(sh))[::-1]); ax.set_yticklabels([x[0] for x in sh], fontsize=6)
ax.set_xlabel("% located in top-decile hazard cells"); ax.set_xlim(0, max(x[1] for x in sh) * 1.45)
panel(ax, "e", "Critical facilities (J24)")

save(fig, "fig11_equity")

# priority table (J20 / RQ53): hazard x population x vulnerability x basin gap
g["priority"] = g.hazard_pct * g.pop_pct * g.rpl_themes_pct.fillna(0.5) * (1 - g.cb_per_road_ha_pct.fillna(0.5) * 0.5)
pr = g.sort_values("priority", ascending=False).head(40)
pr[["cell_id", "boro", "nta", "hazard_pct", "p_eb", "p_model", "swm", "pop", "rpl_themes", "cb_per_road_ha", "gi_count",
    "n_schools", "n_subway_ug", "priority"]].to_csv(TAB / "fig11_priority_cells.csv", index=False)
g.drop(columns="geometry")[["cell_id", "boro", "nta", "hazard", "hazard_pct", "hz3", "sv3", "pop", "rpl_themes"]].to_csv(TAB / "fig11_cell_hazard.csv", index=False)
write_stats("fig11", {"cells": len(g), "high_high_cells": len(both), "high_high_pop": float(both["pop"].sum()),
                      "pop_by_hazard_svi_M": popt.round(3).to_dict(),
                      "corr_hazard_svi": float(np.corrcoef(g.hazard_pct, g.rpl_themes.fillna(g.rpl_themes.median()))[0, 1]),
                      "corr_measures": g[["p_eb_pct", "p_model_pct", "swm_pct"]].corr(method="spearman").round(3).to_dict(),
                      "gi_density": gi.round(2).to_dict(), "critical_top_decile_pct": {x[0]: [x[1], x[2]] for x in sh},
                      "top_priority_nta": pr.nta.value_counts().head(12).to_dict()})
