import json
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, roc_auc_score, precision_score, recall_score, f1_score, brier_score_loss, precision_recall_curve
from sklearn.dummy import DummyClassifier
from .analysis import load_panel, save, plt
from .common import path, write_json
import joblib


def temporal_split(df, train_fraction, validation_fraction):
    times=df.time_utc.drop_duplicates().sort_values().tolist()
    a=int(len(times)*train_fraction); b=int(len(times)*(train_fraction+validation_fraction))
    if not 0<a<b<len(times): raise ValueError('Invalid temporal split')
    return df[df.time_utc<times[a]],df[(df.time_utc>=times[a])&(df.time_utc<times[b])],df[df.time_utc>=times[b]]


def train(c):
    df=load_panel(c)
    rain=[f'rain_{n}h' for n in c.weather.windows]
    # Missing weather is not dry weather; exclude rows with unavailable history.
    df=df.dropna(subset=rain)
    tr,va,te=temporal_split(df,c.model.train_fraction,c.model.validation_fraction)
    for name,split in [('train',tr),('validation',va),('test',te)]:
        if split.reported.nunique()!=2: raise ValueError(f'{name} has only one class; extend interval or revise split.')
    base=rain+['hour_sin','hour_cos','weekend']
    static=[x for x in c.model.static_columns if x in tr and tr[x].notna().any()]
    groups={'weather_time':base}
    if static: groups['weather_time_static']=base+static
    results=[]; curves=[]; best=None
    for group,features in groups.items():
        models={'logistic':make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),LogisticRegression(max_iter=500,random_state=c.seed)),
                'random_forest':make_pipeline(SimpleImputer(strategy='median'),RandomForestClassifier(n_estimators=c.model.random_forest_trees,min_samples_leaf=10,n_jobs=2,random_state=c.seed))}
        if 'xgboost' in c.model.algorithms:
            from xgboost import XGBClassifier
            models['xgboost']=make_pipeline(SimpleImputer(strategy='median'),XGBClassifier(n_estimators=150,max_depth=5,n_jobs=2,random_state=c.seed,eval_metric='logloss'))
        if 'lightgbm' in c.model.algorithms:
            from lightgbm import LGBMClassifier
            models['lightgbm']=make_pipeline(SimpleImputer(strategy='median'),LGBMClassifier(n_estimators=150,n_jobs=2,random_state=c.seed,verbosity=-1))
        models={k:v for k,v in models.items() if k in c.model.algorithms}
        if group=='weather_time': models['prevalence']=DummyClassifier(strategy='prior')
        for name,model in models.items():
            model.fit(tr[features],tr.reported)
            p_val=model.predict_proba(va[features])[:,1]; p_test=model.predict_proba(te[features])[:,1]
            # Select threshold from validation only; threshold candidates plus configured default.
            thresholds=np.unique(np.r_[np.quantile(p_val,np.linspace(0,1,101)),c.model.threshold])
            threshold=float(max(thresholds,key=lambda t:f1_score(va.reported,p_val>=t,zero_division=0)))
            score=float(average_precision_score(va.reported,p_val)); yhat=p_test>=threshold
            r={'feature_set':group,'model':name,'validation_ap':score,'test_ap':average_precision_score(te.reported,p_test),'test_auroc':roc_auc_score(te.reported,p_test),'test_f1':f1_score(te.reported,yhat,zero_division=0),'test_precision':precision_score(te.reported,yhat,zero_division=0),'test_recall':recall_score(te.reported,yhat,zero_division=0),'test_brier':brier_score_loss(te.reported,p_test),'threshold':threshold,'test_prevalence':te.reported.mean()}
            results.append(r)
            p,rec,_=precision_recall_curve(te.reported,p_test); curves.append((f'{group}/{name}',p,rec))
            if best is None or score>best[0]: best=(score,model,features,p_test,r)
    pd.DataFrame(results).to_csv(path(c,'output','tables/model_metrics.csv'),index=False)
    if best is None: raise ValueError('No models')
    _,model,features,p,r=best
    pred=te[['cell_id','time_utc','reported']].copy(); pred['probability']=p; pred.to_csv(path(c,'output','tables/test_predictions.csv'),index=False)
    joblib.dump({'model':model,'features':features},path(c,'output','models/best.joblib'))
    write_json(path(c,'output','model_run.json'),{'mode':c.mode,'selected_by':'validation average precision','selected':r,'features':features,'splits':{n:{'start':s.time_utc.min(),'end':s.time_utc.max(),'rows':len(s),'positives':int(s.reported.sum())} for n,s in [('train',tr),('validation',va),('test',te)]},'note':'Retrospective reanalysis proxy, not operational forecast; temporal test only.'})
    fig,ax=plt.subplots(figsize=(7,5))
    for label,p,rec in curves: ax.plot(rec,p,label=label)
    ax.axhline(te.reported.mean(),linestyle='--',color='gray'); ax.set(xlabel='Recall',ylabel='Precision',title='Held-out precision–recall'); ax.legend(fontsize=7); save(c,fig,'precision_recall')


def explain(c):
    import shap
    artifact=joblib.load(path(c,'output','models/best.joblib'))
    model,features=artifact['model'],artifact['features']; df=load_panel(c)
    df=df.dropna(subset=[f'rain_{n}h' for n in c.weather.windows]); tr,_,te=temporal_split(df,c.model.train_fraction,c.model.validation_fraction)
    bg=tr[features].sample(min(50,len(tr)),random_state=c.seed); sample=te[features].sample(min(100,len(te)),random_state=c.seed)
    # Impute from training only; explain the entire pipeline in probability space.
    bg=bg.fillna(tr[features].median()); sample=sample.fillna(tr[features].median())
    def predict(x): return model.predict_proba(pd.DataFrame(x,columns=features))[:,1]
    explainer=shap.Explainer(predict,bg,algorithm='permutation',seed=c.seed)
    values=explainer(sample,max_evals=2*len(features)+1)
    plt.figure(); shap.plots.beeswarm(values,show=False); save(c,plt.gcf(),'shap_beeswarm')
    pd.DataFrame({'feature':features,'mean_abs_shap':np.abs(values.values).mean(axis=0)}).sort_values('mean_abs_shap',ascending=False).to_csv(path(c,'output','tables/shap_importance.csv'),index=False)
