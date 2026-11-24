"""Fig. 5 - Topography x rainfall x drainage (3DEP DEM, 311 storm panel, catch basins, land cover).
J01, J09, J11, J17; RQ16-17."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from matplotlib.patches import Patch
from .common import *  # noqa
from .strat import agg_table, groups, strata, interaction_test, draw_curves, draw_ratio

style()
a = agg_table().copy()
cells = a.drop_duplicates("cell_id").set_index("cell_id")
a["elev_g"] = a.cell_id.map(groups(cells.elev_p10, 3, ["Low-lying", "Middle", "High ground"]))
a["dep_g"] = a.cell_id.map(groups(cells.dep_frac, 3, ["Few depressions", "Middle", "Many depressions"]))
tests = [interaction_test(a, "elev_p10", log=True), interaction_test(a, "dep_frac"), interaction_test(a, "tpi_p10"),
         interaction_test(a, "slope_mean", log=True)]

fig = plt.figure(figsize=(7.2, 6.9))
gs = fig.add_gridspec(2, 3, hspace=0.5, wspace=0.5, height_ratios=[1, 1])

# (a) map: depression share + persistent hotspots
g = cell_table()
hot = pd.read_csv(TAB / "fig02_cell_hotspots.csv")
g = g.merge(hot[["cell_id", "persistent"]], on="cell_id")
ax = fig.add_subplot(gs[0, 0]); basemap(ax)
g.plot(ax=ax, column="elev_p10", cmap="Blues_r", vmin=0, vmax=40, linewidth=0, zorder=1)
g[g.persistent].boundary.plot(ax=ax, color=C[1], linewidth=0.7, zorder=2)
sm_ = plt.cm.ScalarMappable(cmap="Blues_r", norm=plt.Normalize(0, 40))
cax = ax.inset_axes([0.03, 0.9, 0.42, 0.03]); cb = fig.colorbar(sm_, cax=cax, orientation="horizontal")
cb.set_label("Cell 10th-pct elevation (m)", fontsize=5.5); cax.xaxis.set_label_position("top"); cb.ax.tick_params(labelsize=5)
ax.legend(handles=[Patch(facecolor="none", edgecolor=C[1], label="Persistent hotspot")], loc="lower right", fontsize=5.5)
ax.set_xlim(560000, 612000); ax.set_ylim(4482000, 4532000)
panel(ax, "a", "Low ground and persistent hotspots", x=0.0, y=0.93)

# (b) J01 elevation
sub = gs[0, 1].subgridspec(2, 1, height_ratios=[2.2, 1], hspace=0.12)
ax = fig.add_subplot(sub[0]); out, rat = strata(a, "elev_g")
draw_curves(ax, out, [C[0], MUTED, C[3]]); ax.set_xlabel(""); ax.set_xticklabels([])
ax.legend(fontsize=5.5, loc="upper left")
panel(ax, "b", "Rainfall × elevation (J01)")
ax2 = fig.add_subplot(sub[1]); rat_inv = rat.copy()
rat_inv[["ratio", "lo", "hi"]] = 1 / rat[["ratio", "hi", "lo"]].values      # Low-lying / High ground
draw_ratio(ax2, rat_inv, C[0], "Low / High"); ax2.set_xlabel("Storm peak 1-h rain (mm h⁻¹)")
t = tests[0]; ax.text(0.98, 0.04, f"interaction p = {t['p_interaction']:.2g}", transform=ax.transAxes, ha="right", fontsize=5.5, color=INK2)
J01 = rat_inv

# (c) depressions
sub = gs[0, 2].subgridspec(2, 1, height_ratios=[2.2, 1], hspace=0.12)
ax = fig.add_subplot(sub[0]); out2, rat2 = strata(a, "dep_g")
draw_curves(ax, out2, [C[3], MUTED, C[0]]); ax.set_xlabel(""); ax.set_xticklabels([])
ax.legend(fontsize=5.5, loc="upper left")
panel(ax, "c", "Rainfall × depressions (RQ17)")
ax2 = fig.add_subplot(sub[1]); draw_ratio(ax2, rat2, C[0], "Many / Few"); ax2.set_xlabel("Storm peak 1-h rain (mm h⁻¹)")
t = tests[1]; ax.text(0.98, 0.04, f"interaction p = {t['p_interaction']:.2g}", transform=ax.transAxes, ha="right", fontsize=5.5, color=INK2)

# (d) J09 elevation x imperviousness, heavy storms only
heavy = a[a.rain_class.isin(["6–12", "12–20", "≥20"])]
hc = heavy.groupby("cell_id").agg(h=("hits", "sum"), n=("n", "sum")).join(cells[["elev_p10", "impervious"]])
hc["eg"] = groups(hc.elev_p10, 3, ["Low", "Mid", "High"]); hc["ig"] = groups(hc.impervious, 3, ["Low", "Mid", "High"])
M = hc.groupby(["eg", "ig"], observed=True).apply(lambda d: d.h.sum() / d.n.sum() * 100).unstack()
Nc = hc.groupby(["eg", "ig"], observed=True).size().unstack()
ax = fig.add_subplot(gs[1, 0])
im = ax.imshow(M.values, cmap=SEQ_HOT, origin="lower", vmin=0.8)
for i in range(3):
    for j in range(3):
        ax.text(j, i, f"{M.values[i, j]:.1f}%\n(n={Nc.values[i, j]})", ha="center", va="center", fontsize=5.6,
                color="white" if M.values[i, j] > M.values.max() * 0.6 else INK)
ax.set_xticks(range(3)); ax.set_xticklabels(["Low", "Mid", "High"]); ax.set_xlabel("Impervious share tercile")
ax.set_yticks(range(3)); ax.set_yticklabels(["Low", "Mid", "High"]); ax.set_ylabel("Elevation tercile")
cb = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03); cb.set_label("P(report | storm ≥6 mm h⁻¹), %", fontsize=5.8); cb.ax.tick_params(labelsize=5.5)
panel(ax, "d", "Elevation × imperviousness (J09)")

# (e) J17 locally differentiated thresholds: 4 terrain-drainage types
pan = panel_df().merge(storms()[["eid", "max1h_mm"]], on="eid")
cells["low"] = cells.elev_p10 <= cells.elev_p10.median()
cells["cbhi"] = cells.cb_per_road_ha >= cells.cb_per_road_ha.median()
types = {(True, False): "Low-lying, sparse basins", (True, True): "Low-lying, dense basins",
         (False, False): "Higher, sparse basins", (False, True): "Higher, dense basins"}
cells["type"] = [types[(l, c)] for l, c in zip(cells.low, cells.cbhi)]
pan = pan.merge(cells[["type"]], left_on="cell_id", right_index=True)
pan["hit"] = pan.n_reports > 0
per = pan.groupby(["type", "eid"]).agg(h=("hit", "sum"), n=("hit", "size"), x=("max1h_mm", "first")).reset_index()
ax = fig.add_subplot(gs[1, 1])
xx = np.linspace(1, 45, 100); thr = {}
cols = {"Low-lying, sparse basins": C[7], "Low-lying, dense basins": C[1], "Higher, sparse basins": C[0], "Higher, dense basins": C[2]}
rng = np.random.default_rng(0)
for typ, d in per.groupby("type"):
    X = sm.add_constant(np.log(d.x)); mod = sm.GLM(np.c_[d.h, d.n - d.h], X, family=sm.families.Binomial()).fit()
    p = mod.predict(sm.add_constant(np.log(xx)))
    ax.plot(xx, p * 100, color=cols[typ], lw=1.5, label=typ)
    target = 0.02
    b0, b1 = mod.params.iloc[0], mod.params.iloc[1]
    x_thr = np.exp((np.log(target / (1 - target)) - b0) / b1)
    bs = []
    for _ in range(200):
        dd = d.sample(len(d), replace=True, random_state=int(rng.integers(1e9)))
        m2 = sm.GLM(np.c_[dd.h, dd.n - dd.h], sm.add_constant(np.log(dd.x)), family=sm.families.Binomial()).fit()
        bs.append(np.exp((np.log(target / (1 - target)) - m2.params.iloc[0]) / m2.params.iloc[1]))
    thr[typ] = (x_thr, *np.percentile(bs, [2.5, 97.5]))
ax.axhline(2, color=MUTED, lw=0.6, ls="--")
ax.set_xlabel("Storm peak 1-h rain (mm h⁻¹)"); ax.set_ylabel("Fitted P(cell reports | storm), %")
ax.legend(fontsize=5.3, loc="upper left")
ax.set_xlim(0, 45)
txt = "\n".join(f"{k.split(',')[0][:6]}… {k.split(', ')[1][:6]}: {v[0]:.0f} ({v[1]:.0f}–{v[2]:.0f})" for k, v in thr.items())
panel(ax, "e", "Local thresholds (J17)")
thr_df = pd.DataFrame([(k, *v) for k, v in thr.items()], columns=["type", "mm_h_at_2pct", "lo", "hi"])

# (f) threshold dot plot
ax = fig.add_subplot(gs[1, 2])
td = thr_df.sort_values("mm_h_at_2pct")
for i, rr in enumerate(td.itertuples()):
    ax.plot([rr.lo, rr.hi], [i, i], color=cols[rr.type], lw=1.3); ax.plot(rr.mm_h_at_2pct, i, "o", color=cols[rr.type], ms=4.5)
    ax.text(rr.hi + 0.6, i, f"{rr.mm_h_at_2pct:.1f}", va="center", fontsize=5.8)
ax.set_yticks(range(len(td))); ax.set_yticklabels([t.replace(", ", ",\n") for t in td.type], fontsize=5.8)
ax.set_xlabel("Peak 1-h rain at which P = 2% (mm h⁻¹)")
ax.set_xlim(0, td.hi.max() * 1.25)
panel(ax, "f", "Threshold by terrain–drainage type")

save(fig, "fig05_topography")
pd.concat([out.assign(f="elev"), out2.assign(f="dep")]).to_csv(TAB / "fig05_strata.csv", index=False)
thr_df.to_csv(TAB / "fig05_thresholds.csv", index=False)
write_stats("fig05", {"tests": tests, "J01_low_over_high": J01.to_dict("records"), "dep_ratio": rat2.to_dict("records"),
                      "J09_matrix_pct": M.round(2).to_dict(), "thresholds": thr_df.to_dict("records")})
