"""Fig. 2 - Spatial clustering, recurring hotspots and their characteristics (311 x FloodNet x terrain x drainage)."""
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy import stats
from libpysal.weights import DistanceBand
from esda.getisord import G_Local
from esda.moran import Moran
from statsmodels.stats.multitest import multipletests
from .common import *  # noqa

style()
g = cell_table().reset_index(drop=True)
cent = np.c_[g.geometry.centroid.x, g.geometry.centroid.y]
w = DistanceBand(cent, threshold=750, binary=True, silence_warnings=True)   # 8-neighbour (queen) on 500 m grid
w.transform = "B"

# storm-period report rate per km² per 100 storms
y = g.rate_km2.fillna(0).values
gi = G_Local(y, w, transform="B", star=True, permutations=999, seed=1)
q = multipletests(gi.p_sim, method="fdr_bh")[1]
g["gi_z"] = gi.Zs
g["gi_class"] = np.select([(q < 0.05) & (gi.Zs > 0), (q < 0.05) & (gi.Zs < 0)], ["Hot", "Cold"], "n.s.")
g["gi_class"] = np.where((g.gi_class == "n.s.") & (gi.p_sim < 0.05) & (gi.Zs > 0), "Hot (unadj.)", g.gi_class)

# annual top-decile recurrence
r = reports()
r["year"] = r.t.dt.tz_convert("America/New_York").dt.year
yr = r[r.year.between(2010, 2025)].groupby(["cell_id", "year"]).size().unstack(fill_value=0)
yr = yr.reindex(g.cell_id).fillna(0)
dens = yr.div(g.set_index("cell_id").land_km2, axis=0)
top = dens.ge(dens.quantile(0.9, axis=0), axis=1) & (yr > 0)
g["years_top10"] = top.sum(1).values
g["persistent"] = g.years_top10 >= 8

# annual Moran's I
mor = []
cb = reports("catch_basin"); cb["year"] = cb.t.dt.tz_convert("America/New_York").dt.year
cby = cb[cb.year.between(2010, 2025)].groupby(["cell_id", "year"]).size().unstack(fill_value=0).reindex(g.cell_id).fillna(0)
wr = DistanceBand(cent, threshold=750, binary=True, silence_warnings=True); wr.transform = "R"
for yv in range(2010, 2026):
    m1 = Moran(dens[yv].values, wr, permutations=199)
    m2 = Moran((cby[yv] / g.set_index("cell_id").land_km2).values, wr, permutations=199)
    mor.append((yv, m1.I, m1.p_sim, m2.I))
mor = pd.DataFrame(mor, columns=["year", "I_sf", "p_sf", "I_cb"])

# FloodNet validation: events per sensor-year by Gi* class
sens = pd.read_parquet(PROC / "floodnet_sensors.parquet")
ev = pd.read_parquet(PROC / "floodnet_events.parquet")
sens["inst"] = pd.to_datetime(sens.date_installed, errors="coerce", utc=True)
sens["rem"] = pd.to_datetime(sens.date_removed, errors="coerce", utc=True).fillna(pd.Timestamp("2026-11-09", tz="UTC"))
sens["yrs"] = ((sens.rem - sens.inst).dt.days / 365.25).clip(lower=0)
sens = sens[(sens.yrs >= 0.5) & (sens.tidally_influenced != "Yes")]
sens["n_ev"] = sens.sensor_id.map(ev.groupby("sensor_id").size()).fillna(0)
sens["ev_rate"] = sens.n_ev / sens.yrs
sens = sens.merge(g[["cell_id", "gi_class", "persistent", "years_top10"]], on="cell_id", how="left")
sens["grp"] = np.where(sens.gi_class.str.startswith("Hot"), "311 hotspot", "Other")

fig = plt.figure(figsize=(7.2, 6.6))
gs = fig.add_gridspec(2, 3, height_ratios=[1.3, 1], hspace=0.12, wspace=0.95, width_ratios=[1, 1.15, 0.9])
cols = {"Hot": "#a8360c", "Hot (unadj.)": "#f5b48f", "Cold": C[0], "n.s.": "#ecebe7"}
ax = fig.add_subplot(gs[0, :2]) if False else fig.add_subplot(gs[0, 0:2])
# two maps side by side inside the top row
ax.remove()
sub = gs[0, :].subgridspec(1, 2, wspace=0.02)
ax = fig.add_subplot(sub[0]); basemap(ax)
for k, c in cols.items():
    g[g.gi_class == k].plot(ax=ax, color=c, linewidth=0, zorder=1)
ax.legend(handles=[Patch(color=c, label=f"{k} (n={int((g.gi_class == k).sum())})") for k, c in cols.items()],
          loc="upper left", fontsize=6)
ax.set_xlim(560000, 612000); ax.set_ylim(4482000, 4532000); scalebar(ax, 565000, 4485000)
panel(ax, "a", "Getis–Ord Gi* of storm-period report rate (FDR 5%)", x=0.02, y=0.98)

ax = fig.add_subplot(sub[1]); basemap(ax)
cmap = plt.get_cmap(SEQ_HOT, 5)
g2 = g[g.years_top10 > 0]
g2.plot(ax=ax, column="years_top10", cmap=SEQ_HOT, vmin=1, vmax=16, linewidth=0, zorder=1)
g[g.persistent].boundary.plot(ax=ax, color=INK, linewidth=0.5, zorder=2)
sm = plt.cm.ScalarMappable(cmap=SEQ_HOT, norm=plt.Normalize(1, 16))
cax = ax.inset_axes([0.04, 0.88, 0.32, 0.025]); cbr = fig.colorbar(sm, cax=cax, orientation="horizontal")
cbr.set_label("Years in annual top 10% (2010–2025)", fontsize=6); cax.xaxis.set_label_position("top"); cbr.ax.tick_params(labelsize=5.5)
ax.text(0.04, 0.80, f"outlined: persistent (≥8 yr), n={int(g.persistent.sum())}", transform=ax.transAxes, fontsize=6, color=INK)
ax.set_xlim(560000, 612000); ax.set_ylim(4482000, 4532000)
panel(ax, "b", "Recurring hotspots", x=0.02, y=0.98)

# (c) Moran's I by year
ax = fig.add_subplot(gs[1, 0])
ax.plot(mor.year, mor.I_sf, color=C[0], marker="o", ms=3, label="Street flooding")
ax.plot(mor.year, mor.I_cb, color=C[1], marker="s", ms=3, label="Catch basin clogged")
ax.axhline(0, color=MUTED, lw=0.6)
ax.set_ylabel("Global Moran's I (density)"); ax.set_xticks(range(2010, 2026, 5))
ax.legend(loc="lower left", fontsize=6); ax.set_ylim(0, None)
panel(ax, "c", "Clustering over time" + (" (all p<0.01)" if (mor.p_sf < 0.01).all() else ""))

# (d) standardized mean differences, persistent vs other land cells
ax = fig.add_subplot(gs[1, 1])
feats = ["elev_p10", "tpi_p10", "dep_frac", "dist_shore_m", "slope_mean", "impervious", "building_cov", "far_cell",
         "canopy", "cb_per_road_ha", "ms4_frac", "pop", "rpl_themes"]
rows = []
rng = np.random.default_rng(0)
for f_ in feats:
    a_ = g.loc[g.persistent, f_].dropna().values; b_ = g.loc[~g.persistent & (g.land_frac > 0.5), f_].dropna().values
    sd = np.sqrt((a_.var() + b_.var()) / 2)
    d = (a_.mean() - b_.mean()) / sd
    bs = [(rng.choice(a_, len(a_)).mean() - rng.choice(b_, len(b_)).mean()) / sd for _ in range(1000)]
    p = stats.mannwhitneyu(a_, b_).pvalue
    rows.append((f_, d, *np.percentile(bs, [2.5, 97.5]), p))
smd = pd.DataFrame(rows, columns=["feat", "d", "lo", "hi", "p"]).sort_values("d")
grp_of = {v: k for k, vs in GROUPS.items() for v in vs}
for i, rr in enumerate(smd.itertuples()):
    col = GROUP_COLOR[grp_of[rr.feat]]
    ax.plot([rr.lo, rr.hi], [i, i], color=col, lw=1.2)
    ax.plot(rr.d, i, "o", color=col, ms=4)
ax.axvline(0, color=MUTED, lw=0.6)
ax.set_yticks(range(len(smd))); ax.set_yticklabels([LABEL[f_] for f_ in smd.feat], fontsize=5.8)
ax.set_xlabel("Standardised difference (Cohen's d)")
for k in ["Topography", "Built form", "Greenness", "Drainage", "Population / reporting"]:
    ax.plot([], [], "o", color=GROUP_COLOR[k], label=k, ms=3)
ax.legend(fontsize=5.3, loc="upper left", handletextpad=0.2)
panel(ax, "d", "Persistent hotspots vs other cells")

# (e) FloodNet event rate by 311 hotspot status
ax = fig.add_subplot(gs[1, 2])
data = [sens.loc[sens.grp == k, "ev_rate"].values for k in ["311 hotspot", "Other"]]
parts = ax.violinplot(data, positions=[0, 1], showextrema=False, widths=0.7)
for b_, c in zip(parts["bodies"], [C[1], C[0]]):
    b_.set_facecolor(c); b_.set_alpha(0.35); b_.set_edgecolor("none")
for i, d in enumerate(data):
    ax.scatter(np.full(len(d), i) + rng.uniform(-0.12, 0.12, len(d)), d, s=3, color=[C[1], C[0]][i], alpha=0.6, linewidth=0)
    ax.plot([i - 0.2, i + 0.2], [np.median(d)] * 2, color=INK, lw=1.4)
mw = stats.mannwhitneyu(*data, alternative="greater")
ax.set_xticks([0, 1]); ax.set_xticklabels([f"311 hotspot\nn={len(data[0])}\nmed {np.median(data[0]):.1f}", f"Elsewhere\nn={len(data[1])}\nmed {np.median(data[1]):.1f}"], fontsize=5.8)
ax.set_yscale("symlog", linthresh=1); ax.set_ylim(0, 60); ax.set_ylabel("FloodNet events per sensor-year")
ax.text(0.5, 0.97, f"Mann–Whitney p = {mw.pvalue:.2g}", transform=ax.transAxes, ha="center", va="top", fontsize=6)
panel(ax, "e", "Sensor validation")

save(fig, "fig02_hotspots")
g.drop(columns="geometry")[["cell_id", "boro", "rate_km2", "gi_z", "gi_class", "years_top10", "persistent"]].to_csv(TAB / "fig02_cell_hotspots.csv", index=False)
mor.to_csv(TAB / "fig02_moran_by_year.csv", index=False)
smd.to_csv(TAB / "fig02_smd.csv", index=False)
write_stats("fig02", {"gi_counts": g.gi_class.value_counts().to_dict(), "persistent_cells": int(g.persistent.sum()),
                      "persistent_share_of_storm_reports": float(g.loc[g.persistent, "storm_reports"].sum() / g.storm_reports.sum()),
                      "persistent_share_of_area": float(g.loc[g.persistent, "land_km2"].sum() / g.land_km2.sum()),
                      "hot_share_of_storm_reports": float(g.loc[g.gi_class == "Hot", "storm_reports"].sum() / g.storm_reports.sum()),
                      "hot_share_of_area": float(g.loc[g.gi_class == "Hot", "land_km2"].sum() / g.land_km2.sum()),
                      "moran_mean_sf": mor.I_sf.mean(), "moran_mean_cb": mor.I_cb.mean(),
                      "floodnet_rate_median": {"hot": float(np.median(data[0])), "other": float(np.median(data[1]))},
                      "floodnet_mw_p": mw.pvalue, "hot_by_boro": g[g.gi_class == "Hot"].boro.value_counts().to_dict()})
