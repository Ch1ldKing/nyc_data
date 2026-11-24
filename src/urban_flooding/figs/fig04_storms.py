"""Fig. 4 - Storm case studies: rainfall, report and sensor timing, spatial footprint, and cross-storm similarity
(ASOS x 311 x FloodNet x hotspot map)."""
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from scipy import stats
from .common import *  # noqa

style()
s = storms().set_index("eid")
rain = pd.read_parquet(PROC / "rain_hourly.parquet").set_index("t")
r = reports()
ev = pd.read_parquet(PROC / "floodnet_events.parquet")
sens = pd.read_parquet(PROC / "floodnet_sensors.parquet")
ev = ev.merge(sens[["sensor_id", "x", "y", "tidally_influenced"]], on="sensor_id", how="left")
hot = pd.read_csv(TAB / "fig02_cell_hotspots.csv")
pan = panel_df()
b = boroughs()

cases = [("2021-09-01", "Ida remnants"), ("2023-09-28", "29 Sep 2023 deluge"),
         ("2025-10-29", "30 Oct 2025 flash flood"), ("2022-12-22", "Dec 2022 coastal storm")]
def pick(day):
    d = pd.Timestamp(day, tz="America/New_York")
    c = s[(s.start.dt.tz_convert("America/New_York").dt.normalize() >= d - pd.Timedelta(days=1)) &
          (s.start.dt.tz_convert("America/New_York").dt.normalize() <= d + pd.Timedelta(days=1))]
    return c.n_reports_city.idxmax()

fig = plt.figure(figsize=(7.2, 7.9))
gs = fig.add_gridspec(4, 4, height_ratios=[0.7, 0.7, 1.1, 1.2], hspace=0.45, wspace=0.35)
bottom = gs[3, :].subgridspec(1, 2, wspace=0.55)
stc = {"NYC": C[0], "LGA": C[1], "JFK": C[2], "EWR": MUTED, "TEB": "#b9b8b2"}
case_rows = []
for k, (day, name) in enumerate(cases):
    e = pick(day); st = s.loc[e]
    t0, t1 = st.start - pd.Timedelta(hours=4), st.end + pd.Timedelta(hours=14)
    hrs = lambda t: (t - st.start) / pd.Timedelta(hours=1)
    # (row 1) hyetograph per station
    ax = fig.add_subplot(gs[0, k])
    rr = rain.loc[t0:t1]
    for stn, col in stc.items():
        ax.plot(hrs(rr.index), rr[stn], color=col, lw=1.0 if stn in ("EWR", "TEB") else 1.3, label=stn)
    ax.set_xlim(hrs(t0), hrs(t1)); ax.set_ylim(0, None)
    if k == 0:
        ax.set_ylabel("Rain (mm h⁻¹)")
    if k == 3:
        ax.legend(fontsize=5.3, loc="upper right", handlelength=1)
    loc = st.start.tz_convert("America/New_York")
    panel(ax, "abcd"[k], f"{name}", y=1.06)
    ax.text(0.02, 0.97, f"{loc:%d %b %Y}\ntotal {st.total_mm:.0f} mm\npeak {st.max1h_mm:.0f} mm h⁻¹", transform=ax.transAxes,
            fontsize=5.5, va="top", color=INK2)
    # (row 2) cumulative reports and sensors
    ax = fig.add_subplot(gs[1, k])
    rs = r[(r.t >= t0) & (r.t <= t1)].sort_values("t")
    es = ev[(ev.flood_start_time >= t0) & (ev.flood_start_time <= t1)].sort_values("flood_start_time")
    es1 = es.drop_duplicates("sensor_id")
    ax.step(hrs(rs.t), np.arange(1, len(rs) + 1) / max(len(rs), 1) * 100, where="post", color=C[1], lw=1.4, label="311 reports")
    if len(es1):
        ax.step(hrs(es1.flood_start_time), np.arange(1, len(es1) + 1) / len(es1) * 100, where="post", color=C[0], lw=1.4,
                label="FloodNet sensors flooding")
    ax.set_xlim(hrs(t0), hrs(t1)); ax.set_ylim(0, 102); ax.set_xlabel("Hours from storm start")
    if k == 0:
        ax.set_ylabel("Cumulative %"); ax.legend(fontsize=5.3, loc="lower right")
    lag_r = hrs(rs.t).median() if len(rs) else np.nan
    lag_e = hrs(es1.flood_start_time).median() if len(es1) else np.nan
    peak_h = hrs(rain.loc[st.start:st.end, "city"].idxmax())
    ax.axvline(peak_h, color=INK2, lw=0.6, ls=":")
    ax.text(0.98, 0.04 if k else 0.45, f"n={len(rs)} reports\n{len(es1)} sensors", transform=ax.transAxes, ha="right", va="bottom", fontsize=5.5, color=INK2)
    # (row 3) map
    ax = fig.add_subplot(gs[2, k]); basemap(ax, b)
    rp = gpd.GeoDataFrame(rs, geometry=gpd.points_from_xy(rs.x, rs.y), crs="EPSG:26918")
    ax.hexbin(rs.x, rs.y, gridsize=(26, 26), extent=(560000, 612000, 4482000, 4532000), mincnt=1, cmap=SEQ_HOT,
              vmin=1, vmax=12, linewidths=0, zorder=1)
    if len(es):
        mx = es.groupby("sensor_id").agg(x=("x", "first"), y=("y", "first"), d=("max_depth_mm", "max"))
        ax.scatter(mx.x, mx.y, s=np.clip(mx.d / 15, 2, 60), facecolor="none", edgecolor=C[0], linewidth=0.6, zorder=3)
    ax.set_xlim(560000, 612000); ax.set_ylim(4482000, 4532000)
    if k == 0:
        for dv in [100, 300, 600]:
            ax.scatter([], [], s=dv / 15, facecolor="none", edgecolor=C[0], linewidth=0.6, label=f"{dv} mm")
        ax.legend(title="FloodNet peak", fontsize=5.2, title_fontsize=5.4, loc="upper left", labelspacing=0.3)
    # stats per case
    cell = pan[pan.eid == e].merge(hot[["cell_id", "persistent"]], on="cell_id")
    case_rows.append({"storm": name, "eid": int(e), "start": str(loc), "total_mm": st.total_mm, "max1h_mm": st.max1h_mm,
                      "peak15_mm": st.peak15_mm, "tide_max_m": st.tide_max_m, "n_reports_window": len(rs),
                      "n_sensors": len(es1), "median_report_lag_h": lag_r, "median_sensor_onset_h": lag_e,
                      "rain_peak_h": peak_h, "share_in_persistent": cell.loc[cell.persistent, "n_reports"].sum() / max(cell.n_reports.sum(), 1),
                      "cells_hit": int((cell.n_reports > 0).sum())})
sm_ = plt.cm.ScalarMappable(cmap=SEQ_HOT, norm=plt.Normalize(1, 12))
cax = ax.inset_axes([0.55, 0.06, 0.42, 0.035]); cbr = fig.colorbar(sm_, cax=cax, orientation="horizontal")
cbr.set_label("Reports / hexagon", fontsize=5.3); cax.xaxis.set_label_position("top"); cbr.ax.tick_params(labelsize=5)

# (e) cross-storm similarity of spatial footprint
top = s[s.start >= "2010-01-04"].nlargest(14, "n_reports_city").sort_values("start")
M = pan[pan.eid.isin(top.index)].pivot(index="cell_id", columns="eid", values="n_reports").fillna(0)
M = M[top.index]
rho = M.corr(method="spearman")
off = rho.values[np.triu_indices(len(rho), 1)]
ax = fig.add_subplot(bottom[0])
im = ax.imshow(rho.values, cmap=SEQ, vmin=0, vmax=0.35)
labs = [t.tz_convert("America/New_York").strftime("%Y-%m-%d") for t in top.start]
ax.set_xticks(range(len(labs))); ax.set_xticklabels(labs, rotation=90, fontsize=5.3)
ax.set_yticks(range(len(labs))); ax.set_yticklabels(labs, fontsize=5.3)
cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02); cb.set_label(f"Spearman ρ of cell counts (median {np.median(off):.2f})", fontsize=6); cb.ax.tick_params(labelsize=5.5)
off = rho.values[np.triu_indices(len(rho), 1)]
panel(ax, "e", f"Footprint similarity, 14 largest storms")

# (f) does extreme rain spread flooding beyond usual hotspots?
ax = fig.add_subplot(bottom[1])
ps = pan.merge(hot[["cell_id", "persistent"]], on="cell_id")
agg = ps.groupby("eid").apply(lambda d: pd.Series({"n": d.n_reports.sum(), "share": d.loc[d.persistent, "n_reports"].sum() / max(d.n_reports.sum(), 1),
                                                   "cells": (d.n_reports > 0).sum()}))
agg = agg.join(s[["max1h_mm", "total_mm"]])
agg = agg[agg.n >= 20]
sc = ax.scatter(agg.max1h_mm, agg.share * 100, s=np.sqrt(agg.n) * 1.6, c=np.log10(agg.total_mm), cmap=SEQ, linewidth=0.3, edgecolor="white")
rho_s, p_s = stats.spearmanr(agg.max1h_mm, agg.share)
ax.axhline(hot.persistent.mean() * 100, color=MUTED, lw=0.6, ls="--")
ax.text(46, hot.persistent.mean() * 100 + 1, "area share of persistent cells", ha="right", fontsize=5.5, color=INK2)
ax.set_xlabel("Storm peak 1-h rainfall (mm)"); ax.set_ylabel("% of storm reports in persistent hotspots")
ax.text(0.98, 0.95, f"Spearman ρ = {rho_s:.2f}, p = {p_s:.2g}\n(storms with ≥20 reports, n={len(agg)})", transform=ax.transAxes,
        ha="right", va="top", fontsize=5.8)
cb = fig.colorbar(sc, ax=ax, fraction=0.04, pad=0.02); cb.set_label("log₁₀ storm total (mm)", fontsize=6); cb.ax.tick_params(labelsize=5.5)
panel(ax, "f", "Hotspot share vs storm intensity")

save(fig, "fig04_storms")
pd.DataFrame(case_rows).to_csv(TAB / "fig04_cases.csv", index=False)
rho.to_csv(TAB / "fig04_storm_similarity.csv")
write_stats("fig04", {"cases": case_rows, "median_rho_top14": float(np.median(off)), "share_vs_intensity": [rho_s, p_s]})
