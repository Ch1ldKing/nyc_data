"""Fig. 10 - Predicting where a storm produces flooding reports: multi-source vs single-source models,
temporal and spatial-block validation, SHAP attribution, and a design-storm hazard map."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import lightgbm as lgb
import shap
from sklearn.metrics import average_precision_score, roc_auc_score, precision_recall_curve
from scipy import stats
from .common import *  # noqa
from .strat import urban_mask

style()
SEED = 42
s = storms().copy()
s["warm"] = s.start.dt.month.isin([5, 6, 7, 8, 9, 10]).astype(int)
g = grid().merge(static(), on="cell_id")
g = g[urban_mask(g)].copy()
cent = g.geometry.centroid
g["block"] = (np.floor(cent.x / 5000)).astype(int).astype(str) + "_" + (np.floor(cent.y / 5000)).astype(int).astype(str)
# nearest gauge for local storm rain
gauges = {"NYC": (40.7790, -73.9693), "LGA": (40.7794, -73.8803), "JFK": (40.6386, -73.7622), "EWR": (40.6825, -74.1694), "TEB": (40.8501, -74.0608)}
import geopandas as gpd
gp = gpd.GeoSeries(gpd.points_from_xy([v[1] for v in gauges.values()], [v[0] for v in gauges.values()]), crs=4326).to_crs("EPSG:26918")
dist = np.stack([cent.distance(pt).values for pt in gp], 1)
g["gauge"] = np.array(list(gauges))[dist.argmin(1)]

pan = panel_df()
pan = pan[pan.cell_id.isin(g.cell_id)]
storm_cols = ["total_mm", "max1h_mm", "max3h_mm", "dur_h", "ante72_mm", "ante7d_mm", "tide_max_m", "warm"]
pan = pan.merge(s[["eid", "start"] + storm_cols + [f"tot_{k}" for k in gauges]], on="eid")
static_cols = [c for grp in GROUPS.values() for c in grp]
pan = pan.merge(g[["cell_id", "gauge", "block", "boro"] + static_cols], on="cell_id")
pan["local_total_mm"] = np.select([pan.gauge == k for k in gauges], [pan[f"tot_{k}"] for k in gauges])
pan["y"] = (pan.n_reports > 0).astype(np.int8)
RAIN = storm_cols + ["local_total_mm"]
sets = {"Rain only": RAIN, "Static only": static_cols,
        "Rain + topography": RAIN + GROUPS["Topography"], "Rain + built form": RAIN + GROUPS["Built form"],
        "Rain + greenness": RAIN + GROUPS["Greenness"], "Rain + drainage": RAIN + GROUPS["Drainage"],
        "Rain + population": RAIN + GROUPS["Population / reporting"],
        "Rain + physical (no pop.)": RAIN + [c for k, v in GROUPS.items() if k != "Population / reporting" for c in v],
        "All sources": RAIN + static_cols}
dev_all = pan[pan.start < "2022-07-01"]; te = pan[pan.start >= "2022-07-01"]
# validation = random 20% of development storms (storm-grouped), so early stopping is not tied to one odd year
_rng = np.random.default_rng(SEED); _ev = dev_all.eid.unique(); _val_ev = set(_rng.choice(_ev, int(len(_ev) * 0.2), replace=False))
va = dev_all[dev_all.eid.isin(_val_ev)]; tr = dev_all[~dev_all.eid.isin(_val_ev)]
params = dict(objective="binary", learning_rate=0.03, num_leaves=31, min_child_samples=200, subsample=0.8, subsample_freq=1,
              colsample_bytree=0.8, reg_lambda=1.0, n_estimators=2000, verbose=-1, random_state=SEED, n_jobs=8)

def fit(cols, trn, val):
    m = lgb.LGBMClassifier(**params)
    m.fit(trn[cols], trn.y, eval_set=[(val[cols], val.y)], eval_metric="average_precision",
          callbacks=[lgb.early_stopping(200, verbose=False)])
    return m

def storm_boot_ap(df, p, n=300, seed=0):
    rng = np.random.default_rng(seed); ids = df.eid.values; u = np.unique(ids)
    pos = {e: np.nonzero(ids == e)[0] for e in u}; out = []
    for _ in range(n):
        idx = np.concatenate([pos[e] for e in rng.choice(u, len(u))])
        if df.y.values[idx].sum() > 0: out.append(average_precision_score(df.y.values[idx], p[idx]))
    return np.percentile(out, [2.5, 97.5])

def within_storm_auc(df, p):
    """Mean AUC across test storms with >=5 positive cells: can the model rank cells within a storm?"""
    out = []
    for e, idx in df.groupby("eid").indices.items():
        yy = df.y.values[idx]
        if yy.sum() >= 5: out.append(roc_auc_score(yy, p[idx]))
    return np.mean(out), len(out)

res, curves, models = [], {}, {}
for name, cols in sets.items():
    m = fit(cols, tr, va); p = m.predict_proba(te[cols])[:, 1]
    lo, hi = storm_boot_ap(te, p)
    wauc, nst = within_storm_auc(te, p)
    res.append({"set": name, "ap": average_precision_score(te.y, p), "ap_lo": lo, "ap_hi": hi, "auc": roc_auc_score(te.y, p),
                "within_storm_auc": wauc, "n_storms_wauc": nst,
                "n_features": len(cols), "best_iter": m.best_iteration_})
    curves[name] = precision_recall_curve(te.y, p)[:2]; models[name] = (m, cols, p)
    print(name, res[-1])
res = pd.DataFrame(res); prev = te.y.mean()

# spatial-block CV (train+valid period, 5 folds over 5-km blocks) for three key sets
from sklearn.model_selection import GroupKFold
dev = pan[pan.start < "2022-07-01"]
sp = []
for name in ["Rain only", "Static only", "Rain + physical (no pop.)", "All sources"]:
    cols = sets[name]; aps = []
    for k, (i_tr, i_te) in enumerate(GroupKFold(5).split(dev, groups=dev.block)):
        a_, b_ = dev.iloc[i_tr], dev.iloc[i_te]
        inner = a_.eid.isin(_val_ev)
        m = fit(cols, a_[~inner], a_[inner]); p = m.predict_proba(b_[cols])[:, 1]
        aps.append(average_precision_score(b_.y, p) / b_.y.mean())
    sp.append({"set": name, "lift_mean": np.mean(aps), "lift_sd": np.std(aps)})
sp = pd.DataFrame(sp)

# SHAP on the full model
m_all, cols_all, p_all = models["All sources"]
samp = te.sample(30000, random_state=SEED)
expl = shap.TreeExplainer(m_all)
sv = expl.shap_values(samp[cols_all])
sv = sv[1] if isinstance(sv, list) else sv
imp = pd.Series(np.abs(sv).mean(0), index=cols_all).sort_values(ascending=False)
grp_of = {v: k for k, vs in GROUPS.items() for v in vs}; grp_of.update({c: "Rainfall / storm" for c in RAIN})
gimp = imp.groupby(imp.index.map(grp_of)).sum().sort_values(ascending=False)
gcol = dict(GROUP_COLOR); gcol["Rainfall / storm"] = INK2
LAB2 = dict(LABEL); LAB2.update({"total_mm": "Storm total (city)", "max1h_mm": "Peak 1-h (city)", "max3h_mm": "Peak 3-h (city)",
                                 "dur_h": "Duration", "ante72_mm": "Antecedent 72 h", "ante7d_mm": "Antecedent 7 d",
                                 "tide_max_m": "Max tide", "warm": "Warm season", "local_total_mm": "Storm total (nearest gauge)"})

fig = plt.figure(figsize=(7.2, 7.4))
gs = fig.add_gridspec(2, 3, hspace=0.45, wspace=0.65)

# (a) PR curves
ax = fig.add_subplot(gs[0, 0])
show = [("Rain only", MUTED), ("Static only", C[1]), ("Rain + physical (no pop.)", C[0]), ("All sources", INK)]
for name, col in show:
    p_, r_ = curves[name]; k_ = r_ >= 0.01; p_, r_ = p_[k_], r_[k_]; ax.plot(r_, p_, color=col, lw=1.3, label=f"{name} (AP {res.set_index('set').loc[name, 'ap']:.3f})")
ax.axhline(prev, color=MUTED, ls="--", lw=0.6); ax.text(0.98, prev * 1.15, f"prevalence {prev:.3f}", ha="right", fontsize=5.3, color=INK2)
ax.set_xlabel("Recall"); ax.set_ylabel("Precision"); ax.set_ylim(0, 0.2); ax.legend(fontsize=5, loc="upper right")
panel(ax, "a", "Held-out storms, Jul 2022 to 2026")

# (b) AP lift by feature set
ax = fig.add_subplot(gs[0, 1:])
rr = res.sort_values("ap"); y = np.arange(len(rr))
ax.barh(y, rr.ap / prev, color=[INK if n == "All sources" else (C[0] if "physical" in n else "#9fb8d9") for n in rr.set], height=0.6)
ax.errorbar(rr.ap / prev, y, xerr=[(rr.ap - rr.ap_lo) / prev, (rr.ap_hi - rr.ap) / prev], fmt="none", ecolor=INK, lw=0.8)
for yy, (a_, hi_, auc, wa) in enumerate(zip(rr.ap / prev, rr.ap_hi / prev, rr.auc, rr.within_storm_auc)):
    ax.text(hi_ + 0.2, yy, f"AUC {auc:.3f} | within-storm {wa:.3f}", va="center", fontsize=5.2, color=INK2)
spi = sp.set_index("set")
for yy, n in enumerate(rr.set):
    if n in spi.index:
        ax.plot(spi.loc[n, "lift_mean"], yy, "D", ms=3.5, color=C[1], zorder=4)
ax.plot([], [], "D", color=C[1], ms=3.5, label="Spatial-block CV (5-km blocks, mean of 5 folds)")
ax.set_yticks(y); ax.set_yticklabels(rr.set, fontsize=6); ax.set_xlabel("Average precision / prevalence (lift), temporal test with 95% storm-bootstrap CI")
ax.legend(fontsize=5.4, loc="lower right"); ax.set_xlim(0, (rr.ap_hi / prev).max() * 1.55)
panel(ax, "b", "Are multi-source data more predictive?")

# (c) SHAP beeswarm (custom)
ax = fig.add_subplot(gs[1, 0])
top = imp.index[:14][::-1]
rng = np.random.default_rng(0)
for i, f_ in enumerate(top):
    j = cols_all.index(f_); v = sv[:, j]; x = samp[f_].values
    sub = rng.choice(len(v), 2500, replace=False)
    q = pd.Series(x[sub]).rank(pct=True).values
    ax.scatter(v[sub], i + rng.normal(0, 0.12, len(sub)), c=q, cmap="coolwarm", s=1.2, linewidth=0, alpha=0.7, rasterized=True)
ax.set_yticks(range(len(top))); ax.set_yticklabels([LAB2.get(f_, f_) for f_ in top], fontsize=5.4)
for t_, f_ in zip(ax.get_yticklabels(), top):
    t_.set_color(gcol[grp_of[f_]])
ax.axvline(0, color=MUTED, lw=0.5); ax.set_xlabel("SHAP value (log-odds)")
sm_ = plt.cm.ScalarMappable(cmap="coolwarm"); cax = ax.inset_axes([0.62, 0.08, 0.32, 0.03])
cb = fig.colorbar(sm_, cax=cax, orientation="horizontal", ticks=[0, 1]); cb.ax.set_xticklabels(["low", "high"], fontsize=5)
cb.set_label("feature value", fontsize=5); cax.xaxis.set_label_position("top")
panel(ax, "c", "SHAP: top features")

# (d) grouped importance
ax = fig.add_subplot(gs[1, 1])
share = gimp / gimp.sum() * 100
ax.barh(range(len(share))[::-1], share.values, color=[gcol[k] for k in share.index], height=0.6)
for yy, v in zip(range(len(share))[::-1], share.values):
    ax.text(v + 1, yy, f"{v:.0f}%", va="center", fontsize=6)
ax.set_yticks(range(len(share))[::-1]); ax.set_yticklabels(share.index, fontsize=6); ax.set_xlim(0, share.max() * 1.3)
ax.set_xlabel("Share of mean |SHAP|")
panel(ax, "d", "Contribution by source (RQ28)")

# (e) design-storm hazard map + agreement with DEP stormwater model
ax = fig.add_subplot(gs[1, 2]); basemap(ax)
design = g[["cell_id"] + static_cols].copy()
for c, v in {"total_mm": 60, "max1h_mm": 30, "max3h_mm": 50, "dur_h": 6, "ante72_mm": s.ante72_mm.median(),
             "ante7d_mm": s.ante7d_mm.median(), "tide_max_m": s.tide_max_m.median(), "warm": 1, "local_total_mm": 60}.items():
    design[c] = v
design["p"] = m_all.predict_proba(design[cols_all])[:, 1]
gg = g[["cell_id", "geometry", "swm_extreme_deep", "swm_extreme_nuisance"]].merge(design[["cell_id", "p"]], on="cell_id")
gg.plot(ax=ax, column="p", cmap=SEQ_HOT, linewidth=0, vmin=0, vmax=gg.p.quantile(0.98), zorder=1)
sm2 = plt.cm.ScalarMappable(cmap=SEQ_HOT, norm=plt.Normalize(0, gg.p.quantile(0.98) * 100))
cax = ax.inset_axes([0.03, 0.9, 0.42, 0.03]); cb = fig.colorbar(sm2, cax=cax, orientation="horizontal")
cb.set_label("P(report), 30 mm h⁻¹ / 60 mm storm (%)", fontsize=5.2); cax.xaxis.set_label_position("top"); cb.ax.tick_params(labelsize=5)
rho_sw = stats.spearmanr(gg.p, gg.swm_extreme_deep + gg.swm_extreme_nuisance)
ax.text(0.97, 0.04, f"ρ with DEP 'extreme'\nmodelled flood area = {rho_sw[0]:.2f}", transform=ax.transAxes, ha="right", fontsize=5.3, color=INK2)
ax.set_xlim(560000, 612000); ax.set_ylim(4482000, 4532000)
panel(ax, "e", "Design-storm hazard", x=0.02, y=1.0)

save(fig, "fig10_model")
res.to_csv(TAB / "fig10_ablation.csv", index=False); sp.to_csv(TAB / "fig10_spatial_cv.csv", index=False)
imp.to_csv(TAB / "fig10_shap_importance.csv"); design[["cell_id", "p"]].to_csv(TAB / "fig10_design_storm_hazard.csv", index=False)
write_stats("fig10", {"rows": {"train": len(tr), "valid": len(va), "test": len(te)}, "prevalence_test": prev,
                      "ablation": res.to_dict("records"), "spatial_cv": sp.to_dict("records"), "group_share_pct": share.round(1).to_dict(),
                      "top_features": imp.head(15).round(4).to_dict(), "rho_design_vs_stormwater_map": [rho_sw[0], rho_sw[1]]})
