from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone
import pandas as pd
from omegaconf import OmegaConf


def load_config(path):
    c = OmegaConf.load(path)
    if c.mode not in ('real', 'demo') or any(c.mode not in Path(c.paths[k]).parts for k in ('raw', 'processed', 'output')):
        raise ValueError('Use separate real/demo paths for every run.')
    if pd.Timestamp(c.start) >= pd.Timestamp(c.end):
        raise ValueError('Invalid date range')
    for p in c.paths.values():
        Path(p).mkdir(parents=True, exist_ok=True)
    return c


def path(c, kind, name):
    p = Path(c.paths[kind]) / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_json(p, value):
    p.write_text(json.dumps(value, indent=2, default=str, allow_nan=False) + '\n')


def manifest(c, files, sources):
    records = []
    for p in files:
        with p.open('rb') as f:
            digest = hashlib.file_digest(f, 'sha256').hexdigest()
        records.append({'file': str(p), 'bytes': p.stat().st_size, 'sha256': digest})
    write_json(path(c, 'raw', 'manifest.json'), {'mode': c.mode, 'start': c.start, 'end': c.end,
        'created_utc': datetime.now(timezone.utc).isoformat(), 'sources': sources, 'files': records})


def time_range(c):
    return pd.date_range(c.start, c.end, freq='h', inclusive='left', tz='UTC')
