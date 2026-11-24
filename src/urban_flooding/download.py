"""Download a small real pilot, or generate explicitly synthetic fixtures."""
import os
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import box
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .common import path, manifest, time_range

API = 'https://data.cityofnewyork.us/resource/erm2-nwe9.json'
BORO = 'https://data.cityofnewyork.us/resource/gthc-hcne.geojson'
WEATHER = 'https://archive-api.open-meteo.com/v1/archive'


def session():
    s = requests.Session()
    s.mount('https://', HTTPAdapter(max_retries=Retry(total=4, backoff_factor=1, status_forcelist=[429,500,502,503,504])))
    return s


def get(s, url, params=None):
    headers = {'X-App-Token': os.environ['SOCRATA_APP_TOKEN']} if url.startswith('https://data.cityofnewyork.us/') and os.getenv('SOCRATA_APP_TOKEN') else {}
    r = s.get(url, params=params, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()


def download(c):
    if c.mode == 'demo':
        return demo(c)
    s = session()
    # API timestamps are NYC local wall time. Retrieve a padded interval, then filter in UTC.
    a = (pd.Timestamp(c.start) - pd.Timedelta(days=1)).isoformat()
    b = (pd.Timestamp(c.end) + pd.Timedelta(days=1)).isoformat()
    where = (f"created_date >= '{a}' AND created_date < '{b}' "
             "AND upper(descriptor) like '%STREET FLOODING%'")
    select = 'unique_key,created_date,complaint_type,descriptor,latitude,longitude,borough'
    rows = []
    for offset in range(0, 10000000, 50000):
        batch = get(s, API, {'$select': select, '$where': where, '$order': 'unique_key', '$limit': 50000, '$offset': offset})
        rows.extend(batch)
        if len(batch) < 50000:
            break
    else:
        raise RuntimeError('Pagination cap reached; shorten interval.')
    if not rows:
        raise RuntimeError('No matching reports; audit API filter and date coverage.')
    df = pd.DataFrame(rows)
    if df.unique_key.duplicated().any():
        raise ValueError('Duplicate report IDs; rerun API query and inspect.')
    f1 = path(c, 'raw', 'reports.csv'); df.to_csv(f1, index=False)
    f2 = path(c, 'raw', 'boroughs.geojson')
    import json
    f2.write_text(json.dumps(get(s, BORO, {'$limit': 10})))
    if len(gpd.read_file(f2)) != 5:
        raise ValueError('Expected 5 boroughs; inspect downloaded boundary.')
    # Historical reanalysis, one city-scale reference location; not real-time observations.
    params = {'latitude': c.weather.latitude, 'longitude': c.weather.longitude,
              'start_date': (pd.Timestamp(c.start) - pd.Timedelta(days=2)).date().isoformat(),
              'end_date': pd.Timestamp(c.end).date().isoformat(), 'hourly': 'precipitation',
              'timezone': 'GMT', 'models': c.weather.model, 'precipitation_unit': 'mm'}
    w = get(s, WEATHER, params)
    if w['hourly_units']['precipitation'] != 'mm' or w.get('utc_offset_seconds') != 0:
        raise ValueError('Unexpected weather units or time zone')
    f3 = path(c, 'raw', 'weather.csv')
    pd.DataFrame(w['hourly']).rename(columns={'time':'time_utc','precipitation':'precip_mm'}).to_csv(f3, index=False)
    manifest(c, [f1,f2,f3], {'reports': {'url': API, 'filter': where}, 'boroughs': BORO,
        'weather': {'url': WEATHER, 'params': params, 'returned_latitude': w.get('latitude'), 'returned_longitude': w.get('longitude')}})


def demo(c):
    rng = np.random.default_rng(c.seed)
    size = int(c.spatial.grid_m)
    x0, y0 = 580000, 4500000
    land = gpd.GeoDataFrame({'boroname':['SYNTHETIC']}, geometry=[box(x0,y0,x0+6*size,y0+5*size)], crs=c.spatial.crs)
    f2 = path(c,'raw','boroughs.geojson'); land.to_crs(4326).to_file(f2, driver='GeoJSON')
    times = pd.date_range(pd.Timestamp(c.start, tz='UTC')-pd.Timedelta(days=2), pd.Timestamp(c.end,tz='UTC'), freq='h')
    rain = rng.gamma(2,2,len(times)) * (rng.random(len(times)) < .20)
    f3 = path(c,'raw','weather.csv'); pd.DataFrame({'time_utc':times,'precip_mm':rain}).to_csv(f3,index=False)
    cells = [(x,y) for x in range(6) for y in range(5)]
    static = pd.DataFrame([{'cell_id':f'{x0//size+x}_{y0//size+y}', 'elevation_m':float(rng.uniform(2,35)),
        'catch_basin_count':int(rng.integers(1,30)), 'green_fraction':float(rng.uniform(.1,.8)),
        'impervious_fraction':float(rng.uniform(.2,.9))} for x,y in cells])
    f4 = path(c,'raw','static_features.csv'); static.to_csv(f4,index=False)
    records=[]
    for t in time_range(c):
        r = rain[times.get_loc(t)]
        for i,(x,y) in enumerate(cells):
            p = min(.7, .012 + .035*r + .06*(static.elevation_m.iloc[i]<10))
            if rng.random()<p:
                records.append((t,x0+(x+.5)*size,y0+(y+.5)*size))
    geo = gpd.GeoDataFrame(geometry=gpd.points_from_xy([r[1] for r in records],[r[2] for r in records]),crs=c.spatial.crs).to_crs(4326)
    f1 = path(c,'raw','reports.csv')
    pd.DataFrame({'unique_key':range(len(records)), 'created_date':[r[0].tz_convert('America/New_York').tz_localize(None) for r in records],
        'complaint_type':'SYNTHETIC','descriptor':'SYNTHETIC Street Flooding','longitude':geo.geometry.x,'latitude':geo.geometry.y}).to_csv(f1,index=False)
    manifest(c,[f1,f2,f3,f4],{'all':'SYNTHETIC TEST FIXTURES; NOT NYC EVIDENCE'})
