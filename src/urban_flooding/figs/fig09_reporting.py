"""Fig. 9 - Who reports measured flooding? FloodNet events matched to 311 (x SVI x time of day x storms).
J22, J23, RQ43-48."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from scipy.spatial import cKDTree
from .common import *  # noqa

style()
ev = pd.read_parquet(TAB / "fig08_events_enriched.parquet")
ev = ev[ev.flood_start_time >= "2020-10-01"].copy()
r = reports(None)
r = r[r.kind.isin(["street_flooding", "catch_basin", "highway_flooding"])].sort_values("t")
tree = cKDTree(np.c_[r.x, r.y]); rt = r.t.values

def match(radius, before_h=1, after_h=3, kinds=None):
    idx = tree.query_ball_point(np.c_[ev.x, ev.y], radius)
    s0 = (ev.flood_start_time - pd.Timedelta(hours=before_h)).values
    s1 = (ev.flood_end_time + pd.Timedelta(hours=after_h)).values
    kk = r.kind.values
    out = np.zeros(len(ev), bool)
    for i, ii in enumerate(idx):
        if not ii: continue
        ii = np.array(ii); m = (rt[ii] >= s0[i]) & (rt[ii] <= s1[i])
        if kinds is not None: m &= np.isin(kk[ii], kinds)
        out[i] = m.any()
    return out

ev["reported"] = match(250).astype(int)
ev["reported_sj"] = match(250, kinds=["street_flooding"])
ev["local"] = ev.flood_start_time.dt.tz_convert("America/New_York")
ev["night"] = ~ev.local.dt.hour.between(7, 21)
ev["weekend"] = ev.local.dt.dayofweek >= 5
ev["svi_g"] = pd.qcut(ev.rpl_themes, 3, labels=["Low SVI", "Mid SVI", "High SVI"])
d = ev.dropna(subset=["max_depth_mm"]).copy()
d["ld"] = np.log(d.max_depth_mm)

fig = plt.figure(figsize=(7.2, 6.9))
gs = fig.add_gridspec(2, 3, hspace=0.5, wspace=0.55)
xx = np.linspace(np.log(10), np.log(1200), 60)

def logit_curve(ax, sub, col, lab):
    m = smf.logit("reported ~ ld", sub).fit(disp=0)
    X = pd.DataFrame({"ld": xx}); pr = m.get_prediction(X).summary_frame()
    ax.plot(np.exp(xx), pr.predicted * 100, color=col, lw=1.5, label=f"{lab} (n={len(sub)})")
    ax.fill_between(np.exp(xx), pr.ci_lower * 100, pr.ci_upper * 100, color=col, alpha=0.12, lw=0)
    b = pd.cut(sub.max_depth_mm, [10, 30, 60, 120, 250, 500, 2000]); t = sub.groupby(b, observed=True).reported.agg(["mean", "size"])
    ax.scatter([iv.mid for iv in t.index], t["mean"] * 100, s=np.clip(t["size"] / 4, 4, 40), color=col, linewidth=0.4, edgecolor="white", zorder=3)
    return m

# (a) J22 by SVI (non-tidal sensors, all events)
ax = fig.add_subplot(gs[0, 0])
nt = d[~d.tidal]
mods = {}
for k, (lab, sub) in enumerate(nt.groupby("svi_g", observed=True)):
    mods[lab] = logit_curve(ax, sub, [C[2], MUTED, C[6]][k], lab)
ax.set_xscale("log"); ax.set_xlabel("Measured peak depth (mm)"); ax.set_ylabel("P(≥1 nearby 311 report), %")
ax.legend(fontsize=5.4, loc="upper left"); ax.set_ylim(0, None)
panel(ax, "a", "Depth × SVI (J22)")

# (b) J23 day vs night
ax = fig.add_subplot(gs[0, 1])
for k, (nv, lab) in enumerate([(False, "Day onset (07–22 h)"), (True, "Night onset (22–07 h)")]):
    logit_curve(ax, nt[nt.night == nv], [C[3], C[0]][k], lab)
ax.set_xscale("log"); ax.set_xlabel("Measured peak depth (mm)"); ax.set_ylabel("P(≥1 nearby 311 report), %")
ax.legend(fontsize=5.4, loc="upper left"); ax.set_ylim(0, None)
panel(ax, "b", "Depth × time of day (J23)")

# (c) multivariable logit
ax = fig.add_subplot(gs[0, 2])
mm = nt.dropna(subset=["rpl_themes", "minority_rate", "pop", "rain60", "duration_mins"]).copy()
for v, src in [("z_svi", mm.rpl_themes), ("z_min", mm.minority_rate), ("z_pop", np.log1p(mm["pop"])),
               ("z_rain", np.log1p(mm.rain60)), ("z_dur", np.log(mm.duration_mins.clip(lower=1))), ("z_depth", mm.ld)]:
    mm[v] = (src - src.mean()) / src.std()
mm["night"] = mm.night.astype(int); mm["weekend"] = mm.weekend.astype(int)
lm = smf.logit("reported ~ z_depth + z_dur + z_rain + night + weekend + z_pop + z_svi + z_min", mm).fit(
    disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(mm.sensor_id)[0]})
names = {"z_depth": "Peak depth (SD)", "z_dur": "Duration (SD)", "z_rain": "1-h rain (SD)", "night": "Night onset",
         "weekend": "Weekend", "z_pop": "Population (SD)", "z_svi": "SVI (SD)", "z_min": "Minority share (SD)"}
ci = lm.conf_int(); rows = [(names[k], np.exp(lm.params[k]), np.exp(ci.loc[k, 0]), np.exp(ci.loc[k, 1]), lm.pvalues[k]) for k in names]
for i, (lab, e, lo, hi, pv) in enumerate(rows[::-1]):
    col = C[0] if lo > 1 else (C[7] if hi < 1 else MUTED)
    ax.plot([lo, hi], [i, i], color=col, lw=1.2); ax.plot(e, i, "o", color=col, ms=4)
ax.axvline(1, color=MUTED, lw=0.6); ax.set_xscale("log")
from matplotlib.ticker import FixedLocator, NullFormatter
ax.set_xlim(0.03, 5); ax.xaxis.set_major_locator(FixedLocator([0.05, 0.1, 0.25, 0.5, 1, 2, 4])); ax.set_xticklabels(["0.05", "0.1", "0.25", "0.5", "1", "2", "4"], fontsize=5.5); ax.xaxis.set_minor_formatter(NullFormatter())
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r_[0] for r_ in rows[::-1]], fontsize=6)
ax.set_xlabel("Odds ratio of being reported"); ax.text(0.02, 0.02, f"n={int(lm.nobs)} events,\n{mm.sensor_id.nunique()} sensors", transform=ax.transAxes, fontsize=5.3, color=INK2)
panel(ax, "c", "Joint reporting model")

# (d) sensitivity heatmap (RQ48)
ax = fig.add_subplot(gs[1, 0])
radii = [100, 250, 500, 1000]; afters = [1, 3, 6, 12]
deep = (d.max_depth_mm >= 100).values & (~d.tidal).values
H = np.array([[match(rd, 1, ah)[deep].mean() * 100 for ah in afters] for rd in radii])
im = ax.imshow(H, cmap=SEQ, origin="lower", vmin=0, vmax=100)
for i in range(len(radii)):
    for j in range(len(afters)):
        ax.text(j, i, f"{H[i, j]:.0f}%", ha="center", va="center", fontsize=6, color="white" if H[i, j] > 55 else INK)
ax.set_xticks(range(len(afters))); ax.set_xticklabels([f"+{a} h" for a in afters]); ax.set_xlabel("Window after flood end")
ax.set_yticks(range(len(radii))); ax.set_yticklabels([f"{r_} m" for r_ in radii]); ax.set_ylabel("Match radius")
panel(ax, "d", f"Match rate, peaks ≥100 mm (n={deep.sum()})")

# (e) storm-level agreement (RQ45)
ax = fig.add_subplot(gs[1, 1])
s = storms(); s = s[s.start >= "2020-10-01"]
st = s.sort_values("start")
idx = np.searchsorted(st.start.values, d.flood_start_time.values, side="right") - 1
ok = (idx >= 0) & (d.flood_start_time.values <= (st.end + pd.Timedelta(hours=6)).values[np.clip(idx, 0, None)])
d2 = d[ok & ~d.tidal.values].assign(eid=st.eid.values[idx[ok & ~d.tidal.values]])
per = d2.groupby("eid").agg(sensors=("sensor_id", "nunique"), depth=("max_depth_mm", "max"))
per = st.set_index("eid")[["n_reports_city", "max1h_mm"]].join(per).fillna({"sensors": 0})
# normalise by active non-tidal sensors at the time
se = pd.read_parquet(PROC / "floodnet_sensors.parquet"); se = se[se.tidally_influenced != "Yes"]
inst = pd.to_datetime(se.date_installed, utc=True, errors="coerce"); rem = pd.to_datetime(se.date_removed, utc=True, errors="coerce")
per["active"] = [((inst <= t) & (rem.isna() | (rem > t))).sum() for t in st.set_index("eid").loc[per.index, "start"]]
per["frac"] = per.sensors / per.active.replace(0, np.nan) * 100
pp = per[per.active >= 20]
sc = ax.scatter(pp.frac + 0.3, pp.n_reports_city + 1, c=pp.max1h_mm, cmap=SEQ, s=10, linewidth=0.3, edgecolor="white", vmin=0, vmax=25)
ax.set_xscale("log"); ax.set_yscale("log")
rho = stats.spearmanr(pp.frac, pp.n_reports_city)
ax.set_xlabel("% of active non-tidal sensors flooding (+0.3)"); ax.set_ylabel("311 street-flooding reports (+1)")
ax.text(0.03, 0.97, f"Spearman ρ = {rho[0]:.2f}\n{len(pp)} storms since 2020-10", transform=ax.transAxes, va="top", fontsize=5.8)
cb = fig.colorbar(sc, ax=ax, fraction=0.045, pad=0.02); cb.set_label("Peak 1-h rain (mm)", fontsize=6); cb.ax.tick_params(labelsize=5.5)
panel(ax, "e", "311 volume vs sensor flooding")

# (f) unreported deep floods: share by borough and night
ax = fig.add_subplot(gs[1, 2])
dd = nt[nt.max_depth_mm >= 100]
tab = dd.groupby(["borough", "night"]).reported.agg(["mean", "size"]).reset_index()
bor = ["Brooklyn", "Queens", "Bronx", "Manhattan", "Staten Island"]
for k, nv in enumerate([False, True]):
    t = tab[tab.night == nv].set_index("borough").reindex(bor)
    ax.barh(np.arange(len(bor)) + (k - 0.5) * 0.38, (1 - t["mean"]) * 100, height=0.36, color=[C[3], C[0]][k],
            label=["Day onset", "Night onset"][k])
    for j, (m_, n_) in enumerate(zip(t["mean"], t["size"])):
        if not np.isnan(n_): ax.text((1 - m_) * 100 + 1, j + (k - 0.5) * 0.38, f"n={int(n_)}", va="center", fontsize=4.8, color=INK2)
ax.set_yticks(range(len(bor))); ax.set_yticklabels(bor, fontsize=6); ax.invert_yaxis(); ax.set_xlim(0, 115)
ax.set_xlabel("% of ≥100 mm floods with no 311 report"); ax.legend(fontsize=5.4, loc="upper center", bbox_to_anchor=(0.4, -0.16), ncol=2)
panel(ax, "f", "Silent deep floods")

save(fig, "fig09_reporting")
pd.DataFrame(H, index=radii, columns=afters).to_csv(TAB / "fig09_sensitivity.csv")
pd.DataFrame(rows, columns=["term", "or", "lo", "hi", "p"]).to_csv(TAB / "fig09_logit.csv", index=False)
write_stats("fig09", {"n_events_matched": len(d), "match_rate_all": float(d.reported.mean()),
                      "match_rate_nontidal": float(nt.reported.mean()), "match_rate_nontidal_ge100": float(nt[nt.max_depth_mm >= 100].reported.mean()),
                      "match_rate_sj_only_nontidal_ge100": float(nt[nt.max_depth_mm >= 100].reported_sj.mean()),
                      "by_svi_ge100": nt[nt.max_depth_mm >= 100].groupby("svi_g", observed=True).reported.mean().to_dict(),
                      "by_night_ge100": nt[nt.max_depth_mm >= 100].groupby("night").reported.mean().to_dict(),
                      "logit": rows, "storm_rho": [rho[0], rho[1]], "sensitivity": H.tolist()})
