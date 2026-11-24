"""Acquire every public dataset used by the full NYC pluvial-flooding analysis.

Usage:  uv run python -m urban_flooding.acquire [name ...]

Each dataset is written under data/raw/full/<name>/ and is skipped when its
output already exists (delete the folder to refresh).  A provenance record
(URL, query, bytes, sha256, UTC time) is appended to data/raw/full/manifest.jsonl.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RAW = Path("data/raw/full")
SOCRATA = "https://data.cityofnewyork.us/resource/{}.json"
UA = {"User-Agent": "urban-flooding-research/0.1 (academic analysis)"}

# 311 flood-related descriptors (complaint_type = 'Sewer'); street flooding is the
# primary label, the others are secondary drainage-failure signals.
FLOOD_DESCRIPTORS = [
    "Street Flooding (SJ)",
    "Catch Basin Clogged/Flooding (Use Comments) (SC)",
    "Sewer Backup (Use Comments) (SA)",
    "Manhole Overflow (Use Comments) (SA1)",
    "Highway Flooding (SH)",
]


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(UA)
    s.mount("https://", HTTPAdapter(max_retries=Retry(total=6, backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504])))
    return s


S = session()


def record(name: str, files: list[Path], source: dict) -> None:
    rows = []
    for f in files:
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        rows.append({"file": str(f), "bytes": f.stat().st_size, "sha256": h})
    with (RAW / "manifest.jsonl").open("a") as fh:
        fh.write(json.dumps({"dataset": name, "utc": datetime.now(timezone.utc).isoformat(),
                             "source": source, "files": rows}) + "\n")


def socrata_all(dataset: str, params: dict, page: int = 50000) -> pd.DataFrame:
    out, offset = [], 0
    while True:
        p = dict(params, **{"$limit": page, "$offset": offset})
        r = S.get(SOCRATA.format(dataset), params=p, timeout=600)
        r.raise_for_status()
        batch = r.json()
        out.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return pd.DataFrame(out)


def done(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


# ---------------------------------------------------------------- 311 -----
def nyc311():
    d = RAW / "nyc311"; d.mkdir(parents=True, exist_ok=True)
    desc = ",".join(f"'{x}'" for x in FLOOD_DESCRIPTORS)
    select = ("unique_key,created_date,closed_date,complaint_type,descriptor,incident_zip,"
              "borough,location_type,latitude,longitude")
    files = []
    # erm2-nwe9 holds 2020-present, 76ig-c548 holds 2010-2019; query year by year.
    for year in range(2010, 2027):
        f = d / f"flood311_{year}.parquet"
        if done(f):
            files.append(f); continue
        where = (f"complaint_type='Sewer' AND descriptor in({desc}) AND "
                 f"created_date >= '{year}-01-01T00:00:00' AND created_date < '{year+1}-01-01T00:00:00'")
        ds = "erm2-nwe9" if year >= 2020 else "76ig-c548"   # 2010-2019 archive is a separate dataset
        df = socrata_all(ds, {"$select": select, "$where": where, "$order": "unique_key"})
        if df.empty:
            print(f"  311 {year}: 0 rows", flush=True); continue
        df.to_parquet(f, index=False); files.append(f)
        print(f"  311 {year}: {len(df):,} rows", flush=True)
    record("nyc311", files, {"url": [SOCRATA.format("erm2-nwe9"), SOCRATA.format("76ig-c548")], "descriptors": FLOOD_DESCRIPTORS})


# ------------------------------------------------------------ FloodNet -----
def floodnet():
    d = RAW / "floodnet"; d.mkdir(parents=True, exist_ok=True)
    f1, f2 = d / "events.parquet", d / "sensors.parquet"
    if not done(f1):
        socrata_all("aq7i-eu5q", {"$order": "flood_start_time"}, page=20000).to_parquet(f1, index=False)
    if not done(f2):
        socrata_all("kb2e-tjy3", {"$select": "sensor_name,sensor_id,date_installed,tidally_influenced,date_removed,"
                    "street_name,borough,census_tract,nta,latitude,longitude,lowest_point_height_delta_inches"}).to_parquet(f2, index=False)
    record("floodnet", [f1, f2], {"events": "aq7i-eu5q", "sensors": "kb2e-tjy3"})


# --------------------------------------------------------- point layers ----
def catch_basins():
    d = RAW / "catch_basins"; d.mkdir(parents=True, exist_ok=True); f = d / "catch_basins.parquet"
    if not done(f):
        socrata_all("2w2g-fk3i", {"$select": "unitid,latitude,longitude"}).to_parquet(f, index=False)
    record("catch_basins", [f], {"dataset": "2w2g-fk3i"})


def pluto():
    d = RAW / "pluto"; d.mkdir(parents=True, exist_ok=True); f = d / "pluto.parquet"
    if not done(f):
        sel = ("bbl,borough,landuse,bldgclass,lotarea,bldgarea,numfloors,builtfar,yearbuilt,unitsres,"
               "latitude,longitude")
        socrata_all("64uk-42ks", {"$select": sel}).to_parquet(f, index=False)
    record("pluto", [f], {"dataset": "64uk-42ks"})


def green_infra():
    d = RAW / "green_infra"; d.mkdir(parents=True, exist_ok=True); f = d / "gi_points.parquet"
    if not done(f):
        df = socrata_all("df32-vzax", {"$select": "asset_id,asset_type,status,status_gro,sewer_type,borough,"
                         "asset_area,constructed_date,the_geom"})
        df["longitude"] = df.the_geom.map(lambda g: g["coordinates"][0] if isinstance(g, dict) else None)
        df["latitude"] = df.the_geom.map(lambda g: g["coordinates"][1] if isinstance(g, dict) else None)
        df.drop(columns="the_geom").to_parquet(f, index=False)
    record("green_infra", [f], {"dataset": "df32-vzax"})


def facilities():
    d = RAW / "facilities"; d.mkdir(parents=True, exist_ok=True); f = d / "facdb.parquet"
    if not done(f):
        socrata_all("ji82-xba5", {"$select": "uid,facname,facgroup,facsubgrp,factype,boro,latitude,longitude,capacity"}).to_parquet(f, index=False)
    f2 = d / "subway_stations.parquet"
    if not done(f2):
        r = S.get("https://data.ny.gov/resource/39hk-dx4f.json", params={"$limit": 5000}, timeout=300)
        r.raise_for_status()
        pd.DataFrame(r.json()).drop(columns=["georeference"], errors="ignore").to_parquet(f2, index=False)
    record("facilities", [f, f2], {"facdb": "ji82-xba5", "subway": "data.ny.gov 39hk-dx4f"})


# ------------------------------------------------------------ polygons ------
def geojson(dataset: str, path: Path, params: dict | None = None):
    r = S.get(f"https://data.cityofnewyork.us/resource/{dataset}.geojson",
              params=dict({"$limit": 50000}, **(params or {})), timeout=600)
    r.raise_for_status(); path.write_bytes(r.content)


def boundaries():
    d = RAW / "boundaries"; d.mkdir(parents=True, exist_ok=True)
    f1, f2 = d / "boroughs.geojson", d / "tracts2020.geojson"
    if not done(f1): geojson("gthc-hcne", f1)
    if not done(f2): geojson("63ge-mke6", f2)
    record("boundaries", [f1, f2], {"boroughs": "gthc-hcne", "tracts": "63ge-mke6"})


def blob(dataset: str, path: Path):
    r = S.get(f"https://data.cityofnewyork.us/download/{dataset}/application%2Fx-zip-compressed",
              timeout=1800, stream=True)
    r.raise_for_status()
    with path.open("wb") as fh:
        for chunk in r.iter_content(1 << 20): fh.write(chunk)


def stormwater_maps():
    d = RAW / "stormwater_maps"; d.mkdir(parents=True, exist_ok=True); f = d / "stormwater_flood_maps.zip"
    if not done(f): blob("9i7c-xyvv", f)
    record("stormwater_maps", [f], {"dataset": "9i7c-xyvv"})


def ms4():
    d = RAW / "ms4"; d.mkdir(parents=True, exist_ok=True); f = d / "MS4OpenData.gdb.zip"
    if not done(f): blob("j57c-rqtq", f)
    record("ms4", [f], {"dataset": "j57c-rqtq"})


# ------------------------------------------------------- precipitation ------
ASOS = ["NYC", "LGA", "JFK", "EWR", "TEB"]


def asos_hourly():
    d = RAW / "asos"; d.mkdir(parents=True, exist_ok=True); f = d / "asos_hourly.parquet"
    if not done(f):
        frames = []
        for st in ASOS:
            net = "NJ_ASOS" if st in ("EWR", "TEB") else "NY_ASOS"
            r = S.get("https://mesonet.agron.iastate.edu/cgi-bin/request/hourlyprecip.py",
                      params={"network": net, "station": st, "year1": 2010, "month1": 1, "day1": 1,
                              "year2": 2026, "month2": 11, "day2": 1, "lalo": 1, "st": 1, "tz": "UTC"}, timeout=900)
            r.raise_for_status()
            frames.append(pd.read_csv(io.StringIO(r.text)))
            print(f"  ASOS hourly {st}: {len(frames[-1]):,}", flush=True)
        pd.concat(frames).to_parquet(f, index=False)
    record("asos_hourly", [f], {"url": "IEM hourlyprecip.py", "stations": ASOS})


def asos_metar_p01i():
    """METAR 1-h precipitation (p01i) for 2010-01 .. 2012-12, where the hourly product has gaps."""
    d = RAW / "asos"; d.mkdir(parents=True, exist_ok=True); f = d / "asos_p01i_2010_2012.parquet"
    if not done(f):
        frames = []
        for st in ASOS:
            r = S.get("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py",
                      params={"station": st, "data": "p01i", "year1": 2010, "month1": 1, "day1": 1,
                              "year2": 2013, "month2": 1, "day2": 1, "tz": "Etc/UTC", "format": "onlycomma",
                              "latlon": "no", "missing": "M", "trace": "0.0001", "report_type": [3, 4]}, timeout=900)
            r.raise_for_status()
            frames.append(pd.read_csv(io.StringIO(r.text)))
            print(f"  METAR p01i {st}: {len(frames[-1]):,}", flush=True)
        pd.concat(frames).to_parquet(f, index=False)
    record("asos_metar_p01i", [f], {"url": "IEM asos.py data=p01i", "stations": ASOS})


def asos_1min():
    """1-minute precipitation for the FloodNet era; used for sub-hourly intensity."""
    d = RAW / "asos"; d.mkdir(parents=True, exist_ok=True)
    files = []
    for st in ["NYC", "LGA", "JFK", "EWR"]:
        for year in range(2020, 2027):
            f = d / f"asos1min_{st}_{year}.parquet"
            if done(f): files.append(f); continue
            r = S.get("https://mesonet.agron.iastate.edu/cgi-bin/request/asos1min.py",
                      params={"station": st, "vars": "precip", "sts": f"{year}-01-01T00:00Z",
                              "ets": f"{year+1}-01-01T00:00Z" if year < 2026 else "2026-11-01T00:00Z",
                              "sample": "1min", "what": "download", "tz": "UTC", "delim": "comma"}, timeout=1800)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            df.to_parquet(f, index=False); files.append(f)
            print(f"  ASOS 1min {st} {year}: {len(df):,}", flush=True)
    record("asos_1min", files, {"url": "IEM asos1min.py"})


def tides():
    d = RAW / "tides"; d.mkdir(parents=True, exist_ok=True); f = d / "battery_hourly.parquet"
    if not done(f):
        frames = []
        for product in ["hourly_height", "predictions"]:
            for year in range(2010, 2027):
                params = {"station": 8518750, "product": product, "datum": "NAVD", "units": "metric",
                          "time_zone": "gmt", "format": "json", "application": "academic_research",
                          "begin_date": f"{year}0101", "end_date": f"{year}1231" if year < 2026 else "20261031"}
                if product == "predictions": params["interval"] = "h"
                r = S.get("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter", params=params, timeout=300)
                r.raise_for_status(); js = r.json()
                key = "data" if "data" in js else "predictions"
                if key not in js: print("  tides", product, year, js.get("error")); continue
                x = pd.DataFrame(js[key])[["t", "v"]]; x["product"] = product; frames.append(x)
        pd.concat(frames).to_parquet(f, index=False)
    record("tides", [f], {"station": 8518750, "datum": "NAVD"})


# -------------------------------------------------------- socioeconomic -----
def census():
    d = RAW / "census"; d.mkdir(parents=True, exist_ok=True)
    f1, f2 = d / "acs2022_tract.parquet", d / "svi2022_ny.csv"
    if not done(f1):
      try:
        vars_ = {"B01003_001E": "pop", "B19013_001E": "median_income", "B17001_002E": "poverty_n",
                 "B17001_001E": "poverty_den", "B25044_003E": "own_noveh", "B25044_010E": "rent_noveh",
                 "B25044_001E": "hh", "B01001_020E": "m65a", "B01001_021E": "m65b", "B01001_022E": "m65c",
                 "B01001_023E": "m65d", "B01001_024E": "m65e", "B01001_025E": "m65f", "B01001_044E": "f65a",
                 "B01001_045E": "f65b", "B01001_046E": "f65c", "B01001_047E": "f65d", "B01001_048E": "f65e",
                 "B01001_049E": "f65f", "B03002_003E": "nh_white", "B25003_003E": "renter_hh", "B25003_001E": "tenure_den"}
        frames = []
        for county in ["005", "047", "061", "081", "085"]:
            r = S.get("https://api.census.gov/data/2022/acs/acs5",
                      params={"get": ",".join(vars_), "for": "tract:*", "in": f"state:36 county:{county}"}, timeout=300)
            r.raise_for_status(); js = r.json()
            frames.append(pd.DataFrame(js[1:], columns=js[0]))
        df = pd.concat(frames).rename(columns=vars_)
        df["geoid"] = df.state + df.county + df.tract
        df.to_parquet(f1, index=False)
      except requests.HTTPError as e:   # api.census.gov blocks this client; SVI carries ACS-derived estimates
        print("  ACS API unavailable, using SVI estimates only:", e, flush=True)
    if not done(f2):
        r = S.get("https://svi.cdc.gov/Documents/Data/2022/csv/states/NewYork.csv", timeout=600)
        r.raise_for_status(); f2.write_bytes(r.content)
    record("census", [f for f in (f1, f2) if f.exists()], {"acs": "2022 ACS 5-year API", "svi": "CDC SVI 2022 NY tract"})


# ----------------------------------------------------------- rasters -------
NYC_BBOX_26918 = (562000, 4482000, 612000, 4532000)  # UTM18N metres, covers 5 boroughs


def dem():
    """USGS 3DEP bare-earth DEM resampled to 5 m (metres, NAVD88) via ImageServer tiles."""
    import numpy as np
    import rasterio
    from rasterio.merge import merge
    d = RAW / "dem"; d.mkdir(parents=True, exist_ok=True); out = d / "dem3dep_5m.tif"
    if done(out): return
    tiles = []
    xmin, ymin, xmax, ymax = NYC_BBOX_26918
    step, res = 10000, 5
    for x in range(xmin, xmax, step):
        for y in range(ymin, ymax, step):
            f = d / f"tile_{x}_{y}.tif"
            if not done(f):
                r = S.get("https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage",
                          params={"bbox": f"{x},{y},{x+step},{y+step}", "bboxSR": 26918, "imageSR": 26918,
                                  "size": f"{step//res},{step//res}", "format": "tiff", "pixelType": "F32",
                                  "interpolation": "RSP_BilinearInterpolation", "noDataInterpretation": "esriNoDataMatchAny",
                                  "f": "image"}, timeout=900)
                r.raise_for_status()
                if not r.content[:2] in (b"II", b"MM"):
                    raise RuntimeError(f"3DEP returned non-TIFF for tile {x},{y}: {r.content[:200]!r}")
                f.write_bytes(r.content)
            tiles.append(f)
    srcs = [rasterio.open(t) for t in tiles]
    arr, transform = merge(srcs)
    prof = srcs[0].profile; prof.update(height=arr.shape[1], width=arr.shape[2], transform=transform,
                                        compress="deflate", tiled=True, predictor=3, crs="EPSG:26918")
    with rasterio.open(out, "w", **prof) as dst: dst.write(arr)
    for s in srcs: s.close()
    for t in tiles: t.unlink()
    record("dem", [out], {"url": "USGS 3DEP ImageServer exportImage", "res_m": res, "bbox_26918": NYC_BBOX_26918})


def land_cover():
    """NYC 2017 land cover, internal overview level 3 (8 ft pixels, nearest-neighbour)."""
    import rasterio
    d = RAW / "land_cover"; d.mkdir(parents=True, exist_ok=True); out = d / "landcover2017_8ft.tif"
    if done(out): return
    url = "https://data.source.coop/betanyc/nyc-land-cover-2017/land-cover-2017/nyc-land-cover-2017.tif"
    with rasterio.Env(GDAL_HTTP_MAX_RETRY=5, GDAL_HTTP_RETRY_DELAY=3, GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(url, overview_level=3) as ds:
            a = ds.read(1); prof = ds.profile
    prof.update(driver="GTiff", height=a.shape[0], width=a.shape[1], compress="deflate", tiled=True,
                blockxsize=512, blockysize=512)
    prof.pop("photometric", None)
    with rasterio.open(out, "w", **prof) as dst: dst.write(a, 1)
    record("land_cover", [out], {"url": url, "overview_level": 3})


ALL = {f.__name__: f for f in [nyc311, floodnet, catch_basins, pluto, green_infra, facilities, boundaries,
                               stormwater_maps, ms4, asos_hourly, asos_metar_p01i, asos_1min, tides, census, dem, land_cover]}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    names = sys.argv[1:] or list(ALL)
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(ALL[n]): n for n in names}
        for fu in as_completed(futs):
            n = futs[fu]
            try:
                fu.result(); print(f"[ok] {n}", flush=True)
            except Exception as e:  # report and continue; blockers are logged
                print(f"[FAIL] {n}: {type(e).__name__}: {e}", flush=True)
                with (RAW / "blockers.log").open("a") as fh:
                    fh.write(f"{datetime.now(timezone.utc).isoformat()} {n}: {e}\n")
