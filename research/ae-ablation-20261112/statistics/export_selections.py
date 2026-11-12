"""Export the already-computed deterministic lists from fixed ensemble arrays."""
import sys
sys.dont_write_bytecode=True
import numpy as np,pandas as pd
import run_statistics as run
def main():
    run.frozen();rows=[]
    for split in run.SPLITS:
        frame=pd.read_csv(run.OUT/'private'/f'split{split}-jan-cohort.csv',dtype={k:'string' for k in run.KEY});scores=np.load(run.OUT/'private'/f'split{split}-ensemble-probabilities.npz')
        for model in run.SYSTEMS:
            p=scores['jan__'+model]
            for scope,mask in run.masks(frame):
                f=frame.loc[mask].reset_index(drop=True);q=p[mask];order=np.lexsort((f.snapshot_date.astype(str),f.customer_unique_id.astype(str),-q));k=2937 if scope=='all' else 79
                selected=f.iloc[order[:k]].copy();selected['probability']=q[order[:k]];selected['rank']=np.arange(1,k+1);selected['split_id']=split;selected['model']=model;selected['scope']=scope;rows.append(selected)
    result=pd.concat(rows,ignore_index=True);assert len(result)==70*(2937+79)
    path=run.OUT/'private/ensemble-selections.csv.gz';result.to_csv(path,index=False,lineterminator='\n')
    run.dump('selection-export.json',dict(status='fixed_score_deterministic_lists_saved_private',rows=len(result),systems=14,split_system_cells=70,score_rule='mean(calibrated probability)',list_policy='all K2937, long cluster1 K79, probability descending then customer/snapshot keys',private_path='private/ensemble-selections.csv.gz',sha256=run.sha(path),source_code_sha256=run.sha(__file__)))
if __name__=='__main__':main()
