"""Re-score P1 LR suite from its portable bundle; no refit or calibration fitting."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import argparse
import joblib
import numpy as np
import pandas as pd
from scipy.special import expit,logit

def predict(frame,bundle):
    result=frame[['customer_unique_id','snapshot_date']].copy()
    values={m:a['pipeline'].predict_proba(frame[a['fields']])[:,1] for m,a in bundle['base_models'].items()}
    eps=bundle['clip_epsilon'];z=logit(np.clip(values['weightedLR'],eps,1-eps))
    values['weightedLR-prior-corrected']=expit(z-bundle['prior_log_weight_ratio'])
    values['weightedLR-oof-Platt']=bundle['platt'].predict_proba(z.reshape(-1,1))[:,1]
    values['constant-Oct']=np.full(len(frame),bundle['constant'])
    for m,p in values.items():
        result['score_'+m]=p
        result['prediction_0.5_'+m]=(p>=.5).astype('int8')
        result['prediction_Oct_maxF1_'+m]=(p>=bundle['thresholds'][m]).astype('int8')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('input_csv');parser.add_argument('output_csv')
    parser.add_argument('--bundle',default=str(Path(__file__).resolve().parent/'private/lr-probability-predictors.joblib'))
    args=parser.parse_args()
    predict(pd.read_csv(args.input_csv,dtype={'customer_unique_id':'string'}),joblib.load(args.bundle)).to_csv(args.output_csv,index=False)
