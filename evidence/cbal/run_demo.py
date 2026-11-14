"""Reproduce C-BAL on deterministic synthetic data using a pinned public checkout.
No APIs, GPUs, personal data, or pretrained model downloads are used.
See README.md for source checkout and isolated environment instructions.
"""
from pathlib import Path
import os,json,time,hashlib,subprocess,platform,datetime,importlib.metadata,argparse,sys
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
EXPECTED_COMMIT='70a8139c163d000824e67c4420b43e14f42b5e3e'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-dir',type=Path,required=True,help='Clean public cbal checkout at the pinned commit')
parser.add_argument('--output-dir',type=Path,default=Path('run-output'),help='Directory for generated CSVs, JSON and optional chart')
parser.add_argument('--no-plot',action='store_true',help='Run numerical reproduction without drawing a chart')
args=parser.parse_args()
source_dir=args.source_dir.resolve()
head=subprocess.check_output(['git','-C',str(source_dir),'rev-parse','HEAD'],text=True).strip()
if head!=EXPECTED_COMMIT:parser.error(f'Expected commit {EXPECTED_COMMIT}; found {head}')
dirty=subprocess.check_output(['git','-C',str(source_dir),'status','--porcelain'],text=True).strip()
if dirty:parser.error('Source checkout has uncommitted changes; use a clean pinned checkout.')
sys.path.insert(0,str(source_dir))
work=args.output_dir.resolve()
work.mkdir(parents=True,exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR',str(work/'mpl-cache'))
import numpy as np
import pandas as pd
from cbal import TimeSeriesPredictor,TimeSeriesDataFrame,__version__ as cbal_version

SEED=42;HORIZON=14;DAYS=180
rng=np.random.default_rng(SEED)
rows=[]
for i,(base,trend,amp,noise,phase) in enumerate([(80,.08,18,2.2,0),(130,.16,12,3.5,2),(200,-.04,25,4.0,5)]):
 for t in range(DAYS):
  value=base+trend*t+amp*np.sin(2*np.pi*(t+phase)/7)+rng.normal(0,noise)
  rows.append({'item_id':f'Series {chr(65+i)}','timestamp':pd.Timestamp('2025-01-01')+pd.Timedelta(days=t),'target':round(value,4)})
raw=pd.DataFrame(rows);raw.to_csv(work/'synthetic-data.csv',index=False)
data=TimeSeriesDataFrame.from_data_frame(raw)
trainval,test=data.train_test_split(HORIZON)
train,validation=trainval.train_test_split(HORIZON)
models={'Naive':{},'SeasonalNaive':{'seasonal_period':7},'Average':{},'Drift':{},'AutoETS':{'season_length':7,'n_jobs':1},'AutoTheta':{'season_length':7,'n_jobs':1}}
config={'models':models,'ensemble':'WeightedEnsemble','time_limit_per_model':20}
predictor=TimeSeriesPredictor(prediction_length=HORIZON,eval_metric='MAE',freq='D',path=str(work/'model-output'),verbosity=2,cache_predictions=False)
started=time.perf_counter()
predictor.fit(train,presets=config,val_data=validation,enable_ensemble=True,num_val_windows=1,time_limit=60,random_seed=SEED)
fit_seconds=time.perf_counter()-started
leaderboard=predictor.leaderboard(silent=True)
assert set(models)==set(predictor._models),f'Not all requested models fitted: {predictor.model_names}'
assert np.isfinite(leaderboard['score_val']).all()
selected=predictor.best_model
weights=dict(predictor._ensemble.weights) if predictor._ensemble is not None else {}
# Model selection ends here. The final 14 observations have never been supplied.
# Explicitly refit every base model on train+validation using its public fit().
# C-BAL stores these models in _models and the ensemble keeps their references;
# its public refit_full currently skips ensembles, so this external harness
# does the final refit explicitly without editing the library source.
refit_start=time.perf_counter()
for model in predictor._models.values():model.fit(trainval,time_limit=20)
refit_seconds=time.perf_counter()-refit_start
predictions={name:predictor.predict(trainval,model=name,quantile_levels=[.1,.5,.9]) for name in predictor.model_names}
actual=test.slice_by_timestep(-HORIZON,None)['target']
test_scores={}
for name,forecast in predictions.items():
 assert len(forecast)==3*HORIZON and forecast.index.equals(actual.index)
 assert np.isfinite(forecast['mean']).all()
 test_scores[name]=float(np.mean(np.abs(actual.values-forecast['mean'].values)))
 forecast.reset_index().to_csv(work/f'prediction-{name}.csv',index=False)
leaderboard.to_csv(work/'validation-leaderboard.csv',index=False)
report={'repository':'https://github.com/codespermuted/cbal','commit':head,'run_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'python':platform.python_version(),'platform':platform.platform(),'seed':SEED,'data_kind':'synthetic, no personal or business data','data_sha256':hashlib.sha256((work/'synthetic-data.csv').read_bytes()).hexdigest(),'series_count':3,'observations_per_series':DAYS,'total_rows':len(raw),'initial_train_days':152,'validation_days':14,'untouched_test_days':14,'model_selection':'single chronological validation window, MAE','refit':'all base models refitted on first 166 days after selection, ensemble weights fixed','selected_model':selected,'ensemble_weights':weights,'validation_leaderboard':leaderboard.to_dict('records'),'holdout_mae_by_model':test_scores,'selected_holdout_mae':test_scores[selected],'fit_seconds':fit_seconds,'refit_seconds':refit_seconds,'dependencies':{'cbal':cbal_version,**{name:importlib.metadata.version(name) for name in ['numpy','pandas','scipy','statsforecast','scikit-learn','matplotlib']}},'limitations':['Synthetic demonstration, not production performance or a published benchmark.','Only six CPU baseline/statistical candidates were run; deep and foundation models were not tested.','One validation and one holdout window; no multi-window generalization claim.','External harness explicitly refits base models; the source library is unmodified.']}
(work/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'selected':selected,'validation':leaderboard.to_dict('records'),'weights':weights,'holdout':test_scores,'fit_seconds':fit_seconds,'refit_seconds':refit_seconds},ensure_ascii=False,indent=2))

if args.no_plot:sys.exit(0)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import MaxNLocator
font=FontProperties(family='DejaVu Sans')
plt.rcParams.update({'figure.facecolor':'#f5f4ed','axes.facecolor':'#f5f4ed','axes.edgecolor':'#ccd0c6','axes.labelcolor':'#2c3930','xtick.color':'#647065','ytick.color':'#647065','font.size':11,'svg.fonttype':'path'})
fig=plt.figure(figsize=(15,8.4),dpi=120)
gs=fig.add_gridspec(1,2,width_ratios=[1.55,1],left=.07,right=.965,bottom=.19,top=.72,wspace=.29)
ax=fig.add_subplot(gs[0]);bars=fig.add_subplot(gs[1])
series='Series A';hist=trainval.loc[series]['target'].iloc[-42:];future=actual.loc[series];pred=predictions[selected].loc[series]
ax.plot(hist.index,hist.values,color='#697369',lw=1.7,label='Train + validation')
ax.plot(future.index,future.values,color='#293e32',lw=2.1,marker='o',ms=3.5,label='Held-out observations')
ax.plot(pred.index,pred['mean'],color='#aa4a36',lw=2.2,linestyle='--',label='Selected forecast')
ax.axvline(future.index[0],color='#b7beb2',lw=1,ls=':')
ax.axvspan(future.index[0],future.index[-1],color='#e1e8dc',alpha=.55,zorder=-2)
ax.set_title('Forecasting the next 14 days',fontproperties=font,fontsize=14,loc='left',pad=22,color='#22352a')
ax.set_ylabel('Synthetic demand (arbitrary units)',fontproperties=font,fontsize=11,labelpad=10)
ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2));ax.xaxis.set_major_formatter(mdates.DateFormatter('%m.%d'))
ax.grid(axis='y',color='#dde1d8',lw=.8);ax.set_axisbelow(True)
ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='both',length=0,pad=10)
legend=ax.legend(loc='lower left',bbox_to_anchor=(-.025,-.19),frameon=False,prop=FontProperties(family='DejaVu Sans',size=9),ncols=3,columnspacing=1.5)
rank=leaderboard.sort_values('score_val',ascending=True)
labels=[str(x).replace('WeightedEnsemble','Ensemble') for x in rank['model']]
colors=['#a44c37' if n==selected else '#80977f' for n in rank['model']]
bars.barh(labels,rank['score_val'],color=colors,height=.55)
bars.invert_yaxis();bars.set_title('Comparing the same validation window',fontproperties=font,fontsize=14,loc='left',pad=22,color='#22352a')
bars.set_xlabel('Validation MAE (lower is better)',fontproperties=font,fontsize=11,labelpad=13)
bars.xaxis.set_major_locator(MaxNLocator(4));bars.set_xlim(0,float(rank['score_val'].max())*1.20)
bars.grid(axis='x',color='#dde1d8',lw=.8);bars.set_axisbelow(True);bars.spines[['top','right','left']].set_visible(False);bars.tick_params(axis='both',length=0,pad=8)
for i,v in enumerate(rank['score_val']):bars.text(float(v)+.15,i,f'{v:.2f}',va='center',fontsize=11,color='#334b3a')
fig.text(.07,.92,'C-BAL: from model comparison to forecast',fontproperties=font,fontsize=23,color='#23372a')
fig.text(.07,.858,'Public code on CPU  /  3 synthetic series x 180 days  /  seed 42',fontproperties=font,fontsize=13,color='#63705f')
fig.text(.07,.795,f'Selected: {selected}     |     Held-out test MAE: {test_scores[selected]:.2f}',fontproperties=font,fontsize=13,color='#a14a35')
fig.text(.07,.045,'Actual code execution on synthetic data. This is a demonstration, not evidence of production performance.',fontproperties=font,fontsize=10.5,color='#63705f')
fig.savefig(work/'cbal-synthetic-forecast.png',dpi=120)
from PIL import Image
image=Image.open(work/'cbal-synthetic-forecast.png')
media=work/'cbal-synthetic-forecast.webp';image.save(media,'WEBP',quality=94,method=6)
report['evidence']={'file':media.name,'width':image.width,'height':image.height,'bytes':media.stat().st_size,'alt':'C-BAL synthetic forecast and validation MAE comparison from an actual CPU run; not production performance.'}
(work/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'evidence':report['evidence']},ensure_ascii=False,indent=2))
