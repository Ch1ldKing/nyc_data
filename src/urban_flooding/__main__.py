import argparse
import json
from .common import load_config, path
from .download import download
from .preprocess import audit, preprocess, static_features
from .analysis import analyze, figures
from .model import train, explain


def report(c):
    import pandas as pd
    def table(p):
        d=pd.read_csv(p); return '```text\n'+d.to_string(index=False)+'\n```'
    r=json.loads(path(c,'output','model_run.json').read_text())
    body=f'# Analysis run — {c.mode.upper()}\n\n'
    if c.mode=='demo': body+='**SYNTHETIC DEMONSTRATION ONLY. No empirical conclusions.**\n\n'
    body+='## Data summary\n'+table(path(c,'output','tables/summary.csv'))+'\n\n## Model results\n'+table(path(c,'output','tables/model_metrics.csv'))+'\n\n'
    body+='## Model selection\nSelected on validation AP: '+r['selected']['model']+' / '+r['selected']['feature_set']+'.\n\n'
    body+='## Limitations\n- Target is a recorded street-flooding report, not confirmed flooding.\n- Historical weather is city-scale reanalysis, not a live forecast.\n- Conditional rates and SHAP are not causal.\n- Independent sensor validation, spatial generalization and complete infrastructure coverage remain future tasks.\n\n## Figures\n'
    for f in sorted(path(c,'output','figures').glob('*.png')): body+=f'- [{f.stem}](figures/{f.name})\n'
    path(c,'output','report.md').write_text(body)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--config',required=True); p.add_argument('command',choices=['download','audit','static','preprocess','analyze','train','explain','figures','report','all']); a=p.parse_args(); c=load_config(a.config)
    commands={'download':download,'audit':audit,'static':static_features,'preprocess':preprocess,'analyze':analyze,'train':train,'explain':explain,'figures':figures,'report':report}
    if a.command=='all':
        for k in ['download','preprocess','analyze','train','figures','report']:
            print(f'[{c.mode}] {k}',flush=True); commands[k](c)
    else: commands[a.command](c)

if __name__=='__main__': main()
