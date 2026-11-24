"""Fig. 3 - Rainfall controls on reported flooding: thresholds, accumulation windows, intensity-duration,
antecedent wetness and tide (311 x ASOS hourly/1-min x NOAA tide)."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.metrics import roc_auc_score
from scipy import stats
from .common import *  # noqa

style()
s = storms()
s = s[s.start >= "2010-01-04"].copy()
rain = pd.read_parquet(PROC / "rain_hourly.parquet").set_index("t").city
pk15 = pd.read_parquet(PROC / "rain_peak15_hourly.parquet").set_index("t").city
r = reports()

# ---- hourly city table -------------------------------------------------
cnt = r.t.dt.floor("h").value_counts().reindex(rain.index, fill_value=0).sort_index()
H = pd.DataFrame({"rain": rain})
H["y3"] = cnt[::-1].rolling(3, min_periods=1).sum()[::-1].values     # reports in [t, t+3h)
for wnd in [1, 3, 6, 12, 24, 72]:
    H[f"R{wnd}"] = rain.rolling(wnd, min_periods=wnd).sum()
H["P15"] = pk15.reindex(H.index)
H["evt"] = (H.y3 >= 3).astype(int)
H["month"] = H.index.to_period("M").astype(str)
Hw = H[(H.R24 > 0.5)].dropna(subset=["R72"])          # wet-period hours (avoid trivial dry negatives)

def auc_ci(df, col, n=300):
    d = df.dropna(subset=[col])
    base = roc_auc_score(d.evt, d[col])
    months = d.month.unique(); rng = np.random.default_rng(0); grp = dict(tuple(d.groupby("month")))
    bs = []
    for _ in range(n):
        x = pd.concat([grp[m] for m in rng.choice(months, len(months))])
        if x.evt.nunique() == 2: bs.append(roc_auc_score(x.evt, x[col]))
    return base, *np.percentile(bs, [2.5, 97.5]), len(d)

win = [(f"{w_} h", f"R{w_}") for w_ in [1, 3, 6, 12, 24, 72]]
aucs = pd.DataFrame([(lab, *auc_ci(Hw, c)) for lab, c in win], columns=["window", "auc", "lo", "hi", "n"])
H20 = Hw[Hw.index >= "2020-10-01"].dropna(subset=["P15"])
aucs20 = pd.DataFrame([(lab, *auc_ci(H20, c)) for lab, c in [("15 min", "P15")] + win],
                      columns=["window", "auc", "lo", "hi", "n"])

# ---- storm-level segmented regression --------------------------------
s["ly"] = np.log1p(s.n_reports_city)
def seg_fit(d, x="max1h_mm"):
    best = None
    for bp in np.linspace(4, 30, 105):
        X = np.c_[np.ones(len(d)), d[x], np.maximum(d[x] - bp, 0)]
        beta, res, *_ = np.linalg.lstsq(X, d.ly, rcond=None)
        sse = ((d.ly - X @ beta) ** 2).sum()
        if best is None or sse < best[0]: best = (sse, bp, beta)
    return best
_, bp, beta = seg_fit(s)
rng = np.random.default_rng(2)
bps = [seg_fit(s.sample(len(s), replace=True, random_state=int(rng.integers(1e9))))[1] for _ in range(300)]
bp_ci = np.percentile(bps, [2.5, 97.5])

# ---- NB GLM ------------------------------------------------------------
s["year"] = s.start.dt.year; s["warm"] = s.start.dt.month.isin([5, 6, 7, 8, 9, 10]).astype(int)
m = s.dropna(subset=["tide_max_m"]).copy()
for c, src in [("z_int", np.log(m.max1h_mm)), ("z_tot", np.log(m.total_mm)), ("z_dur", np.log(m.dur_h)),
               ("z_ante", np.log1p(m.ante7d_mm)), ("z_tide", m.tide_max_m), ("z_year", m.year)]:
    m[c] = (src - src.mean()) / src.std()
nb = smf.glm("n_reports_city ~ z_int + z_tot + z_dur + z_ante + z_tide + z_year + warm", data=m,
             family=sm.families.NegativeBinomial(alpha=1.0)).fit(cov_type="HC1")
# estimate alpha by profile
alphas = np.linspace(0.2, 3, 29)
ll = [smf.glm(nb.model.formula, data=m, family=sm.families.NegativeBinomial(alpha=a_)).fit().llf for a_ in alphas]
a_hat = alphas[int(np.argmax(ll))]
nb = smf.glm(nb.model.formula, data=m, family=sm.families.NegativeBinomial(alpha=a_hat)).fit(cov_type="HC1")

fig = plt.figure(figsize=(7.2, 7.4))
gs = fig.add_gridspec(3, 3, hspace=0.62, wspace=0.75)

# (a) storm scatter + segmented fit
ax = fig.add_subplot(gs[0, :2])
sc = ax.scatter(s.max1h_mm, s.n_reports_city + 1, c=s.total_mm, cmap=SEQ, norm=LogNorm(3, 150), s=7, linewidth=0.2,
                edgecolor="white", zorder=2)
xx = np.linspace(0.5, 47, 200)
ax.plot(xx, np.expm1(beta[0] + beta[1] * xx + beta[2] * np.maximum(xx - bp, 0)) + 1, color=C[1], lw=1.6, zorder=3,
        label=f"Segmented fit, break {bp:.1f} mm h⁻¹ (95% CI {bp_ci[0]:.1f}–{bp_ci[1]:.1f})")
ax.axvspan(*bp_ci, color=C[1], alpha=0.12, lw=0)
ax.set_yscale("log"); ax.set_xlabel("Storm peak 1-h rainfall, city mean (mm)"); ax.set_ylabel("Street-flooding reports + 1")
top = s.nlargest(4, "n_reports_city")
for _, t_ in top.iterrows():
    right = t_.max1h_mm > 38
    ax.annotate(t_.start.tz_convert("America/New_York").strftime("%Y-%m-%d"), (t_.max1h_mm, t_.n_reports_city + 1),
                xytext=(-4 if right else 4, 0), textcoords="offset points", fontsize=5.5, color=INK2, va="center",
                ha="right" if right else "left")
cax = ax.inset_axes([0.66, 0.24, 0.3, 0.03]); cb = fig.colorbar(sc, cax=cax, orientation="horizontal")
cb.set_label("Storm total (mm)", fontsize=6); cax.xaxis.set_label_position("top"); cb.ax.tick_params(labelsize=5.5)
ax.legend(loc="lower right", fontsize=6)
panel(ax, "a", f"Storm response is non-linear (n = {len(s)} storms, 2010–2026)")

# (b) AUC by window
ax = fig.add_subplot(gs[0, 2])
xs = np.arange(len(aucs))
ax.errorbar(xs - 0.12, aucs.auc, yerr=[aucs.auc - aucs.lo, aucs.hi - aucs.auc], fmt="o", color=C[0], ms=3.5, lw=1, capsize=0, label="2010–2026 (hourly)")
a2 = aucs20.set_index("window")
ax.errorbar(np.arange(-1, len(aucs)) + 0.12, a2.auc.values, yerr=[a2.auc - a2.lo, a2.hi - a2.auc], fmt="s", color=C[1], ms=3.5, lw=1, capsize=0, label="2020–2026 (+1-min)")
ax.set_xticks(np.arange(-1, len(aucs))); ax.set_xticklabels(["15m"] + [w_[0].replace(" ", "") for w_ in win], fontsize=6)
ax.set_xlabel("Antecedent accumulation window"); ax.set_ylabel("AUC: ≥3 reports in next 3 h")
ax.legend(fontsize=5.5, loc="lower center")
panel(ax, "b", "Predictive window")

# (c) intensity-duration matrix
ax = fig.add_subplot(gs[1, :2])
ib = [0, 3, 6, 10, 15, 50]; db = [0, 4, 8, 12, 18, 24, 72]
s["ib"] = pd.cut(s.max1h_mm, ib, right=False); s["db"] = pd.cut(s.dur_h, db, right=False)
pv = s.pivot_table(index="db", columns="ib", values="n_reports_city", aggfunc="median", observed=False)
nn = s.pivot_table(index="db", columns="ib", values="n_reports_city", aggfunc="size", observed=False)
pv = pv.where(nn >= 3)
im = ax.imshow(pv.values + 1, cmap=SEQ_HOT, norm=LogNorm(1, 400), origin="lower", aspect="auto")
for i in range(pv.shape[0]):
    for j in range(pv.shape[1]):
        if nn.iloc[i, j] >= 3:
            v = pv.iloc[i, j]
            ax.text(j, i, f"{v:.0f}\n(n={nn.iloc[i, j]})", ha="center", va="center", fontsize=5.3,
                    color="white" if v > 40 else INK)
        elif nn.iloc[i, j] > 0:
            ax.text(j, i, f"n={nn.iloc[i, j]}", ha="center", va="center", fontsize=5, color=MUTED)
ax.set_xticks(range(len(ib) - 1)); ax.set_xticklabels([f"{a}–{b}" for a, b in zip(ib[:-2], ib[1:-1])] + [f"≥{ib[-2]}"])
ax.set_yticks(range(len(db) - 1)); ax.set_yticklabels([f"{a}–{b}" for a, b in zip(db[:-1], db[1:])])
ax.set_xlabel("Peak 1-h intensity (mm h⁻¹)"); ax.set_ylabel("Storm duration (h)")
cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02); cbar.set_label("Median reports", fontsize=6); cbar.ax.tick_params(labelsize=5.5)
panel(ax, "c", "Intensity–duration matrix (J05)")

# (d) NB coefficients
ax = fig.add_subplot(gs[1, 2])
names = {"z_int": "Peak 1-h", "z_tot": "Total", "z_dur": "Duration", "z_ante": "Antec. 7-d",
         "z_tide": "Max tide", "z_year": "Year", "warm": "Warm season"}
ci = nb.conf_int()
rows = [(names[k], np.exp(nb.params[k]), np.exp(ci.loc[k, 0]), np.exp(ci.loc[k, 1]), nb.pvalues[k]) for k in names]
for i, (lab, e, lo, hi, pv_) in enumerate(rows[::-1]):
    col = C[0] if lo > 1 else (C[7] if hi < 1 else MUTED)
    ax.plot([lo, hi], [i, i], color=col, lw=1.2); ax.plot(e, i, "o", color=col, ms=4)
ax.axvline(1, color=MUTED, lw=0.6); ax.set_xscale("log")
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r_[0] for r_ in rows[::-1]], fontsize=6)
ax.set_xlabel("Incidence-rate ratio per SD (NB GLM)")
from matplotlib.ticker import NullFormatter, FixedLocator
ax.xaxis.set_major_locator(FixedLocator([0.8, 1, 1.5, 2])); ax.set_xticklabels(["0.8", "1", "1.5", "2"])
ax.xaxis.set_minor_formatter(NullFormatter()); ax.set_xlim(0.75, 2.3)
panel(ax, "d", "Joint storm model")

# (e) antecedent wetness x intensity (J06)
ax = fig.add_subplot(gs[2, 0:2])
s["ante_t"] = pd.qcut(s.ante7d_mm.rank(method="first"), 3, labels=["Dry (lowest third)", "Middle", "Wet (highest third)"])
for k, (lab, d) in enumerate(s.groupby("ante_t", observed=True)):
    t = d.groupby("rain_class", observed=True).n_reports_city.agg(["mean", "count", "std"])
    se = t["std"] / np.sqrt(t["count"])
    x = np.arange(len(t)) + (k - 1) * 0.12
    ax.errorbar(x, t["mean"], yerr=1.96 * se, fmt="-o", color=[C[3], MUTED, C[0]][k], ms=3, lw=1.2, capsize=0, label=f"7-d antecedent: {lab}")
ax.set_xticks(range(len(RAIN_LABELS))); ax.set_xticklabels([f"{l}\n(n={n})" for l, n in zip(RAIN_LABELS, s.rain_class.value_counts().reindex(RAIN_LABELS))])
ax.set_xlabel("Peak 1-h intensity class (mm h⁻¹)"); ax.set_ylabel("Mean reports per storm (95% CI)")
ax.set_yscale("log"); ax.legend(fontsize=6, loc="upper left")
panel(ax, "e", "Antecedent 7-day rainfall by intensity class (J06)")

# (f) tide x intensity (J07) - coastal cells only
ax = fig.add_subplot(gs[2, 2])
st_ = static().set_index("cell_id")
coast = st_[(st_.dist_shore_m < 500) & (st_.elev_p10 < 3)].index
pan = panel_df(); pan = pan[pan.cell_id.isin(coast)]
pc = pan.groupby("eid").n_reports.sum().rename("coast")
inland = st_[(st_.dist_shore_m > 1500)].index
pi_ = panel_df(); pi_ = pi_[pi_.cell_id.isin(inland)].groupby("eid").n_reports.sum().rename("inland")
s2 = s.set_index("eid").join(pc).join(pi_).dropna(subset=["tide_max_m"])
s2["tide_hi"] = s2.tide_max_m >= s2.tide_max_m.quantile(0.75)
s2["heavy"] = s2.max1h_mm >= 6
out = []
for grp, lab in [("coast", f"Low coastal cells (n={len(coast)})"), ("inland", f"Inland cells (n={len(inland)})")]:
    nk = len(coast) if grp == "coast" else len(inland)
    for hv in [False, True]:
        d = s2[s2.heavy == hv]
        hi_ = d[d.tide_hi][grp].mean() / nk * 1000; lo_ = d[~d.tide_hi][grp].mean() / nk * 1000
        out.append((lab, hv, lo_, hi_, stats.mannwhitneyu(d[d.tide_hi][grp], d[~d.tide_hi][grp]).pvalue))
out = pd.DataFrame(out, columns=["grp", "heavy", "low_tide", "high_tide", "p"])
xb = np.arange(2)
for k, (lab, d) in enumerate(out.groupby("grp", sort=False)):
    ratio = (d.high_tide / d.low_tide).values
    ax.bar(xb + (k - 0.5) * 0.36, ratio, width=0.34, color=[C[0], MUTED][k], label=lab)
    for j, (rv, pv_) in enumerate(zip(ratio, d.p)):
        ax.text(j + (k - 0.5) * 0.36, rv + 0.05, f"{rv:.2f}\np={pv_:.2g}", ha="center", fontsize=5.2)
ax.axhline(1, color=INK2, lw=0.6)
ax.set_xticks(xb); ax.set_xticklabels(["Peak <6 mm h⁻¹", "Peak ≥6 mm h⁻¹"])
ax.set_ylabel("Report rate ratio, high vs low tide"); ax.legend(fontsize=5.3, loc="upper left")
ax.set_ylim(0, max(out.high_tide / out.low_tide) * 1.45)
panel(ax, "f", "High tide vs low tide (J07)")

save(fig, "fig03_rainfall")
aucs.to_csv(TAB / "fig03_auc_windows.csv", index=False); aucs20.to_csv(TAB / "fig03_auc_windows_2020.csv", index=False)
out.to_csv(TAB / "fig03_tide.csv", index=False)
pd.DataFrame(rows, columns=["term", "irr", "lo", "hi", "p"]).to_csv(TAB / "fig03_nb_glm.csv", index=False)
write_stats("fig03", {"breakpoint_mm_h": bp, "breakpoint_ci": bp_ci.tolist(), "slope_below": beta[1], "slope_above": beta[1] + beta[2],
                      "nb_alpha": a_hat, "nb_n": int(nb.nobs), "auc": aucs.to_dict("records"), "auc2020": aucs20.to_dict("records"),
                      "spearman_max1h": stats.spearmanr(s.max1h_mm, s.n_reports_city)[0],
                      "spearman_total": stats.spearmanr(s.total_mm, s.n_reports_city)[0],
                      "spearman_dur": stats.spearmanr(s.dur_h, s.n_reports_city)[0], "tide": out.to_dict("records")})
print(nb.summary().tables[1])
