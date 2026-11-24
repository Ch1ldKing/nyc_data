import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
from .common import path, time_range, write_json


def make_grid(c):
    land = gpd.read_file(path(c,'raw','boroughs.geojson')).to_crs(c.spatial.crs)
    if not land.geometry.is_valid.all():
        land.geometry = land.geometry.make_valid()
    union = land.geometry.union_all()
    size = int(c.spatial.grid_m)
    xmin,ymin,xmax,ymax = union.bounds
    ix0, iy0 = np.floor([xmin/size,ymin/size]).astype(int)
    ix1, iy1 = np.ceil([xmax/size,ymax/size]).astype(int)
    rows = []
    for x in range(ix0, ix1):
        for y in range(iy0, iy1):
            square=box(x*size,y*size,(x+1)*size,(y+1)*size)
            frac=union.intersection(square).area / size**2
            if frac >= c.spatial.min_land_fraction:
                rows.append({'cell_id':f'{x}_{y}','land_fraction':frac,'geometry':square})
    if not rows:
        raise ValueError('Empty grid')
    grid=gpd.GeoDataFrame(rows,crs=c.spatial.crs)
    grid.to_file(path(c,'processed','grid.gpkg'),driver='GPKG')
    return grid


def weather_features(c):
    df = pd.read_csv(path(c,'raw','weather.csv'))
    df['time_utc']=pd.to_datetime(df.time_utc,utc=True)
    df['precip_mm']=pd.to_numeric(df.precip_mm,errors='coerce')
    if df.time_utc.duplicated().any() or (df.precip_mm.dropna()<0).any():
        raise ValueError('Invalid weather timestamps/precipitation')
    w = df.set_index('time_utc').sort_index().asfreq('h')
    # precipitation at t is accumulation ending at t. Use lag 1 conservatively.
    for n in c.weather.windows:
        w[f'rain_{n}h']=w.precip_mm.shift(1).rolling(n,min_periods=n).sum()
    w=w.reindex(time_range(c)).drop(columns='precip_mm')
    w.index.name='time_utc'
    return w.reset_index()


def audit(c):
    df=pd.read_csv(path(c,'raw','reports.csv'))
    weather=pd.read_csv(path(c,'raw','weather.csv'))
    result={'mode':c.mode,'report_rows':len(df),'duplicate_ids':int(df.unique_key.duplicated().sum()),
            'missing_coordinates':int(df[['latitude','longitude']].isna().any(axis=1).sum()),
            'descriptors':df.descriptor.value_counts(dropna=False).to_dict(),
            'weather_rows':len(weather),'missing_precipitation':int(weather.precip_mm.isna().sum())}
    write_json(path(c,'output','audit.json'),result)
    return result


def preprocess(c):
    audit(c)
    grid=make_grid(c)
    weather=weather_features(c)
    size=int(c.spatial.grid_m)
    reports=pd.read_csv(path(c,'raw','reports.csv')).drop_duplicates('unique_key')
    t=pd.to_datetime(reports.created_date,errors='coerce',format='mixed')
    reports['time_utc']=t.dt.tz_localize('America/New_York',ambiguous='NaT',nonexistent='NaT').dt.tz_convert('UTC').dt.floor('h')
    reports['longitude']=pd.to_numeric(reports.longitude,errors='coerce')
    reports['latitude']=pd.to_numeric(reports.latitude,errors='coerce')
    reports=reports.dropna(subset=['time_utc','longitude','latitude'])
    reports=reports[reports.longitude.between(-180,180)&reports.latitude.between(-90,90)]
    reports=reports[reports.time_utc.isin(weather.time_utc)]
    pts=gpd.GeoSeries(gpd.points_from_xy(reports.longitude,reports.latitude),crs=4326).to_crs(c.spatial.crs)
    reports['cell_id']=[f'{int(np.floor(x/size))}_{int(np.floor(y/size))}' for x,y in zip(pts.x,pts.y)]
    counts=reports.groupby(['cell_id','time_utc']).size().rename('report_count').reset_index()
    n=len(grid)*len(weather)
    if n>c.model.max_rows:
        raise RuntimeError(f'{n:,} grid-hours exceeds max_rows; shorten date range or implement partitioned processing.')
    cells=grid.drop(columns='geometry')
    f=path(c,'raw','static_features.csv')
    if f.exists():
        st=pd.read_csv(f,dtype={'cell_id':str})
        allowed=[k for k in c.model.static_columns if k in st.columns]
        cells=cells.merge(st[['cell_id',*allowed]],on='cell_id',how='left',validate='one_to_one')
    panel=cells.merge(weather,how='cross').merge(counts,on=['cell_id','time_utc'],how='left',validate='one_to_one')
    panel['report_count']=panel.report_count.fillna(0).astype(int)
    panel['reported']=(panel.report_count>0).astype(int)
    local=panel.time_utc.dt.tz_convert('America/New_York')
    panel['hour_sin']=np.sin(2*np.pi*local.dt.hour/24)
    panel['hour_cos']=np.cos(2*np.pi*local.dt.hour/24)
    panel['weekend']=(local.dt.dayofweek>=5).astype(int)
    panel.to_csv(path(c,'processed','panel.csv'),index=False)
    write_json(path(c,'output','preprocessing.json'),{'mode':c.mode,'grid_cells':len(grid),'rows':len(panel),
        'reports_in_time_with_coordinates':len(reports),'matched_reports':int(panel.report_count.sum()),
        'positive_grid_hours':int(panel.reported.sum()), 'missing_rain_rows':int(panel[['rain_'+str(n)+'h' for n in c.weather.windows]].isna().any(axis=1).sum()),
        'target':'recorded 311 report during hour [t,t+1); zeros are absence of report, not absence of flooding'})
    return panel


def static_features(c):
    """Optional local layers; CRS and DEM units must be audited by the researcher."""
    import rasterio
    from rasterio.mask import mask
    grid=make_grid(c)
    out=grid[['cell_id']].copy()
    f=path(c,'raw','catch_basins.geojson')
    if f.exists():
        points=gpd.read_file(f).to_crs(c.spatial.crs)
        if not points.geom_type.eq('Point').all():
            raise ValueError('Catch basins must be individual points')
        size=int(c.spatial.grid_m)
        ids=pd.Series([f'{int(np.floor(x/size))}_{int(np.floor(y/size))}' for x,y in zip(points.geometry.x,points.geometry.y)])
        out['catch_basin_count']=out.cell_id.map(ids.value_counts()).fillna(0).astype(int)
    f=path(c,'raw','dem_m.tif')
    if f.exists():
        with rasterio.open(f) as src:
            vals=[]
            for geom in grid.to_crs(src.crs).geometry:
                try:
                    a,_=mask(src,[geom],crop=True,filled=False,indexes=1)
                    vals.append(float(a.mean()) if a.count() else np.nan)
                except ValueError:
                    vals.append(np.nan)
            out['elevation_m']=vals
    if len(out.columns)==1:
        raise FileNotFoundError('Add catch_basins.geojson and/or dem_m.tif (vertical units meters) in raw directory.')
    dest=path(c,'raw','static_features.csv')
    if dest.exists():
        raise FileExistsError(f'{dest} exists; archive it or merge explicitly before rerunning static.')
    out.to_csv(dest,index=False)
