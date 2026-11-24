"""Fig. 8 - Measured ponding dynamics (FloodNet events x ASOS 1-min/hourly rain x DEM x catch basins x tide).
RQ42, J07, J18."""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from scipy import stats
from .common import *  # noqa

style()
ev = pd.read_parquet(PROC / "floodnet_events.parquet")
se = pd.read_parquet(PROC / "floodnet_sensors.parquet")
for c in ["lowest_point_height_delta_inches"]:
    se[c] = pd.to_numeric(se[c], errors="coerce")
ev = ev.merge(se, on="sensor_id", how="left", suffixes=("", "_s"))
ev["tidal"] = ev.tidally_influenced.eq("Yes")
# nearest 1-min gauge
gauges = {"NYC": (40.7790, -73.9693), "LGA": (40.7794, -73.8803), "JFK": (40.6386, -73.7622), "EWR": (40.6825, -74.1694)}
lat, lon = pd.to_numeric(ev.latitude, errors="coerce"), pd.to_numeric(ev.longitude, errors="coerce")
dist = np.stack([np.hypot(lat - a, (lon - b) * np.cos(np.radians(40.7))) for a, b in gauges.values()], 1)
ev["gauge"] = np.array(list(gauges))[np.nanargmin(np.where(np.isnan(dist), 9, dist), 1)]
rain = pd.read_parquet(PROC / "rain_hourly.parquet").set_index("t")
p15 = pd.read_parquet(PROC / "rain_peak15_hourly.parquet").set_index("t")
t0 = ev.flood_start_time.dt.floor("h")
def win_sum(row_t, g, a, b, src):
    return src[g].loc[row_t + pd.Timedelta(hours=a): row_t + pd.Timedelta(hours=b)]
ev["rain_win"] = [rain[g].loc[t - pd.Timedelta(hours=3): t + pd.Timedelta(hours=1)].sum() for t, g in zip(t0, ev.gauge)]
ev["rain60"] = [rain[g].loc[t - pd.Timedelta(hours=2): t + pd.Timedelta(hours=1)].max() for t, g in zip(t0, ev.gauge)]
ev["rain15"] = [p15[g].loc[t - pd.Timedelta(hours=2): t + pd.Timedelta(hours=1)].max() if g in p15 else np.nan for t, g in zip(t0, ev.gauge)]
tide = pd.read_parquet(RAW / "tides/battery_hourly.parquet"); tide["t"] = pd.to_datetime(tide.t, utc=True)
tide["v"] = pd.to_numeric(tide.v, errors="coerce")
obs = tide[tide["product"] == "hourly_height"].set_index("t").v.sort_index()
ev["tide_m"] = obs.reindex(t0, method="nearest", tolerance=pd.Timedelta(hours=1)).values
ev["rise_rate"] = ev.max_depth_mm / ev.onset_time_mins.clip(lower=1)        # mm/min
ev["recess_rate"] = ev.max_depth_mm / ev.drain_time_mins.clip(lower=1)
ev["rainy"] = ev.rain_win >= 2

# parse profiles
def prof(dstr, tstr):
    try:
        d = np.array(json.loads(dstr), float) * 25.4; t = np.array(json.loads(tstr), float)
        return d, t
    except Exception:
        return None, None

fig = plt.figure(figsize=(7.2, 7.0))
gs = fig.add_gridspec(2, 3, hspace=0.5, wspace=0.62)

# (a) normalised event hydrographs
ax = fig.add_subplot(gs[0, 0])
nt = ev[~ev.tidal & ev.rainy].copy()
nt["dg"] = pd.qcut(nt.max_depth_mm, 3, labels=["Shallow", "Moderate", "Deep"])
grid_t = np.linspace(0, 1, 51)
shape_stats = {}
for k, (lab, d) in enumerate(nt.groupby("dg", observed=True)):
    curves = []
    for ds_, ts_ in zip(d.flood_profile_depth_inches, d.flood_profile_time_secs):
        dd, tt = prof(ds_, ts_)
        if dd is None or len(dd) < 4 or tt.max() <= 0 or dd.max() <= 0: continue
        curves.append(np.interp(grid_t, tt / tt.max(), dd / dd.max()))
    cv = np.array(curves); med = np.median(cv, 0); q1, q3 = np.percentile(cv, [25, 75], 0)
    col = [C[2], C[0], C[6]][k]
    ax.fill_between(grid_t, q1, q3, color=col, alpha=0.15, lw=0); ax.plot(grid_t, med, color=col, lw=1.5,
                                                                         label=f"{lab} (n={len(cv)}, med {d.max_depth_mm.median():.0f} mm)")
    shape_stats[lab] = float(grid_t[np.argmax(med)])
ax.set_xlabel("Time / event duration"); ax.set_ylabel("Depth / event peak"); ax.legend(fontsize=5.3, loc="upper right")
panel(ax, "a", "Fast rise, slow recession")

# (b) peak depth vs rain intensity
ax = fig.add_subplot(gs[0, 1])
d = ev[ev.rain60 >= 0.5].dropna(subset=["rain60"])   # >= measurable 1-h rain
for tid, col, lab in [(False, C[0], "Non-tidal sensors"), (True, C[1], "Tidally influenced")]:
    x = d[d.tidal == tid]
    ax.scatter(x.rain60, x.max_depth_mm, s=3, color=col, alpha=0.45, linewidth=0, label=f"{lab} (n={len(x)})")
dn = d[~d.tidal].copy(); dn["lx"] = np.log(dn.rain60); dn["ly"] = np.log(dn.max_depth_mm)
xx = np.linspace(np.log(0.5), np.log(80), 50)
qr = {}
for q, ls in [(0.5, "-"), (0.9, "--")]:
    m = smf.quantreg("ly ~ lx", dn).fit(q=q); qr[q] = (m.params["lx"], m.bse["lx"])
    ax.plot(np.exp(xx), np.exp(m.params["Intercept"] + m.params["lx"] * xx), color=INK, lw=1, ls=ls, label=f"Quantile {int(q*100)}: slope {m.params['lx']:.2f}")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(0.4, 100); ax.set_xlabel("Max 1-h rain at nearest gauge (mm)"); ax.set_ylabel("Event peak depth (mm)")
rho_b = stats.spearmanr(dn.rain60, dn.max_depth_mm)
ax.legend(fontsize=5, loc="lower right", markerscale=2)
ax.text(0.03, 0.97, f"ρ = {rho_b[0]:.2f} (non-tidal)", transform=ax.transAxes, va="top", fontsize=5.8)
panel(ax, "b", "Peak depth vs rainfall")

# (c) J18 recession by catch-basin density
ax = fig.add_subplot(gs[0, 2])
nt["cb_g"] = pd.qcut(nt.cb_100m.rank(method="first"), 3, labels=["Few basins ≤100 m", "Middle", "Many basins ≤100 m"])
db = [10, 25, 50, 100, 200, 400, 1500]
nt["dbin"] = pd.cut(nt.max_depth_mm, db)
for k, (lab, dd) in enumerate(nt.groupby("cb_g", observed=True)):
    if lab == "Middle": continue
    t = dd.groupby("dbin", observed=True).drain_time_mins.agg(["median", "count"])
    t = t[t["count"] >= 8]
    mids = [iv.mid for iv in t.index]
    ax.plot(mids, t["median"], "-o", ms=3, color=[C[3], MUTED, C[6]][k], label=lab)
ax.set_xscale("log"); ax.set_yscale("log")
from matplotlib.ticker import FuncFormatter, NullFormatter
for axis in (ax.xaxis, ax.yaxis):
    axis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}")); axis.set_minor_formatter(NullFormatter())
ax.set_yticks([10, 20, 50, 100])
ax.set_xlabel("Event peak depth (mm)"); ax.set_ylabel("Median drain time (min)"); ax.legend(fontsize=5.3, loc="upper left")
mod18 = smf.ols("np.log(drain_time_mins) ~ np.log(max_depth_mm) + np.log1p(cb_100m) + depdepth + tpi + np.log1p(rain_win)",
                nt[(nt.drain_time_mins > 0)].dropna(subset=["depdepth", "tpi"])).fit(cov_type="cluster",
                cov_kwds={"groups": pd.factorize(nt[(nt.drain_time_mins > 0)].dropna(subset=["depdepth", "tpi"]).sensor_id)[0]})
b = mod18.params["np.log1p(cb_100m)"]; pb = mod18.pvalues["np.log1p(cb_100m)"]
ax.text(0.98, 0.04, f"log drain ~ log CB: β={b:.2f}, p={pb:.2g}\n(controls depth, sink, TPI, rain)", transform=ax.transAxes,
        ha="right", fontsize=5.2, color=INK2)
panel(ax, "c", "Recession × drainage (J18)")

# (d) sensor-level correlation matrix
ax = fig.add_subplot(gs[1, 0:2])
se2 = se[se.tidally_influenced != "Yes"].copy()
se2["inst"] = pd.to_datetime(se2.date_installed, errors="coerce", utc=True)
se2["rem"] = pd.to_datetime(se2.date_removed, errors="coerce", utc=True).fillna(pd.Timestamp("2026-11-09", tz="UTC"))
se2["yrs"] = (se2.rem - se2.inst).dt.days / 365.25
agg = nt.groupby("sensor_id").agg(n=("max_depth_mm", "size"), peak=("max_depth_mm", "median"),
                                  dur=("duration_mins", "median"), recess=("recess_rate", "median"), rise=("rise_rate", "median"))
se2 = se2.set_index("sensor_id").join(agg)
se2["n"] = se2.n.fillna(0); se2 = se2[se2.yrs >= 0.5]; se2["freq"] = se2.n / se2.yrs
outs = {"freq": "Events / yr", "peak": "Median peak depth", "dur": "Median duration", "rise": "Median rise rate", "recess": "Median recession rate"}
feats = {"elev_m": "Elevation", "tpi": "Topogr. position", "depdepth": "Sink depth", "lowest_point_height_delta_inches": "Curb-to-low-point Δh",
         "cb_nn_m": "Dist. to nearest CB", "cb_100m": "CBs within 100 m", "impervious": "Impervious (cell)", "canopy": "Canopy (cell)",
         "ms4_frac": "MS4 share", "rpl_themes": "SVI"}
R = np.full((len(outs), len(feats)), np.nan); P = R.copy()
for i, o in enumerate(outs):
    for j, f_ in enumerate(feats):
        x = se2[[o, f_]].dropna()
        if o != "freq": x = x[se2.loc[x.index, "n"] >= 3]
        if len(x) > 15:
            R[i, j], P[i, j] = stats.spearmanr(x[o], x[f_])
im = ax.imshow(R, cmap=DIV, vmin=-0.5, vmax=0.5, aspect="auto")
for i in range(R.shape[0]):
    for j in range(R.shape[1]):
        if not np.isnan(R[i, j]):
            ax.text(j, i, f"{R[i, j]:.2f}" + ("*" if P[i, j] < 0.05 / R.size * 10 else ""), ha="center", va="center", fontsize=5.5,
                    color="white" if abs(R[i, j]) > 0.35 else INK)
ax.set_xticks(range(len(feats))); ax.set_xticklabels(list(feats.values()), rotation=35, ha="right", fontsize=5.8)
ax.set_yticks(range(len(outs))); ax.set_yticklabels(list(outs.values()), fontsize=6)
cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01); cb.set_label("Spearman ρ", fontsize=6); cb.ax.tick_params(labelsize=5.5)
ax.text(0, -0.5, f"Non-tidal sensors with ≥0.5 yr record (n={len(se2)}); depth/rate metrics use sensors with ≥3 rainy events; * p<0.005",
        fontsize=5.3, color=INK2, transform=ax.transAxes)
panel(ax, "d", "Local factors vs ponding frequency, depth and rates")

# (e) J07 tide at event onset
ax = fig.add_subplot(gs[1, 2])
for k, (tid, lab) in enumerate([(False, "Non-tidal"), (True, "Tidal")]):
    for j, (rn, rl) in enumerate([(True, "rain ≥2 mm"), (False, "rain <2 mm")]):
        x = ev[(ev.tidal == tid) & (ev.rainy == rn)].tide_m.dropna()
        pos = k * 2.4 + j
        bp = ax.boxplot(x, positions=[pos], widths=0.7, showfliers=False, patch_artist=True,
                        medianprops=dict(color=INK, lw=1), whiskerprops=dict(lw=0.6), capprops=dict(lw=0.6))
        bp["boxes"][0].set(facecolor=[C[0], C[1]][k], alpha=0.35 if rn else 0.8, linewidth=0.6)
        ax.text(pos, ax.get_ylim()[0] if False else -1.15, f"n={len(x)}", ha="center", fontsize=5, color=INK2)
ax.set_xticks([0, 1, 2.4, 3.4]); ax.set_xticklabels(["Non-tidal\nrain", "Non-tidal\ndry", "Tidal\nrain", "Tidal\ndry"], fontsize=5.6)
ax.axhline(obs.quantile(0.9), color=MUTED, lw=0.6, ls="--"); ax.text(3.9, obs.quantile(0.9) + 0.04, "90th pct tide", ha="right", fontsize=5, color=INK2)
ax.set_ylabel("Battery level at onset (m)"); ax.set_ylim(-1.3, None)
mw = stats.mannwhitneyu(ev[ev.tidal & ev.rainy].tide_m.dropna(), ev[~ev.tidal & ev.rainy].tide_m.dropna())
panel(ax, "e", "Compound tide–rain (J07)")

save(fig, "fig08_floodnet")
ev.drop(columns=["flood_profile_depth_inches", "flood_profile_time_secs"]).to_parquet(TAB / "fig08_events_enriched.parquet", index=False)
pd.DataFrame(R, index=list(outs.values()), columns=list(feats.values())).to_csv(TAB / "fig08_sensor_corr.csv")
write_stats("fig08", {"n_events": len(ev), "n_tidal_events": int(ev.tidal.sum()), "share_rainy": float(ev.rainy.mean()),
                      "share_rainy_tidal": float(ev[ev.tidal].rainy.mean()), "share_rainy_nontidal": float(ev[~ev.tidal].rainy.mean()),
                      "peak_time_fraction": shape_stats, "rho_depth_rain60": rho_b[0], "quantreg_slopes": qr,
                      "drain_model": {k: [mod18.params[k], mod18.pvalues[k]] for k in mod18.params.index},
                      "tide_mw_rainy_tidal_vs_nontidal": [mw.statistic, mw.pvalue],
                      "median_onset_min": float(nt.onset_time_mins.median()), "median_drain_min": float(nt.drain_time_mins.median()),
                      "median_peak_mm": float(nt.max_depth_mm.median())})
