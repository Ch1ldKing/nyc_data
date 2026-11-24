"""Fig. 6 - Built form, land use and greenness x rainfall (2017 land cover, PLUTO, 311 storm panel).
J03, J04, J10, J15; RQ22-24, RQ37; multivariable cell model (RQ28)."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
import statsmodels.formula.api as smf
from .common import *  # noqa
from .strat import agg_table, groups, strata, interaction_test, draw_curves, draw_ratio, urban_mask

style()
a = agg_table().copy()
cells = a.drop_duplicates("cell_id").set_index("cell_id")
a["imp_g"] = a.cell_id.map(groups(cells.impervious, 3, ["Low impervious", "Middle", "High impervious"]))
a["grn_g"] = a.cell_id.map(groups(cells.green, 3, ["Low green", "Middle", "High green"]))
tests = [interaction_test(a, f) for f in ["impervious", "green", "canopy", "building_cov"]] + [interaction_test(a, "far_cell", log=True)]

fig = plt.figure(figsize=(7.2, 7.0))
gs = fig.add_gridspec(2, 3, hspace=0.42, wspace=0.55)

def curve_panel(spec, col, colors, letter, title, ratio_lab, inv=False):
    sub = spec.subgridspec(2, 1, height_ratios=[2.2, 1], hspace=0.12)
    ax = fig.add_subplot(sub[0]); out, rat = strata(a, col)
    draw_curves(ax, out, colors); ax.set_xlabel(""); ax.set_xticklabels([]); ax.legend(fontsize=5.5, loc="upper left")
    panel(ax, letter, title)
    ax2 = fig.add_subplot(sub[1])
    if inv:
        rat = rat.copy(); rat[["ratio", "lo", "hi"]] = 1 / rat[["ratio", "hi", "lo"]].values
    draw_ratio(ax2, rat, colors[-1] if not inv else colors[0], ratio_lab); ax2.set_xlabel("Storm peak 1-h rain (mm h⁻¹)")
    return ax, out, rat

ax, out_i, rat_i = curve_panel(gs[0, 0], "imp_g", [C[2], MUTED, C[1]], "a", "Rainfall × imperviousness (J04)", "High / Low")
ax.text(0.98, 0.04, f"interaction p = {tests[0]['p_interaction']:.2g}", transform=ax.transAxes, ha="right", fontsize=5.5, color=INK2)
ax, out_g, rat_g = curve_panel(gs[0, 1], "grn_g", [C[1], MUTED, C[2]], "b", "Rainfall × greenness (J03)", "High / Low")
ax.text(0.98, 0.04, f"interaction p = {tests[1]['p_interaction']:.2g}", transform=ax.transAxes, ha="right", fontsize=5.5, color=INK2)

# (c) J15: green within highly impervious cells
hi_imp = a[a.imp_g == "High impervious"].copy()
hc = hi_imp.drop_duplicates("cell_id").set_index("cell_id")
hi_imp["can_g"] = hi_imp.cell_id.map(groups(hc.canopy, 3, ["Low canopy", "Middle", "High canopy"]))
out_c, rat_c = strata(hi_imp, "can_g")
sub = gs[0, 2].subgridspec(2, 1, height_ratios=[2.2, 1], hspace=0.12)
ax = fig.add_subplot(sub[0]); draw_curves(ax, out_c, [C[1], MUTED, C[2]]); ax.set_xlabel(""); ax.set_xticklabels([])
ax.legend(fontsize=5.5, loc="upper left")
panel(ax, "c", "Canopy within high-imperv. cells (J15)")
ax.text(0.98, 0.04, f"canopy range {hc.canopy.min():.2f}–{hc.canopy.max():.2f}", transform=ax.transAxes, ha="right", fontsize=5.3, color=INK2)
ax2 = fig.add_subplot(sub[1]); draw_ratio(ax2, rat_c, C[2], "High / Low"); ax2.set_xlabel("Storm peak 1-h rain (mm h⁻¹)")

# (d) J10 land use among low-lying cells
heavy = a[a.rain_class.isin(["6–12", "12–20", "≥20"])]
hcell = heavy.groupby("cell_id").agg(h=("hits", "sum"), n=("n", "sum")).join(cells[["elev_p10", "lu_dominant"]])
hcell["low"] = hcell.elev_p10 <= hcell.elev_p10.quantile(1 / 3)
lus = {"res": "Residential", "mixed": "Mixed", "comm": "Commercial", "ind": "Industrial", "public": "Public facil.",
       "transp": "Transport/util.", "open": "Open space"}
rng = np.random.default_rng(0); rows = []
for k, lab in lus.items():
    for low in [True, False]:
        d = hcell[(hcell.lu_dominant == k) & (hcell.low == low)]
        if len(d) < 8: continue
        p = d.h.sum() / d.n.sum()
        bs = [d.iloc[i].h.sum() / d.iloc[i].n.sum() for i in (rng.integers(0, len(d), len(d)) for _ in range(400))]
        rows.append((lab, low, p * 100, *np.percentile(bs, [2.5, 97.5]) * 100, len(d)))
lu = pd.DataFrame(rows, columns=["lu", "low", "p", "lo", "hi", "n"])
order = lu[lu.low].sort_values("p").lu.tolist()
ax = fig.add_subplot(gs[1, 0])
for low, col, off, lab in [(True, C[0], 0.15, "Low-lying third"), (False, MUTED, -0.15, "Other cells")]:
    d = lu[lu.low == low].set_index("lu").reindex(order)
    y = np.arange(len(order)) + off
    ax.errorbar(d.p, y, xerr=[d.p - d.lo, d.hi - d.p], fmt="o", ms=3.5, color=col, lw=1, capsize=0, label=lab)
    for yy, (n_, pp, hh) in zip(y, zip(d.n, d.p, d.hi)):
        if not np.isnan(n_): ax.text(hh + 0.08, yy, f"n={int(n_)}", va="center", fontsize=4.8, color=INK2)
ax.set_yticks(range(len(order))); ax.set_yticklabels(order, fontsize=6)
ax.set_xlabel("P(report | storm ≥6 mm h⁻¹), %"); ax.legend(fontsize=5.5, loc="center right")
panel(ax, "d", "Land use among low-lying cells (J10)")

# (e) quintile response for built-form variables (heavy storms)
ax = fig.add_subplot(gs[1, 1])
hc2 = heavy.groupby("cell_id").agg(h=("hits", "sum"), n=("n", "sum")).join(cells.drop(columns=["hits", "n", "reps", "rain_class"]))
feats = [("building_cov", C[1]), ("far_cell", C[0]), ("canopy", C[2])]
for f_, col in feats:
    q = pd.qcut(hc2[f_].rank(method="first"), 5, labels=False)
    t = hc2.groupby(q).apply(lambda d: d.h.sum() / d.n.sum() * 100)
    ax.plot(np.arange(1, 6), t.values, "-o", color=col, ms=3, lw=1.3, label=LABEL[f_])
ax.set_xticks(range(1, 6)); ax.set_xlabel("Cell quintile of variable"); ax.set_ylabel("P(report | storm ≥6 mm h⁻¹), %")
ax.legend(fontsize=5.5, loc="lower center")
panel(ax, "e", "Built-form gradients (storms ≥6 mm h⁻¹)")

# (f) multivariable NB GLM across groups
g = cell_table()
g = g[urban_mask(g)].copy()
cent = g.geometry.centroid
g["block"] = (np.floor(cent.x / 2000)).astype(int).astype(str) + "_" + (np.floor(cent.y / 2000)).astype(int).astype(str)
vars_ = ["elev_p10", "slope_mean", "dep_frac", "dist_shore_m", "impervious", "building_cov", "far_cell", "canopy",
         "cb_per_road_ha", "ms4_frac", "gi_density", "pop", "rpl_themes"]
d = g.dropna(subset=vars_ + ["storm_reports"]).copy()
for v in vars_:
    x = np.log1p(d[v]) if v in ("far_cell", "pop", "gi_density", "dist_shore_m") else d[v]
    d["z_" + v] = (x - x.mean()) / x.std()
d["off"] = np.log(d.land_km2 * len(storms()))
form = "storm_reports ~ " + " + ".join("z_" + v for v in vars_) + " + boro"
alphas = np.linspace(0.2, 3, 15)
lls = [smf.glm(form, d, family=sm.families.NegativeBinomial(alpha=al), offset=d.off).fit().llf for al in alphas]
al = alphas[int(np.argmax(lls))]
nb = smf.glm(form, d, family=sm.families.NegativeBinomial(alpha=al), offset=d.off).fit(
    cov_type="cluster", cov_kwds={"groups": pd.factorize(d.block)[0]})
ax = fig.add_subplot(gs[1, 2])
grp_of = {v: k for k, vs in GROUPS.items() for v in vs}
ci = nb.conf_int(); rows2 = []
for v in vars_:
    k = "z_" + v; rows2.append((v, np.exp(nb.params[k]), np.exp(ci.loc[k, 0]), np.exp(ci.loc[k, 1]), nb.pvalues[k]))
fr = pd.DataFrame(rows2, columns=["var", "irr", "lo", "hi", "p"]).sort_values("irr")
for i, rr in enumerate(fr.itertuples()):
    col = GROUP_COLOR[grp_of[rr.var]]
    ax.plot([rr.lo, rr.hi], [i, i], color=col, lw=1.2); ax.plot(rr.irr, i, "o", color=col, ms=3.8,
                                                                 mfc=col if rr.p < 0.05 else "white")
ax.axvline(1, color=MUTED, lw=0.6); ax.set_xscale("log")
from matplotlib.ticker import FixedLocator, NullFormatter
ax.xaxis.set_major_locator(FixedLocator([0.6, 0.8, 1, 1.25, 1.6])); ax.set_xticklabels(["0.6", "0.8", "1", "1.25", "1.6"])
ax.xaxis.set_minor_formatter(NullFormatter())
ax.set_yticks(range(len(fr))); ax.set_yticklabels([LABEL[v] for v in fr["var"]], fontsize=5.6)
ax.set_xlabel("IRR per SD (NB, borough FE)")
ax.text(0.98, 0.02, f"n={int(nb.nobs)} urban cells\nopen = p≥0.05\n(2-km cluster SE)", transform=ax.transAxes, va="bottom", ha="right", fontsize=5.2, color=INK2)
panel(ax, "f", "Multivariable cell model")

save(fig, "fig06_built_green")
fr.to_csv(TAB / "fig06_nb_cell_model.csv", index=False); lu.to_csv(TAB / "fig06_landuse.csv", index=False)
write_stats("fig06", {"tests": tests, "imperv_ratio": rat_i.to_dict("records"), "green_ratio": rat_g.to_dict("records"),
                      "J15_canopy_ratio_in_high_imperv": rat_c.to_dict("records"), "nb_alpha": al, "nb_n": int(nb.nobs),
                      "nb": fr.to_dict("records"), "landuse": lu.to_dict("records")})
