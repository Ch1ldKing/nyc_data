"""Fig. 1 - Where and when NYC street flooding is reported (311 x ASOS x FloodNet x census)."""
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from scipy import stats
from .common import *  # noqa

style()
g = cell_table()
r = reports(None)
r["local"] = r.t.dt.tz_convert("America/New_York")
r["year"] = r.local.dt.year
sj = r[r.kind == "street_flooding"].copy()
rain = pd.read_parquet(PROC / "rain_hourly.parquet").set_index("t")
rain_l = rain.city.copy(); rain_l.index = rain_l.index.tz_convert("America/New_York")
s = storms()
sens = pd.read_parquet(PROC / "floodnet_sensors.parquet")
ev = pd.read_parquet(PROC / "floodnet_events.parquet")
years = range(2010, 2026)  # complete years

fig = plt.figure(figsize=(7.2, 8.6))
gs = fig.add_gridspec(4, 3, height_ratios=[1.55, 0.8, 0.9, 0.75], hspace=0.62, wspace=0.55)

# (a) map ---------------------------------------------------------------
ax = fig.add_subplot(gs[0, :2])
basemap(ax)
g["yr_km2"] = g.all_reports / g.land_km2 / (len(years) + 10 / 12)
gg = g[g.yr_km2 > 0]
gg.plot(ax=ax, column="yr_km2", cmap=SEQ_HOT, norm=LogNorm(0.3, 30), linewidth=0, zorder=1)
sg = gpd.GeoDataFrame(sens, geometry=gpd.points_from_xy(sens.x, sens.y), crs="EPSG:26918")
sg.plot(ax=ax, marker="o", markersize=5, facecolor="none", edgecolor=C[0], linewidth=0.6, zorder=3)
st = gpd.GeoDataFrame({"n": ["NYC", "LGA", "JFK", "EWR", "TEB"]},
                      geometry=gpd.points_from_xy([-73.9693, -73.8803, -73.7622, -74.1694, -74.0608],
                                                  [40.779, 40.7794, 40.6386, 40.6825, 40.8501]), crs=4326).to_crs("EPSG:26918")
st.plot(ax=ax, marker="^", markersize=26, color=INK, edgecolor="white", linewidth=0.6, zorder=4)
for _, row in st.iterrows():
    ax.annotate(row.n, (row.geometry.x, row.geometry.y), xytext=(4, 3), textcoords="offset points", fontsize=6, color=INK)
ax.set_xlim(560000, 612000); ax.set_ylim(4482000, 4532000)
scalebar(ax, 565000, 4485000)
sm = plt.cm.ScalarMappable(norm=LogNorm(0.3, 30), cmap=SEQ_HOT)
cax = ax.inset_axes([0.0, 0.84, 0.24, 0.025])
cb = fig.colorbar(sm, cax=cax, orientation="horizontal"); cax.xaxis.set_label_position("top")
cb.set_label("Street-flooding reports km⁻² yr⁻¹", fontsize=6); cb.ax.tick_params(labelsize=5.5)
ax.scatter([], [], marker="o", facecolor="none", edgecolor=C[0], s=10, label=f"FloodNet sensor (n={len(sens)})")
ax.scatter([], [], marker="^", color=INK, s=18, label="ASOS rain gauge")
ax.legend(loc="lower right", fontsize=6)
panel(ax, "a", "311 street-flooding reports, 2010–2026 (500 m grid)", x=-0.01, y=0.985)

# (b) borough small multiples --------------------------------------------
pop = g.groupby("boro").pop.sum(); area = g.groupby("boro").land_km2.sum()
nyr = len(years) + 10 / 12
b_rep = g.groupby("boro").all_reports.sum()
s_heavy = s[s.max1h_mm >= 12].eid
pan = panel_df(); pan = pan[pan.eid.isin(s_heavy)].merge(g[["cell_id", "boro"]], on="cell_id")
p_heavy = pan.assign(hit=pan.n_reports > 0).groupby("boro").hit.mean()
evs = ev.merge(sens[["sensor_id", "borough"]], on="sensor_id", how="left")
dep = evs.groupby("borough").max_depth_mm.median()
order = ["Manhattan", "Bronx", "Brooklyn", "Queens", "Staten Island"]
metrics = [("Reports km⁻² yr⁻¹", b_rep / area / nyr), ("Reports per 10k residents yr⁻¹", b_rep / pop * 1e4 / nyr),
           ("P(cell reports | storm ≥12 mm h⁻¹)", p_heavy), ("FloodNet median event peak (mm)", dep)]
a = fig.add_subplot(gs[0, 2])
M = pd.concat([v.reindex(order) for _, v in metrics], axis=1)
Mn = (M - M.min()) / (M.max() - M.min())
a.imshow(Mn.values, cmap=SEQ, vmin=-0.15, vmax=1.25, aspect="auto")
for i in range(5):
    for j in range(4):
        val = M.iloc[i, j]
        a.text(j, i, f"{val:.3f}" if val < 0.1 else (f"{val:.1f}" if val < 10 else f"{val:.0f}"), ha="center", va="center",
               fontsize=6, color="white" if Mn.iloc[i, j] > 0.6 else INK)
a.set_yticks(range(5)); a.set_yticklabels(order, fontsize=6)
a.set_xticks(range(4)); a.set_xticklabels(["Reports\nkm⁻² yr⁻¹", "Reports per\n10k res. yr⁻¹", "P(cell hit |\nstorm ≥12 mm h⁻¹)",
                                           "FloodNet\nmedian peak (mm)"], fontsize=5.5, rotation=90)
a.tick_params(length=0); [sp.set_visible(False) for sp in a.spines.values()]
a.xaxis.tick_top()
panel(a, "b", None, x=-0.05, y=1.33)
a.text(0.5, -0.06, "Borough contrasts (shade = column-scaled)", transform=a.transAxes, ha="center", va="top", fontsize=6, color=INK2)

# (c) annual counts by kind ---------------------------------------------
ax = fig.add_subplot(gs[1, :])
kinds = ["street_flooding", "catch_basin", "sewer_backup", "manhole_overflow"]
klab = {"street_flooding": "Street flooding", "catch_basin": "Catch basin clogged/flooding",
        "sewer_backup": "Sewer backup", "manhole_overflow": "Manhole overflow"}
yc = r[r.year.isin(years)].groupby(["year", "kind"]).size().unstack().reindex(columns=kinds).fillna(0) / 1000
bottom = np.zeros(len(yc))
for i, k in enumerate(kinds):
    ax.bar(yc.index, yc[k], bottom=bottom, color=C[i], width=0.78, label=klab[k], edgecolor="white", linewidth=0.6)
    bottom += yc[k].values
ax.set_ylabel("Reports (thousands)")
ax.set_xticks(list(years)); ax.set_xticklabels([str(y)[2:] if y % 2 else str(y) for y in years], fontsize=6)
yr = s[s.start.dt.year.isin(years)].groupby(s.start.dt.year)
heavy = yr.apply(lambda d: (d.max1h_mm >= 20).sum())
for y in years:
    k = int(heavy.get(y, 0))
    if k:
        ax.scatter([y] * k, bottom[list(years).index(y)] + 1.2 + 1.6 * np.arange(k), marker="v", s=9, color=C[7], linewidth=0)
ax.scatter([], [], marker="v", s=9, color=C[7], label="Storm ≥20 mm h⁻¹")
ax.set_ylim(0, bottom.max() * 1.3)
ax.legend(ncol=5, loc="upper left", fontsize=5.8, bbox_to_anchor=(0, 1.08))
panel(ax, "c", "Annual flood-related 311 reports by descriptor", y=1.08)

# (d) month x hour heatmap ----------------------------------------------
ax = fig.add_subplot(gs[2, :2])
sj["m"], sj["h"] = sj.local.dt.month, sj.local.dt.hour
hm = sj.groupby(["m", "h"]).size().unstack().reindex(index=range(1, 13), columns=range(24)).fillna(0)
im = ax.imshow(hm.values, aspect="auto", cmap=SEQ_HOT, origin="upper")
ax.set_yticks(range(12)); ax.set_yticklabels(list("JFMAMJJASOND"), fontsize=6)
ax.set_xticks(range(0, 24, 3)); ax.set_xlabel("Hour of day (local)")
cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.01); cbar.set_label("Reports", fontsize=6); cbar.ax.tick_params(labelsize=5.5)
panel(ax, "d", "Street-flooding reports by month and hour")

# (e) monthly yield -----------------------------------------------------
ax = fig.add_subplot(gs[2, 2])
rl = rain_l[rain_l.index.year.isin(years)]
mrain = rl.groupby([rl.index.year.rename("year"), rl.index.month.rename("m")]).sum()
mrep = sj[sj.year.isin(years)].groupby(["year", "m"]).size()
yd = pd.DataFrame({"rep": mrep.reindex(mrain.index).fillna(0), "rain": mrain}).reset_index()
def ratio(d):
    t = d.groupby("m")[["rep", "rain"]].sum().reindex(range(1, 13))
    return (t.rep / t.rain * 100).values          # ratio of sums: robust to dry months
mean = pd.Series(ratio(yd), index=range(1, 13))
rng = np.random.default_rng(1)
boot = np.array([ratio(pd.concat([yd[yd.year == y] for y in rng.choice(list(years), len(years))])) for _ in range(500)])
lo, hi = np.nanpercentile(boot, [2.5, 97.5], axis=0)
ax.fill_between(range(1, 13), lo, hi, color=C[1], alpha=0.2, linewidth=0)
ax.plot(range(1, 13), mean.values, color=C[1], marker="o", ms=3)
ax.set_xticks(range(1, 13)); ax.set_xticklabels(list("JFMAMJJASOND"), fontsize=6)
ax.set_ylabel("Reports / 100 mm")
panel(ax, "e", "Report yield by month (95% CI, year bootstrap)")

# (f) diurnal share vs rain share --------------------------------------
ax = fig.add_subplot(gs[3, :2])
rh = rain_l.groupby(rain_l.index.hour).sum(); rh = rh / rh.sum() * 100
sh = sj.groupby("h").size(); sh = sh / sh.sum() * 100
ax.plot(rh.index, rh.values, color=MUTED, lw=1.4, label="Share of rainfall")
ax.plot(sh.index, sh.values, color=C[0], lw=1.6, label="Share of street-flooding reports")
ax.set_xticks(range(0, 24, 3)); ax.set_xlabel("Hour of day (local)"); ax.set_ylabel("% of total")
ax.legend(loc="upper left")
chi = stats.chisquare(sj.groupby("h").size().values, rh.values / 100 * len(sj))
ax.text(0.98, 0.06, f"χ² vs rain profile = {chi.statistic:.0f}, p < 1e-10" if chi.pvalue < 1e-10 else f"p={chi.pvalue:.2g}",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=6, color=INK2)
panel(ax, "f", "Diurnal timing: reports lag and under-sample night-time rain")

# (g) share of reports inside storm windows by kind ----------------------
ax = fig.add_subplot(gs[3, 2])
s2 = s.sort_values("start")
def in_storm(t):
    i = np.searchsorted(s2.start.values, t.values, side="right") - 1
    ok = i >= 0; i = np.where(ok, i, 0)
    return ok & (t.values <= (s2.end + pd.Timedelta(hours=12)).values[i])
share = {klab[k]: in_storm(r[r.kind == k].t).mean() * 100 for k in kinds}
ax.barh(range(4), list(share.values()), color=[C[i] for i in range(4)], height=0.6)
ax.set_yticks(range(4)); ax.set_yticklabels(["Street flood.", "Catch basin", "Sewer backup", "Manhole overfl."], fontsize=6)
ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("% within storm (+12 h)")
for i, v in enumerate(share.values()):
    ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=6)
panel(ax, "g", "Rain-linked share")

save(fig, "fig01_overview")

kw = stats.kruskal(*[g[g.boro == b].p_storm.dropna() for b in order])
mon = stats.chisquare(hm.sum(1).values)
write_stats("fig01", {"n_street_flood_reports": len(sj), "n_all_flood_reports": len(r),
                      "borough_rates_km2_yr": (b_rep / area / nyr).round(2).to_dict(),
                      "borough_rates_per10k_yr": (b_rep / pop * 1e4 / nyr).round(2).to_dict(),
                      "p_heavy_storm": p_heavy.round(4).to_dict(), "floodnet_median_depth_mm": dep.round(1).to_dict(),
                      "kruskal_boro_p_storm": [kw.statistic, kw.pvalue], "chisq_month_uniform": [mon.statistic, mon.pvalue],
                      "chisq_hour_vs_rain": [chi.statistic, chi.pvalue], "monthly_yield": mean.round(2).to_dict(),
                      "share_in_storm_pct": share, "annual_counts": yc.round(3).to_dict()})
yc.to_csv(TAB / "fig01_annual_counts_k.csv")
