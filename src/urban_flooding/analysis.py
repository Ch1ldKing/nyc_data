import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
from .common import path


def load_panel(c):
    df=pd.read_csv(path(c,'processed','panel.csv'),dtype={'cell_id':str})
    df['time_utc']=pd.to_datetime(df.time_utc,utc=True)
    return df


def analyze(c):
    df=load_panel(c)
    out=path(c,'output','tables/summary.csv')
    pd.DataFrame([{'mode':c.mode,'grid_hours':len(df),'reports':df.report_count.sum(),'positive_hours':df.reported.sum(),
                   'report_rate':df.reported.mean(),'cells':df.cell_id.nunique()}]).to_csv(out,index=False)
    df.groupby('cell_id').agg(report_count=('report_count','sum'),report_rate=('reported','mean')).to_csv(path(c,'output','tables/cell_summary.csv'))
    df.groupby('time_utc').agg(report_count=('report_count','sum'),rain_1h=('rain_1h','first')).to_csv(path(c,'output','tables/hourly.csv'))
    cols=[x for x in ['reported','rain_1h','rain_3h','rain_6h','rain_24h',*c.model.static_columns] if x in df]
    df[cols].corr(method='spearman').to_csv(path(c,'output','tables/spearman.csv'))
    # Descriptive binned conditional report rates, no causal interpretation.
    for feature in c.model.static_columns:
        if feature not in df or df[feature].nunique()<2: continue
        x=df[['reported','rain_3h',feature]].dropna().copy()
        x['rain_bin']=pd.cut(x.rain_3h,[-.001,0,1,5,10,25,np.inf],include_lowest=True)
        x['static_bin']=pd.qcut(x[feature],4,duplicates='drop')
        if x.static_bin.nunique()<2: continue
        t=x.groupby(['rain_bin','static_bin'],observed=True).reported.agg(['mean','size']).reset_index()
        t.to_csv(path(c,'output',f'tables/interaction_{feature}.csv'),index=False)


def save(c, fig, name):
    if c.mode=='demo': fig.suptitle('SYNTHETIC DEMO — NOT RESEARCH EVIDENCE',fontsize=9,color='#9c3434')
    for ext in ['png','svg','pdf']:
        fig.savefig(path(c,'output',f'figures/{name}.{ext}'),dpi=300,bbox_inches='tight')
    plt.close(fig)


def figures(c):
    sns.set_theme(style='whitegrid', context='paper',font_scale=1.25)
    hourly=pd.read_csv(path(c,'output','tables/hourly.csv'),parse_dates=['time_utc'])
    fig,ax=plt.subplots(figsize=(9,3.3)); ax.plot(hourly.time_utc,hourly.report_count,color='#316584',label='311 reports'); ax.set_ylabel('Reports / hour')
    twin=ax.twinx(); twin.plot(hourly.time_utc,hourly.rain_1h,color='#b46b3b',alpha=.65); twin.set_ylabel('Lagged precipitation (mm)'); ax.set_xlabel('UTC'); fig.autofmt_xdate(); save(c,fig,'hourly_rainfall_reports')
    corr=pd.read_csv(path(c,'output','tables/spearman.csv'),index_col=0)
    fig,ax=plt.subplots(figsize=(7,6)); sns.heatmap(corr,vmin=-1,vmax=1,cmap='vlag',annot=True,fmt='.2f',ax=ax); save(c,fig,'spearman')
    grid=gpd.read_file(path(c,'processed','grid.gpkg'))
    summary=pd.read_csv(path(c,'output','tables/cell_summary.csv'),dtype={'cell_id':str}); grid=grid.merge(summary,on='cell_id')
    fig,ax=plt.subplots(figsize=(7,7)); grid.plot(column='report_count',cmap='YlOrRd',legend=True,ax=ax,edgecolor='none'); ax.set_axis_off(); ax.set_title('Historical reported street flooding (counts)'); save(c,fig,'historical_reports_map')
    import folium
    g=grid.to_crs(4326); centroid=grid.geometry.union_all().centroid; center=gpd.GeoSeries([centroid],crs=grid.crs).to_crs(4326).iloc[0]
    m=folium.Map(location=[center.y,center.x],zoom_start=10)
    folium.Choropleth(geo_data=g.to_json(),data=summary,columns=['cell_id','report_count'],key_on='feature.properties.cell_id',fill_color='YlOrRd',legend_name=('SYNTHETIC ' if c.mode=='demo' else '')+'311 report counts').add_to(m)
    m.save(str(path(c,'output','maps/historical_reports.html')))
    for f in path(c,'output','tables').glob('interaction_*.csv'):
        a=pd.read_csv(f); means=a.pivot(index='static_bin',columns='rain_bin',values='mean'); ns=a.pivot(index='static_bin',columns='rain_bin',values='size').reindex_like(means)
        fig,ax=plt.subplots(figsize=(9,4)); sns.heatmap(means.mask(ns<30),annot=True,fmt='.3f',cmap='YlOrRd',ax=ax); ax.set_title('Conditional report rate (n≥30 grid-hours)'); save(c,fig,f.stem)
    predictions=path(c,'output','tables/test_predictions.csv')
    if predictions.exists():
        pred=pd.read_csv(predictions,dtype={'cell_id':str}); avg=pred.groupby('cell_id').probability.mean().reset_index(); g2=grid.merge(avg,on='cell_id')
        fig,ax=plt.subplots(figsize=(7,7)); g2.plot(column='probability',cmap='YlOrRd',legend=True,ax=ax); ax.set_axis_off(); ax.set_title('Mean held-out report model score'); save(c,fig,'test_mean_risk_map')
