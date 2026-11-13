"""Saved-aggregate comparison figures; no new model, score or interval estimation."""
from pathlib import Path
import hashlib,json,subprocess
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).resolve().parent;F=O/'figures';F.mkdir(exist_ok=True);D=O/'data'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
colors={'weightedLR':'#167a89','unweightedLR':'#748799','nativeCatBoost-mean3':'#c08732'}
names={'weightedLR':'Weighted LR, 8 fields','unweightedLR':'Unweighted LR, 8 fields','nativeCatBoost-mean3':'Native CB, 141 fields, mean3'}
def save(fig,n):
 for ext in ['png','svg']:fig.savefig(F/(n+'.'+ext),dpi=165,bbox_inches='tight')
 plt.close(fig)
p=pd.read_csv(D/'protocol-comparison.csv')
fig,ax=plt.subplots(figsize=(13,6));ax.axis('off')
rowlabels=['Predictor-fit customers','Calibration customers','Historical fields','Model score','January customers / events','Global list K','Observed hits at K','Separate long-group K / hits']
cells=[['21,160','16,928','16,928'],['0','4,232','4,232'],['8','141','8'],['Weighted-LR ranking score','Mean of 3 calibrated CB probabilities','Calibrated weighted-LR probability'],['29,368 / 230']*3,['2,937']*3,['50','49','43'],['79 / 2']*3]
tab=ax.table(cellText=cells,rowLabels=rowlabels,colLabels=['A: team R3 reference','B: proposed main probability pipeline','B: same-protocol reference'],cellLoc='center',rowLoc='left',loc='center',colWidths=[.27,.38,.34]);tab.auto_set_font_size(False);tab.set_fontsize(10);tab.scale(1,2.0)
for (r,c),cell in tab.get_celld().items():
 if r==0:cell.set_facecolor('#e4eef1');cell.set_text_props(weight='bold')
 if r==7:cell.set_facecolor('#f7ecd9')
ax.set_title('Same January evaluation; different training and calibration recipes',fontsize=16,pad=28)
fig.text(.01,.02,'A vs B is not a controlled algorithm win test. Within B, CB141 vs LR8 also changes the information set.\nUse the separate same-information study for model attribution. Both routes score all eligible customers.',fontsize=10,color='#526474')
save(fig,'01-protocol-comparison')

cv=pd.read_csv(D/'team-cv-diagnostics.csv');order=['F0_base_unweighted','F0_base_weighted','F1_delivery_unweighted','F1_delivery_weighted','F2_review_unweighted','F2_review_weighted','B_global_with_cluster','C_segmented_group2_global_fallback'];q=cv.set_index('method').loc[order]
fig,ax=plt.subplots(figsize=(12.4,5.4),layout='constrained');xx=np.arange(8)
ax.bar(xx,q.cv_hits_mean,yerr=q.cv_hits_std,capsize=5,color=['#748799','#167a89']*3+['#c08732','#785c98'])
for i,r in enumerate(q.itertuples()):ax.text(i,r.cv_hits_mean+r.cv_hits_std+.15,f'{r.cv_hits_mean:.1f}',ha='center')
ax.set_xticks(xx,['Base\nunweighted','Base\nweighted','Delivery\nunweighted','Delivery\nweighted','Review\nunweighted','Review\nweighted','R3 add\ncluster','R3 group\nmodels']);ax.set_ylim(0,12);ax.set_ylabel('Mean hits per validation fold (K = 424)');ax.grid(axis='y',alpha=.2)
ax.set_title('A: October internal 5-fold diagnostic\nError bars are sample SD across folds, not 95% CI or a future-month test',fontsize=13)
fig.supxlabel('Each held-out fold: N = 4,232, events = 42 or 43. R3 group variants use a fixed all-October H05 mapping.',fontsize=10)
save(fig,'02-team-cv-diagnostics')

r=pd.read_csv(D/'local-rolling-probability-and-lists.csv');r=r[r.strategy.eq('single')]
fig,axes=plt.subplots(2,2,figsize=(12.5,8.4),layout='constrained')
spec=[('logloss','All-customer log loss (lower is better)'),('AP','Average precision (higher is better)'),('hits','Hits in global top 10%'),('long79_hits','Hits in separate long-group K = 79')]
for ax,(metric,label) in zip(axes.flat,spec):
 for family in names:
  z=r[r.family.eq(family)].sort_values('evaluation_date');ax.plot(np.arange(3),z[metric],marker='o',color=colors[family],label=names[family])
 ax.set_xticks(np.arange(3),['Nov 2017','Dec 2017','Jan 2018']);ax.set_title(label,fontsize=12);ax.grid(alpha=.2)
 if metric=='long79_hits':ax.set_ylim(-.1,2.4);ax.set_yticks([0,1,2])
handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,ncol=3,loc='outside lower center',fontsize=10)
fig.suptitle('B: matched fit/calibration/evaluation protocol within each date\nKnown overlapping historical windows; CB141 vs LR8 is a complete-pipeline comparison',fontsize=14)
save(fig,'03-local-controlled-rolling')
root=Path('E:/app-data/codex/scratchpad/is6400-round3-20261111/git-release');scratch=Path('E:/app-data/codex/scratchpad/is6400-route-comparison-20261114');assets=[
('shared-time','research/team-round3-20261112/members/role01/time-boundaries.png'),
('A-results','research/team-round3-20261112/figures/01-team-models-and-long79.png'),
('A-field-evidence','research/role02-v11-20261113/member/figures/02-candidate-effect-sizes.png'),
('A-profile','research/team-round3-20261112/figures/03-current-group-1.png'),
('B-information','research/common-comparison-20261112/statistics/figures/paired-information-effects.png'),
('B-ablation','research/ae-ablation-20261112/statistics/blocks-canonical-conditional-intervals.png'),
('B-temporal-negative','research/ae-ablation-20261112/temporal/temporal-comparison.png'),
('B-value','research/final-validation-20261112/figures/02-january-hits-value-tradeoff.png')]
reused=[]
for label,path in assets:
 b=subprocess.check_output(['git','show','origin/main:'+path],cwd=root);dst=scratch/(label+'.png');dst.write_bytes(b);reused.append({'label':label,'repository_path':path,'sha256':hashlib.sha256(b).hexdigest(),'view_path':str(dst),'new_scientific_figure':False})
(O/'reused-figure-index.json').write_text(json.dumps(reused,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest={'status':'GENERATED_VIEW_PENDING','new_png_svg_pairs':3,'reused_png':len(reused),'new_model_fits':0,'new_uncertainty_intervals':0,'files':{str(p.relative_to(O)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in F.iterdir()}}
(O/'plot-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');print(json.dumps({'new_png_svg_pairs':3,'reused_figures':len(reused)}))
