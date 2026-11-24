"""Build analysis-ready tables from data/raw/full into data/processed/full.

Usage: uv run python -m urban_flooding.build [step ...]
Steps: grid hydro static rain storms reports panel floodnet
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

RAW = Path("data/raw/full")
PROC = Path("data/processed/full")
CRS = "EPSG:26918"   # UTM 18N metres
CELL = 500           # analysis grid size (m)
TZ = "America/New_York"


def p(name: str) -> Path:
    PROC.mkdir(parents=True, exist_ok=True)
    return PROC / name


def boroughs() -> gpd.GeoDataFrame:
    b = gpd.read_file(RAW / "boundaries/boroughs.geojson").to_crs(CRS)
    b["geometry"] = b.geometry.make_valid()
    return b[["boroname", "geometry"]]


# ---------------------------------------------------------------- grid -----
def grid():
    b = boroughs()
    land = b.union_all()
    xmin, ymin, xmax, ymax = land.bounds
    xs = np.arange(np.floor(xmin / CELL) * CELL, xmax, CELL)
    ys = np.arange(np.floor(ymin / CELL) * CELL, ymax, CELL)
    cells = gpd.GeoDataFrame({"x0": np.repeat(xs, len(ys)), "y0": np.tile(ys, len(xs))},
                             geometry=[box(x, y, x + CELL, y + CELL) for x in xs for y in ys], crs=CRS)
    inter = gpd.overlay(cells.reset_index(names="i"), b, how="intersection", keep_geom_type=True)
    inter["a"] = inter.area
    frac = inter.groupby("i").a.sum() / CELL**2
    boro = inter.sort_values("a").groupby("i").boroname.last()
    cells["land_frac"] = frac.reindex(cells.index).fillna(0)
    cells["boro"] = boro.reindex(cells.index)
    cells = cells[cells.land_frac >= 0.10].copy()
    cells["cell_id"] = (cells["x0"] // CELL).astype(int).astype(str) + "_" + (cells["y0"] // CELL).astype(int).astype(str)
    cells["land_km2"] = cells.land_frac * CELL**2 / 1e6
    cells[["cell_id", "x0", "y0", "boro", "land_frac", "land_km2", "geometry"]].to_file(p("grid.gpkg"), driver="GPKG")
    print("grid cells", len(cells))


def load_grid() -> gpd.GeoDataFrame:
    return gpd.read_file(p("grid.gpkg"))


def cell_index(x, y) -> pd.Series:
    return pd.Series((np.floor(np.asarray(x) / CELL)).astype(int).astype(str)) + "_" + \
        pd.Series((np.floor(np.asarray(y) / CELL)).astype(int).astype(str))


def to_points(df: pd.DataFrame, lon="longitude", lat="latitude") -> gpd.GeoDataFrame:
    df = df.copy()
    df[lon] = pd.to_numeric(df[lon], errors="coerce"); df[lat] = pd.to_numeric(df[lat], errors="coerce")
    df = df[df[lon].between(-74.3, -73.6) & df[lat].between(40.45, 40.95)]
    g = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon], df[lat]), crs=4326).to_crs(CRS)
    g["x"], g["y"] = g.geometry.x, g.geometry.y
    g["cell_id"] = cell_index(g.x, g.y).values
    return g


# --------------------------------------------------------- hydrology -------
def hydro():
    """10 m DEM derivatives: filled-depression depth, slope, TPI, flow accumulation, TWI."""
    import rasterio
    from rasterio.enums import Resampling
    if not hasattr(np, "in1d"):          # pysheds 0.5 still calls the removed numpy alias
        np.in1d = lambda a, b, **k: np.isin(a, b, **k).ravel()
    from pysheds.grid import Grid
    src = RAW / "dem/dem3dep_5m.tif"
    dem10 = p("dem10.tif")
    with rasterio.open(src) as ds:
        scale = 2
        a = ds.read(1, out_shape=(ds.height // scale, ds.width // scale), resampling=Resampling.average)
        prof = ds.profile
        tr = ds.transform * ds.transform.scale(scale, scale)
        nod = ds.nodata
    a = a.astype("float32")
    a[(a < -50) | (a > 500)] = np.nan
    # Mask to the city land area; open water becomes an outlet at -10 m so the
    # depression filling drains to the coast, then is masked out of all products.
    from rasterio.features import geometry_mask
    land = ~geometry_mask(boroughs().geometry, out_shape=a.shape, transform=tr)
    a[~land] = np.nan
    outlet = np.where(np.isnan(a), -10.0, a).astype("float32")
    prof.update(height=a.shape[0], width=a.shape[1], transform=tr, nodata=-9999, dtype="float32")
    with rasterio.open(dem10, "w", **prof) as d:
        d.write(np.where(np.isnan(a), -9999, a), 1)
    tmp = p("dem10_outlet.tif")
    with rasterio.open(tmp, "w", **dict(prof, nodata=-9999)) as d:
        d.write(outlet, 1)
    g = Grid.from_raster(str(tmp))
    dem = g.read_raster(str(tmp))
    # Water/no-data treated as an outlet at sea level so the city drains to the coast.
    pits = g.fill_pits(dem)
    flooded = g.fill_depressions(pits)
    inflated = g.resolve_flats(flooded)
    fdir = g.flowdir(inflated)
    acc = g.accumulation(fdir)
    z = a.copy()
    depth = (np.asarray(flooded) - np.asarray(dem)).astype("float32")
    depth[np.isnan(z)] = np.nan
    gy, gx = np.gradient(np.where(np.isnan(z), np.nanmean(z), z), 10.0)
    slope = np.degrees(np.arctan(np.hypot(gx, gy))).astype("float32")
    from scipy.ndimage import uniform_filter
    zz = np.where(np.isnan(z), 0, z); w = (~np.isnan(z)).astype("float32")
    k = 51  # 510 m window for topographic position
    mean = uniform_filter(zz, k) / np.maximum(uniform_filter(w, k), 1e-6)
    tpi = (z - mean).astype("float32")
    tanb = np.tan(np.radians(np.maximum(slope, 0.1)))
    twi = np.log((np.asarray(acc) + 1) * 10.0 / tanb).astype("float32")
    for name, arr in [("depdepth", depth), ("slope", slope), ("tpi", tpi), ("twi", twi),
                      ("flowacc", np.log10(np.asarray(acc) + 1))]:
        arr = np.where(np.isnan(z), -9999, arr).astype("float32")
        with rasterio.open(p(f"{name}10.tif"), "w", **prof) as d:
            d.write(arr, 1)
    print("hydro done")


def zonal_grid(raster: Path, stats: dict, grid_: gpd.GeoDataFrame) -> pd.DataFrame:
    """Fast zonal stats for the regular grid: rasterise cell ids then group."""
    import rasterio
    from rasterio.features import rasterize
    with rasterio.open(raster) as ds:
        a = ds.read(1).astype("float64")
        nod = ds.nodata
        g = grid_.to_crs(ds.crs)
        ids = rasterize(zip(g.geometry, np.arange(len(g)) + 1), out_shape=a.shape, transform=ds.transform,
                        fill=0, dtype="int32")
    m = (ids > 0) & (a != nod) & np.isfinite(a)
    df = pd.DataFrame({"k": ids[m], "v": a[m]})
    out = pd.DataFrame(index=np.arange(len(g)) + 1)
    gb = df.groupby("k").v
    for col, fn in stats.items():
        out[col] = fn(gb) if callable(fn) else gb.agg(fn)
    out.index = grid_.cell_id.values
    return out


def landcover_fracs(grid_: gpd.GeoDataFrame) -> pd.DataFrame:
    import rasterio
    from rasterio.features import rasterize
    with rasterio.open(RAW / "land_cover/landcover2017_8ft.tif") as ds:
        a = ds.read(1)
        g = grid_.to_crs(ds.crs)
        ids = rasterize(zip(g.geometry, np.arange(len(g)) + 1), out_shape=a.shape, transform=ds.transform,
                        fill=0, dtype="int32")
    m = (ids > 0) & (a > 0)
    ct = np.zeros((len(g) + 1, 9))
    np.add.at(ct, (ids[m], a[m]), 1)
    names = ["", "canopy", "grass", "bare", "water", "building", "road", "other_imperv", "rail"]
    tot = ct[1:, 1:].sum(1, keepdims=True)
    fr = pd.DataFrame(ct[1:, 1:] / np.maximum(tot, 1), columns=[f"lc_{n}" for n in names[1:]], index=grid_.cell_id.values)
    land = ct[1:, 1:].sum(1) - ct[1:, 4]
    fr["impervious"] = (ct[1:, 5] + ct[1:, 6] + ct[1:, 7] + ct[1:, 8]) / np.maximum(land, 1)
    fr["green"] = (ct[1:, 1] + ct[1:, 2]) / np.maximum(land, 1)
    fr["canopy"] = ct[1:, 1] / np.maximum(land, 1)
    fr["grass"] = ct[1:, 2] / np.maximum(land, 1)
    fr["building_cov"] = ct[1:, 5] / np.maximum(land, 1)
    fr["road_frac"] = ct[1:, 6] / np.maximum(land, 1)
    return fr


def static():
    g = load_grid()
    out = pd.DataFrame(index=g.cell_id.values)
    # --- topography
    q10 = lambda gb: gb.quantile(0.10)
    out = out.join(zonal_grid(p("dem10.tif"), {"elev_mean": "mean", "elev_p10": q10, "elev_min": "min",
                                               "relief": lambda gb: gb.quantile(.95) - gb.quantile(.05)}, g))
    out = out.join(zonal_grid(p("slope10.tif"), {"slope_mean": "mean"}, g))
    out = out.join(zonal_grid(p("tpi10.tif"), {"tpi_mean": "mean", "tpi_p10": q10}, g))
    out = out.join(zonal_grid(p("twi10.tif"), {"twi_mean": "mean", "twi_p90": lambda gb: gb.quantile(.9)}, g))
    out = out.join(zonal_grid(p("depdepth10.tif"), {
        "dep_frac": lambda gb: gb.apply(lambda v: (v > 0.10).mean()),
        "dep_depth_mean": lambda gb: gb.apply(lambda v: v[v > 0.10].mean() if (v > 0.10).any() else 0.0),
        "dep_depth_max": "max"}, g))
    # --- land cover
    out = out.join(landcover_fracs(g))
    # --- distance to shoreline (borough boundaries are shoreline-clipped)
    shore = boroughs().boundary.union_all()
    cent = g.geometry.centroid
    out["dist_shore_m"] = cent.distance(shore).values
    # --- PLUTO
    pl = to_points(pd.read_parquet(RAW / "pluto/pluto.parquet"))
    for c in ["lotarea", "bldgarea", "numfloors", "builtfar", "yearbuilt", "unitsres"]:
        pl[c] = pd.to_numeric(pl[c], errors="coerce")
    pl["landuse"] = pd.to_numeric(pl.landuse, errors="coerce")
    agg = pl.groupby("cell_id").agg(lots=("bbl", "size"), lotarea=("lotarea", "sum"), bldgarea=("bldgarea", "sum"),
                                    floors_mean=("numfloors", "mean"), units_res=("unitsres", "sum"))
    agg["far_cell"] = agg.bldgarea / agg.lotarea.replace(0, np.nan)
    yb = pl[pl.yearbuilt > 1800].groupby("cell_id").yearbuilt.median().rename("yearbuilt_med")
    # Land-use groups (DCP codes): 1-3 residential, 4 mixed, 5 commercial, 6 industrial, 7 transport/util,
    # 8 public facilities, 9 open space, 10 parking, 11 vacant.
    grp = {1: "res", 2: "res", 3: "res", 4: "mixed", 5: "comm", 6: "ind", 7: "transp", 8: "public",
           9: "open", 10: "parking", 11: "vacant"}
    pl["lu"] = pl.landuse.map(grp)
    lu = pl.pivot_table(index="cell_id", columns="lu", values="lotarea", aggfunc="sum").fillna(0)
    lu = lu.div(lu.sum(1), axis=0).add_prefix("lu_")
    out = out.join(agg[["lots", "far_cell", "floors_mean", "units_res"]]).join(yb).join(lu)
    lucols = [c for c in out if c.startswith("lu_")]
    has = out[lucols].notna().any(axis=1)
    out["lu_dominant"] = None
    out.loc[has, "lu_dominant"] = out.loc[has, lucols].idxmax(axis=1).str.replace("lu_", "")
    # --- catch basins
    cb = to_points(pd.read_parquet(RAW / "catch_basins/catch_basins.parquet"))
    out["cb_count"] = cb.cell_id.value_counts().reindex(out.index).fillna(0)
    land_km2 = g.set_index("cell_id").land_km2
    out["cb_density"] = out.cb_count / land_km2
    road_km2 = out.road_frac * land_km2
    out["cb_per_road_ha"] = out.cb_count / (road_km2 * 100).replace(0, np.nan)
    # mean distance from 50 m lattice points inside each cell to nearest catch basin
    from scipy.spatial import cKDTree
    tree = cKDTree(np.c_[cb.x, cb.y])
    offs = np.arange(25, CELL, 50)
    ox, oy = np.meshgrid(offs, offs)
    xs = (g["x0"].values[:, None] + ox.ravel()[None, :]); ys = (g["y0"].values[:, None] + oy.ravel()[None, :])
    dist, _ = tree.query(np.c_[xs.ravel(), ys.ravel()])
    out["cb_nn_dist_m"] = dist.reshape(xs.shape).mean(1)
    # --- green infrastructure (constructed assets)
    gi = to_points(pd.read_parquet(RAW / "green_infra/gi_points.parquet"))
    gi = gi[gi.status_gro.fillna("").str.contains("Constructed|Complete", case=False)]
    out["gi_count"] = gi.cell_id.value_counts().reindex(out.index).fillna(0)
    out["gi_density"] = out.gi_count / land_km2
    # --- MS4 drainage areas
    ms4 = ms4_layer()
    if ms4 is not None:
        inter = gpd.overlay(g[["cell_id", "geometry"]], ms4[["geometry"]], how="intersection", keep_geom_type=True)
        out["ms4_frac"] = (inter.assign(a=inter.area).groupby("cell_id").a.sum() / (land_km2 * 1e6)).reindex(out.index).fillna(0).clip(0, 1)
    # --- stormwater flood maps
    sw = stormwater_layers()
    for name, layer in sw.items():
        inter = gpd.overlay(g[["cell_id", "geometry"]], layer[["geometry"]], how="intersection", keep_geom_type=True)
        out[f"swm_{name}"] = (inter.assign(a=inter.area).groupby("cell_id").a.sum() / (land_km2 * 1e6)).reindex(out.index).fillna(0).clip(0, 1)
    # --- census (area-weighted)
    out = out.join(census_to_grid(g))
    # --- facilities
    fac = to_points(pd.read_parquet(RAW / "facilities/facdb.parquet"))
    hosp = fac[fac.factype.fillna("").str.contains("HOSPITAL", case=False)]
    sch = fac[fac.facsubgrp.fillna("").str.contains("SCHOOLS", case=False) & fac.facgroup.fillna("").str.contains("SCHOOLS|EDUCATION", case=False)]
    sub = to_points(pd.read_parquet(RAW / "facilities/subway_stations.parquet"), "gtfs_longitude", "gtfs_latitude")
    sub = sub[sub.structure.fillna("").str.contains("Subway|Open Cut", case=False)]
    for n, d in [("hospitals", hosp), ("schools", sch), ("subway_ug", sub)]:
        out[f"n_{n}"] = d.cell_id.value_counts().reindex(out.index).fillna(0)
    out.index.name = "cell_id"
    out.reset_index().to_parquet(p("static.parquet"), index=False)
    print("static", out.shape)


def ms4_layer():
    import zipfile, pyogrio
    z = RAW / "ms4/MS4OpenData.gdb.zip"
    if not z.exists():
        return None
    d = RAW / "ms4/unzipped"
    if not d.exists():
        zipfile.ZipFile(z).extractall(d)
    gdb = next(d.rglob("*.gdb"))
    layers = [l[0] for l in pyogrio.list_layers(gdb)]
    lay = [l for l in layers if "drain" in l.lower() and "area" in l.lower()] or [l for l in layers if "area" in l.lower()]
    m = gpd.read_file(gdb, layer=lay[0]).to_crs(CRS)
    m["geometry"] = m.geometry.make_valid()
    return gpd.GeoDataFrame(geometry=[m.union_all()], crs=CRS)


def stormwater_layers() -> dict:
    """NYC Stormwater Flood Map scenarios -> {scenario_class: polygons}.

    Flooding_Category 1 = nuisance (4 in-1 ft), 2 = deep & contiguous (>1 ft),
    3 = future high-tide flooding (excluded: not pluvial). GDBs that use the
    unsupported CDF compression are skipped and reported.
    """
    import zipfile, pyogrio, re
    z = RAW / "stormwater_maps/stormwater_flood_maps.zip"
    if not z.exists():
        return {}
    d = RAW / "stormwater_maps/unzipped"
    if not d.exists():
        zipfile.ZipFile(z).extractall(d)
    cache = p("stormwater_layers.gpkg")
    if cache.exists():
        return {l: gpd.read_file(cache, layer=l) for l in [l[0] for l in pyogrio.list_layers(cache)]}
    out = {}
    for gdb in sorted(d.rglob("*.gdb")):
        name = gdb.name.lower()
        scen = "limited" if "limited" in name else "moderate" if "moderate" in name else "extreme"
        try:
            lay = pyogrio.list_layers(gdb)[0][0]
            m = gpd.read_file(gdb, layer=lay).to_crs(CRS)
        except Exception as e:
            print("  stormwater map unreadable:", gdb.name, type(e).__name__)
            continue
        m["geometry"] = m.geometry.force_2d().make_valid()
        for cat, lab in [(1, "nuisance"), (2, "deep")]:
            sub = m[m.Flooding_Category == cat]
            if len(sub):
                k = f"{scen}_{lab}"
                out[k] = gpd.GeoDataFrame(geometry=sub.geometry.values, crs=CRS)
                out[k].to_file(cache, layer=k, driver="GPKG")
    return out


def census_to_grid(g: gpd.GeoDataFrame) -> pd.DataFrame:
    """Area-weighted tract socio-economic variables (ACS 2018-22 estimates carried in CDC SVI 2022).

    The Census API was unreachable (HTTP 403), so counts come from the SVI file's E_* fields.
    """
    tr = gpd.read_file(RAW / "boundaries/tracts2020.geojson").to_crs(CRS)
    svi = pd.read_csv(RAW / "census/svi2022_ny.csv", dtype={"FIPS": str}, encoding="utf-8-sig")
    keep = ["FIPS", "E_TOTPOP", "E_HH", "E_POV150", "E_AGE65", "E_NOVEH", "E_MINRTY", "E_DISABL",
            "RPL_THEMES", "RPL_THEME1", "RPL_THEME2", "RPL_THEME3", "RPL_THEME4"]
    svi = svi[keep].replace(-999, np.nan)
    tr = tr.merge(svi, left_on="geoid", right_on="FIPS", how="left")
    tr["tract_area"] = tr.area
    tr.to_file(p("tracts.gpkg"), driver="GPKG")
    inter = gpd.overlay(g[["cell_id", "geometry"]], tr, how="intersection", keep_geom_type=True)
    inter["w"] = inter.area / inter.tract_area
    cnt = ["E_TOTPOP", "E_HH", "E_POV150", "E_AGE65", "E_NOVEH", "E_MINRTY", "E_DISABL"]
    s = inter[cnt].multiply(inter.w, axis=0).assign(cell_id=inter.cell_id).groupby("cell_id").sum()
    out = pd.DataFrame(index=s.index)
    out["pop"] = s.E_TOTPOP
    den = s.E_TOTPOP.replace(0, np.nan)
    out["poverty_rate"] = s.E_POV150 / den          # share below 150% of poverty line
    out["noveh_rate"] = s.E_NOVEH / s.E_HH.replace(0, np.nan)
    out["pop65_rate"] = s.E_AGE65 / den
    out["minority_rate"] = s.E_MINRTY / den
    out["disab_rate"] = s.E_DISABL / den
    inter["aw"] = inter.area
    for c in ["RPL_THEMES", "RPL_THEME1", "RPL_THEME2", "RPL_THEME3", "RPL_THEME4"]:
        v = inter[[c, "aw", "cell_id"]].dropna()
        out[c.lower()] = (v[c] * v.aw).groupby(v.cell_id).sum() / v.aw.groupby(v.cell_id).sum()
    return out


# ---------------------------------------------------------- rainfall -------
STATIONS = {"NYC": (40.7790, -73.9693), "LGA": (40.7794, -73.8803), "JFK": (40.6386, -73.7622),
            "EWR": (40.6825, -74.1694), "TEB": (40.8501, -74.0608)}


def rain():
    """Hourly precipitation (mm) per station, UTC hour-ending, on a complete index."""
    a = pd.read_parquet(RAW / "asos/asos_hourly.parquet")
    a.columns = [c.lower() for c in a.columns]
    tcol = [c for c in a.columns if "valid" in c][0]
    pcol = [c for c in a.columns if "precip" in c][0]
    a["t"] = pd.to_datetime(a[tcol], utc=True)
    a["p_mm"] = pd.to_numeric(a[pcol], errors="coerce") * 25.4
    w = a.pivot_table(index="t", columns="station", values="p_mm", aggfunc="sum")
    idx = pd.date_range("2010-01-01", "2026-11-01", freq="h", tz="UTC", inclusive="left")
    w = w.reindex(idx)
    w.index.name = "t"
    # 2010-2012: the IEM hourly product omits many hours. Fill from routine METAR p01i
    # (hh:51 report = accumulation for the hour ending at hh+1). A routine METAR with no
    # precipitation group ('M') is taken as zero, as automated ASOS omit the group when dry.
    mf = RAW / "asos/asos_p01i_2010_2012.parquet"
    if mf.exists():
        m = pd.read_parquet(mf)
        m["t"] = pd.to_datetime(m.valid, utc=True)
        m = m[m.t.dt.minute.between(45, 59)].copy()
        m["p_mm"] = pd.to_numeric(m.p01i.replace("M", 0), errors="coerce").fillna(0) * 25.4
        m["t"] = m.t.dt.ceil("h")
        mp = m.pivot_table(index="t", columns="station", values="p_mm", aggfunc="max")
        both = w.loc["2012-03-01":"2012-12-31", "LGA"].dropna().index.intersection(mp.index)
        if len(both):
            print("  p01i vs hourly (LGA 2012, overlap) r =",
                  round(np.corrcoef(w.loc[both, "LGA"], mp.loc[both, "LGA"])[0, 1], 3), "n =", len(both))
        early = w.index < pd.Timestamp("2013-01-01", tz="UTC")
        for st in mp.columns:
            fill = mp[st].reindex(w.index[early])
            w.loc[early, st] = w.loc[early, st].fillna(fill)
    # City series: mean of the three in-city stations, falling back to EWR/TEB if all missing.
    city = w[["NYC", "LGA", "JFK"]].mean(axis=1)
    city = city.fillna(w[["EWR", "TEB"]].mean(axis=1))
    w["city"] = city
    w.reset_index().to_parquet(p("rain_hourly.parquet"), index=False)
    print("rain hourly", w.shape, w.notna().mean().round(3).to_dict())

    # 1-minute ASOS: 15-min and 60-min peak intensity per hour
    files = sorted((RAW / "asos").glob("asos1min_*.parquet"))
    if files:
        frames = []
        for f in files:
            d = pd.read_parquet(f)
            d.columns = [c.lower() for c in d.columns]
            if d.empty:
                continue
            tc = [c for c in d.columns if c.startswith("valid")][0]
            d["t"] = pd.to_datetime(d[tc], utc=True)
            d["p"] = pd.to_numeric(d["precip"], errors="coerce") * 25.4
            frames.append(d[["station", "t", "p"]])
        m = pd.concat(frames)
        m = m.pivot_table(index="t", columns="station", values="p", aggfunc="sum")
        m = m.reindex(pd.date_range(m.index.min().floor("h"), m.index.max().ceil("h"), freq="min", tz="UTC"))
        r15 = m.rolling(15, min_periods=12).sum()
        hourly15 = r15.resample("h", label="right", closed="right").max()
        hourly15["city"] = hourly15[["NYC", "LGA", "JFK"]].max(axis=1)
        hourly15.index.name = "t"
        hourly15.reset_index().to_parquet(p("rain_peak15_hourly.parquet"), index=False)
        print("15-min peaks", hourly15.shape)


def storms():
    """Storm events from city hourly precipitation: wet hours separated by >=6 dry hours, total >= 2.5 mm."""
    w = pd.read_parquet(p("rain_hourly.parquet")).set_index("t")
    r = w.city.fillna(0)
    wet = r > 0.2
    # gap-based grouping
    grp = (wet & ~wet.shift(1, fill_value=False)).cumsum()
    dry_run = (~wet).groupby(wet.cumsum()).cumcount()
    # merge events separated by fewer than 6 dry hours
    eid = np.zeros(len(r), int); cur = 0; last_wet = None
    for i, (is_wet, t) in enumerate(zip(wet.values, r.index)):
        if is_wet:
            if last_wet is None or (i - last_wet) > 6:
                cur += 1
            eid[i] = cur; last_wet = i
    ev = pd.DataFrame({"t": r.index, "p": r.values, "eid": eid})
    ev = ev[ev.eid > 0]
    pk15 = None
    if p("rain_peak15_hourly.parquet").exists():
        pk15 = pd.read_parquet(p("rain_peak15_hourly.parquet")).set_index("t").city
    rows = []
    cum = r.cumsum()
    for k, e in ev.groupby("eid"):
        t0, t1 = e.t.min() - pd.Timedelta(hours=1), e.t.max()
        tot = e.p.sum()
        if tot < 2.5:
            continue
        st = {s: w.loc[e.t, s].sum(min_count=1) for s in ["NYC", "LGA", "JFK", "EWR", "TEB"]}
        a72 = r.loc[t0 - pd.Timedelta(hours=72): t0].sum()
        a7d = r.loc[t0 - pd.Timedelta(days=7): t0].sum()
        rows.append({"eid": k, "start": t0, "end": t1, "dur_h": (t1 - t0) / pd.Timedelta(hours=1), "total_mm": tot,
                     "max1h_mm": e.p.max(), "max3h_mm": e.set_index("t").p.rolling(3, min_periods=1).sum().max(),
                     "max6h_mm": e.set_index("t").p.rolling(6, min_periods=1).sum().max(),
                     "ante72_mm": a72, "ante7d_mm": a7d,
                     "peak15_mm": pk15.reindex(e.t).max() if pk15 is not None else np.nan,
                     **{f"tot_{s}": v for s, v in st.items()},
                     "spatial_cv": np.nanstd(list(st.values())[:3]) / max(np.nanmean(list(st.values())[:3]), 0.1)})
    s = pd.DataFrame(rows)
    # tide during event (Battery observed max, and surge = obs - prediction)
    tf = RAW / "tides/battery_hourly.parquet"
    if tf.exists():
        td = pd.read_parquet(tf); td["t"] = pd.to_datetime(td.t, utc=True); td["v"] = pd.to_numeric(td.v, errors="coerce")
        td = td.pivot_table(index="t", columns="product", values="v")
        s["tide_max_m"] = [td.hourly_height.loc[a:b].max() for a, b in zip(s.start, s.end)]
        s["surge_max_m"] = [(td.hourly_height - td.predictions).loc[a:b].max() for a, b in zip(s.start, s.end)]
    s.to_parquet(p("storms.parquet"), index=False)
    print("storms", len(s), s.total_mm.describe().round(1).to_dict())


# ----------------------------------------------------------- 311 -----------
def reports():
    f = sorted((RAW / "nyc311").glob("flood311_*.parquet"))
    df = pd.concat([pd.read_parquet(x) for x in f]).drop_duplicates("unique_key")
    df["created_local"] = pd.to_datetime(df.created_date, errors="coerce")
    df["t"] = df.created_local.dt.tz_localize(TZ, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    lab = {"Street Flooding (SJ)": "street_flooding", "Catch Basin Clogged/Flooding (Use Comments) (SC)": "catch_basin",
           "Sewer Backup (Use Comments) (SA)": "sewer_backup", "Manhole Overflow (Use Comments) (SA1)": "manhole_overflow",
           "Highway Flooding (SH)": "highway_flooding"}
    df["kind"] = df.descriptor.map(lab)
    n0 = len(df)
    g = to_points(df)
    g = g[g.t.notna()]
    grid_ids = set(load_grid().cell_id)
    g["in_grid"] = g.cell_id.isin(grid_ids)
    out = pd.DataFrame(g.drop(columns="geometry"))
    out.to_parquet(p("reports.parquet"), index=False)
    audit = {"rows_raw": n0, "with_valid_coords_time": len(g), "in_grid": int(g.in_grid.sum()),
             "by_kind": out.kind.value_counts().to_dict(), "by_year": out.t.dt.year.value_counts().sort_index().to_dict()}
    json.dump(audit, open(p("reports_audit.json"), "w"), indent=2, default=str)
    print(audit)


def panel():
    """Cell x storm panel (street-flooding reports during storm + 12 h)."""
    g = load_grid()
    s = pd.read_parquet(p("storms.parquet"))
    r = pd.read_parquet(p("reports.parquet"))
    r = r[r.in_grid & (r.kind == "street_flooding")].sort_values("t")
    s = s.sort_values("start")
    # assign each report to the storm whose window [start, end+12h] contains it
    win_end = s.end + pd.Timedelta(hours=12)
    idx = np.searchsorted(s.start.values, r.t.values, side="right") - 1
    ok = (idx >= 0)
    idx2 = np.where(ok, idx, 0)
    ok &= r.t.values <= win_end.values[idx2]
    r = r[ok].assign(eid=s.eid.values[idx2[ok]])
    cnt = r.groupby(["eid", "cell_id"]).size().rename("n_reports").reset_index()
    # only storms after 2010-01-04 (antecedent available)
    pan = pd.MultiIndex.from_product([s.eid, g.cell_id], names=["eid", "cell_id"]).to_frame(index=False)
    pan = pan.merge(cnt, on=["eid", "cell_id"], how="left").fillna({"n_reports": 0})
    pan["n_reports"] = pan.n_reports.astype("int16")
    pan.to_parquet(p("panel_storm_cell.parquet"), index=False)
    s.merge(r.groupby("eid").size().rename("n_reports_city"), on="eid", how="left").fillna({"n_reports_city": 0}) \
        .to_parquet(p("storms.parquet"), index=False)
    print("panel", pan.shape, "positives", (pan.n_reports > 0).sum(), "reports assigned", len(r))


# ---------------------------------------------------------- FloodNet --------
def floodnet():
    ev = pd.read_parquet(RAW / "floodnet/events.parquet")
    se = pd.read_parquet(RAW / "floodnet/sensors.parquet")
    for c in ["max_depth_inches", "onset_time_mins", "drain_time_mins", "duration_mins",
              "duration_above_4_inches_mins", "duration_above_12_inches_mins"]:
        ev[c] = pd.to_numeric(ev[c], errors="coerce")
    # FloodNet timestamps are UTC ISO strings
    for c in ["flood_start_time", "flood_end_time"]:
        t = pd.to_datetime(ev[c], errors="coerce")
        ev[c] = t.dt.tz_localize("UTC") if t.dt.tz is None else t.dt.tz_convert("UTC")
    ev["max_depth_mm"] = ev.max_depth_inches * 25.4
    sg = to_points(se)
    import rasterio
    with rasterio.open(p("dem10.tif")) as ds:
        sg["elev_m"] = [v[0] for v in ds.sample(zip(sg.x, sg.y))]
    with rasterio.open(p("tpi10.tif")) as ds:
        sg["tpi"] = [v[0] for v in ds.sample(zip(sg.x, sg.y))]
    with rasterio.open(p("depdepth10.tif")) as ds:
        sg["depdepth"] = [v[0] for v in ds.sample(zip(sg.x, sg.y))]
    cb = to_points(pd.read_parquet(RAW / "catch_basins/catch_basins.parquet"))
    from scipy.spatial import cKDTree
    tree = cKDTree(np.c_[cb.x, cb.y])
    sg["cb_nn_m"] = tree.query(np.c_[sg.x, sg.y])[0]
    sg["cb_100m"] = [len(i) for i in tree.query_ball_point(np.c_[sg.x, sg.y], 100)]
    st = pd.read_parquet(p("static.parquet")).set_index("cell_id")
    sg = sg.join(st[["impervious", "green", "canopy", "building_cov", "rpl_themes", "pop", "minority_rate",
                     "poverty_rate", "ms4_frac"]], on="cell_id")
    sg.drop(columns="geometry").to_parquet(p("floodnet_sensors.parquet"), index=False)
    ev.to_parquet(p("floodnet_events.parquet"), index=False)
    print("floodnet", len(ev), "events", len(sg), "sensors")


STEPS = {"grid": grid, "hydro": hydro, "static": static, "rain": rain, "storms": storms,
         "reports": reports, "panel": panel, "floodnet": floodnet}

if __name__ == "__main__":
    for s in sys.argv[1:] or list(STEPS):
        print(f"== {s}", flush=True)
        STEPS[s]()
