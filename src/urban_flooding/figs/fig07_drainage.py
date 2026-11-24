"""Fig. 7 - Drainage infrastructure x rainfall (catch basins, MS4 areas, green infrastructure, 311, land cover).
J02, J08, J12, J13, J14; RQ29-31, coverage gaps."""
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio
from pyproj import Transformer
from scipy import stats
from scipy.spatial import cKDTree
from matplotlib.patches import Patch
from .common import *  # noqa
from .strat import agg_table, groups, strata, interaction_test, draw_curves, draw_ratio

style()
a = agg_table().copy()
cells = a.drop_duplicates("cell_id").set_index("cell_id")
a["cb_g"] = a.cell_id.map(groups(cells.cb_per_road_ha, 3, ["Sparse basins", "Middle", "Dense basins"]))
a["ms4_g"] = a.cell_id.map(pd.cut(cells.ms4_frac, [-0.01, 0.05, 0.5, 1.01], labels=["Non-MS4 (<5%)", "Mixed", "MS4 (>50%)"]))
tests = [interaction_test(a, "cb_per_road_ha"), interaction_test(a, "ms4_frac"), interaction_test(a, "gi_density", log=True)]

fig = plt.figure(figsize=(7.2, 7.0))
gs = fig.add_gridspec(2, 3, hspace=0.42, wspace=0.62)
bot = gs[1, :].subgridspec(1, 3, wspace=1.05, width_ratios=[0.85, 1, 1])

# (a) J02 catch-basin density
sub = gs[0, 0].subgridspec(2, 1, height_ratios=[2.2, 1], hspace=0.12)
ax = fig.add_subplot(sub[0]); out_cb, rat_cb = strata(a, "cb_g")
draw_curves(ax, out_cb, [C[3], MUTED, C[6]]); ax.set_xlabel(""); ax.set_xticklabels([]); ax.legend(fontsize=5.5, loc="upper left")
ax.text(0.98, 0.04, f"interaction p = {tests[0]['p_interaction']:.2g}", transform=ax.transAxes, ha="right", fontsize=5.5, color=INK2)
panel(ax, "a", "Rainfall × catch-basin density (J02)")
ax2 = fig.add_subplot(sub[1]); draw_ratio(ax2, rat_cb, C[6], "Dense / Sparse"); ax2.set_xlabel("Storm peak 1-h rain (mm h⁻¹)")

# (b) J08 drainage regime
sub = gs[0, 1].subgridspec(2, 1, height_ratios=[2.2, 1], hspace=0.12)
ax = fig.add_subplot(sub[0]); out_ms, rat_ms = strata(a, "ms4_g")
draw_curves(ax, out_ms, [C[1], MUTED, C[0]]); ax.set_xlabel(""); ax.set_xticklabels([]); ax.legend(fontsize=5.5, loc="upper left")
ax.text(0.98, 0.04, f"interaction p = {tests[1]['p_interaction']:.2g}", transform=ax.transAxes, ha="right", fontsize=5.5, color=INK2)
panel(ax, "b", "Rainfall × drainage regime (J08)")
ax2 = fig.add_subplot(sub[1]); draw_ratio(ax2, rat_ms, C[0], "MS4 / Non-MS4"); ax2.set_xlabel("Storm peak 1-h rain (mm h⁻¹)")

# (c) J13 imperviousness effect by drainage regime
ax = fig.add_subplot(bot[0])
rows = []
for reg in ["Non-MS4 (<5%)", "MS4 (>50%)"]:
    d = a[a.ms4_g == reg].copy()
    dc = d.drop_duplicates("cell_id").set_index("cell_id")
    d["ig"] = d.cell_id.map(groups(dc.impervious, 3))
    o, rt = strata(d, "ig", n_boot=300)
    rows.append(rt.assign(regime=reg))
j13 = pd.concat(rows)
for k, (reg, d) in enumerate(j13.groupby("regime", sort=False)):
    xs = np.arange(len(d)) + (k - 0.5) * 0.18
    ax.errorbar(xs, d.ratio, yerr=[d.ratio - d.lo, d.hi - d.ratio], fmt="o", ms=3, lw=1, capsize=0, color=[C[1], C[0]][k], label=reg)
ax.axhline(1, color=MUTED, lw=0.6); ax.set_xticks(range(5)); ax.set_xticklabels(RAIN_LABELS, fontsize=5.6)
ax.set_ylabel("High / Low impervious tercile"); ax.set_xlabel("Peak 1-h rain (mm h⁻¹)"); ax.legend(fontsize=5.2, loc="upper right")
panel(ax, "c", "Imperv. × regime (J13)")

# (d) J12 + J14: 2x2 tables, storms >= 6 mm/h
heavy = a[a.rain_class.isin(["6–12", "12–20", "≥20"])]
hc = heavy.groupby("cell_id").agg(h=("hits", "sum"), n=("n", "sum")).join(cells[["building_cov", "cb_per_road_ha", "gi_density"]])
hc["dense_b"] = hc.building_cov >= hc.building_cov.quantile(2 / 3)
hc["cb_hi"] = hc.cb_per_road_ha >= hc.cb_per_road_ha.median()
hc["gi"] = hc.gi_density > 0
ax = fig.add_subplot(bot[1])
rng = np.random.default_rng(0)
def pci(d):
    p = d.h.sum() / d.n.sum()
    bs = [d.iloc[i].h.sum() / d.iloc[i].n.sum() for i in (rng.integers(0, len(d), len(d)) for _ in range(400))]
    return p * 100, *np.percentile(bs, [2.5, 97.5]) * 100, len(d)
tab = []
for lab, m in [("Dense bldg", hc.dense_b), ("Other bldg", ~hc.dense_b)]:
    for cb_, cl in [(False, "Sparse CB"), (True, "Dense CB")]:
        tab.append((lab, cl, *pci(hc[m & (hc.cb_hi == cb_)])))
for lab, m in [("With GI", hc.gi), ("No GI", ~hc.gi)]:
    for cb_, cl in [(False, "Sparse CB"), (True, "Dense CB")]:
        tab.append((lab, cl, *pci(hc[m & (hc.cb_hi == cb_)])))
tab = pd.DataFrame(tab, columns=["grp", "cb", "p", "lo", "hi", "n"])
ylab = []
for i, rr in enumerate(tab.itertuples()):
    col = C[6] if rr.cb == "Dense CB" else C[3]
    ax.errorbar(rr.p, i, xerr=[[rr.p - rr.lo], [rr.hi - rr.p]], fmt="o", ms=3.5, color=col, lw=1, capsize=0)
    ylab.append(f"{rr.grp}, {rr.cb.split()[0].lower()} CB ({rr.n})")
ax.axhline(3.5, color=GRID, lw=0.8)
ax.set_yticks(range(len(tab))); ax.set_yticklabels(ylab, fontsize=5.2); ax.invert_yaxis()
ax.set_xlabel("P(report | storm ≥6), %")
ax.text(1.0, 0.25, "J14", transform=ax.transAxes, fontsize=6, ha="right", color=INK2)
ax.text(1.0, 0.75, "J12", transform=ax.transAxes, fontsize=6, ha="right", color=INK2)
panel(ax, "d", "Density, GI and basins")

# (e) distance from reports to nearest catch basin vs random street points
ax = fig.add_subplot(bot[2])
cb = pd.read_parquet(RAW / "catch_basins/catch_basins.parquet")
from ..build import to_points
cbp = to_points(cb); tree = cKDTree(np.c_[cbp.x, cbp.y])
r = reports(); r = r[r.t >= "2015-01-01"]
d_rep = tree.query(np.c_[r.x, r.y])[0]
with rasterio.open(RAW / "land_cover/landcover2017_8ft.tif") as ds:
    arr = ds.read(1, out_shape=(ds.height // 4, ds.width // 4))
    tr = ds.transform * ds.transform.scale(ds.width / arr.shape[1], ds.height / arr.shape[0])
    iy, ix = np.nonzero(arr == 6)
    pick = rng.choice(len(iy), 40000, replace=False)
    xs_, ys_ = rasterio.transform.xy(tr, iy[pick], ix[pick])
    t = Transformer.from_crs(ds.crs, "EPSG:26918", always_xy=True)
    rx, ry = t.transform(np.array(xs_), np.array(ys_))
d_road = tree.query(np.c_[rx, ry])[0]
for dv, col, lab in [(d_rep, C[1], f"311 street-flooding reports (n={len(d_rep):,})"), (d_road, MUTED, "Random road points (n=40,000)")]:
    v = np.sort(np.clip(dv, 0, 300)); ax.plot(v, np.arange(1, len(v) + 1) / len(v) * 100, color=col, lw=1.5, label=lab)
ks = stats.ks_2samp(d_rep, d_road)
ax.set_xlabel("Distance to nearest catch basin (m)"); ax.set_ylabel("Cumulative %"); ax.set_xlim(0, 150)
ax.legend(fontsize=5.2, loc="lower right", bbox_to_anchor=(1.02, 0.12))
ax.text(0.35, 0.5, f"median {np.median(d_rep):.0f} vs {np.median(d_road):.0f} m\nKS D = {ks.statistic:.2f}", transform=ax.transAxes, va="top", fontsize=5.6)
panel(ax, "e", "Report–basin distance")

# (f) coverage-gap map
ax = fig.add_subplot(gs[0, 2]); basemap(ax)
g = cell_table().merge(pd.read_csv(TAB / "fig02_cell_hotspots.csv")[["cell_id", "persistent", "gi_class"]], on="cell_id")
hotc = g.persistent | g.gi_class.eq("Hot")
med = g.loc[g.road_frac >= 0.08, "cb_per_road_ha"].median()
gap = hotc & (g.cb_per_road_ha < med)
g[hotc & ~gap].plot(ax=ax, color="#f5b48f", linewidth=0, zorder=1)
g[gap].plot(ax=ax, color=C[7], linewidth=0, zorder=2)
gi = pd.read_parquet(RAW / "green_infra/gi_points.parquet"); gip = to_points(gi)
ax.scatter(gip.x, gip.y, s=0.15, color=C[2], alpha=0.35, linewidth=0, zorder=1.5)
ax.set_xlim(560000, 612000); ax.set_ylim(4482000, 4532000)
ax.legend(handles=[Patch(color=C[7], label=f"Hotspot, sparse basins (n={int(gap.sum())})"),
                   Patch(color="#f5b48f", label=f"Hotspot, ≥median basins (n={int((hotc & ~gap).sum())})"),
                   Patch(color=C[2], label="Green infrastructure asset")], loc="lower left", fontsize=5, bbox_to_anchor=(-0.05, -0.32))
panel(ax, "f", "Hotspots with sparse catch basins", x=0.0, y=0.9)

save(fig, "fig07_drainage")
tab.to_csv(TAB / "fig07_j12_j14.csv", index=False); j13.to_csv(TAB / "fig07_j13.csv", index=False)
g.loc[gap, ["cell_id", "boro", "rate_km2", "cb_per_road_ha", "impervious", "elev_p10", "pop", "rpl_themes"]].to_csv(TAB / "fig07_coverage_gap_cells.csv", index=False)
write_stats("fig07", {"tests": tests, "cb_ratio": rat_cb.to_dict("records"), "ms4_ratio": rat_ms.to_dict("records"),
                      "j13": j13.to_dict("records"), "j12_j14": tab.to_dict("records"),
                      "dist_median_report_m": float(np.median(d_rep)), "dist_median_road_m": float(np.median(d_road)),
                      "ks": [ks.statistic, ks.pvalue], "gap_cells": int(gap.sum()), "gap_by_boro": g[gap].boro.value_counts().to_dict()})
