import pandas as pd
import pytest
from urban_flooding.common import load_config
from urban_flooding.download import demo
from urban_flooding.preprocess import preprocess, weather_features
from urban_flooding.model import temporal_split

@pytest.fixture
def cfg(tmp_path):
    c=load_config('configs/demo.yaml')
    for k in c.paths: c.paths[k]=str(tmp_path/k/'demo')
    return c

def test_demo_panel(cfg):
    demo(cfg); df=preprocess(cfg)
    assert df.cell_id.nunique()==30
    assert len(df)==30*14*24
    assert df.reported.nunique()==2
    assert not df.duplicated(['cell_id','time_utc']).any()
    assert (df.reported==(df.report_count>0)).all()
    a,b,c=temporal_split(df,.6,.2)
    assert a.time_utc.max()<b.time_utc.min()<c.time_utc.min()

def test_rainfall_lag(cfg):
    demo(cfg)
    w=weather_features(cfg)
    raw=pd.read_csv(cfg.paths.raw+'/weather.csv'); raw.time_utc=pd.to_datetime(raw.time_utc,utc=True)
    first=w.iloc[0]
    expected=raw.loc[raw.time_utc==first.time_utc-pd.Timedelta(hours=1),'precip_mm'].iloc[0]
    assert first.rain_1h==pytest.approx(expected)
