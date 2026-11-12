"""Source/shared-data audit and adapter freeze; NO model record/score reads."""
import sys
sys.dont_write_bytecode=True
import hashlib,json,runpy
from pathlib import Path
import numpy as np
from scipy import sparse
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.model_selection import train_test_split
from threadpoolctl import threadpool_limits
from scipy.special import expit
from producer_adapter import ROOT,STAT,SPLITS,KEY,load_harness,freeze_binding,sha,dump
BASE=['R','F','M','average_item_rows','freight_share','recent30_orders','recent30_spend','state']

def math_checks():
    z=np.linspace(-4,5,61);y=(np.arange(61)%7==0).astype(float);theta=np.array([.7,-2.3]);C=1e6
    def objective(t):
        a,b=t;v=a*z+b
        return float(np.sum(np.logaddexp(0,v)-y*v)+.5*a*a/C)
    e=expit(theta[0]*z+theta[1])-y;analytic=np.array([e@z+theta[0]/C,e.sum()]);numeric=[]
    for j in [0,1]:
        step=np.zeros(2);step[j]=1e-6;numeric.append((objective(theta+step)-objective(theta-step))/(2e-6))
    error=float(np.max(np.abs(analytic-numeric)));assert error<1e-6
    tests=[]
    for a,g in [(1e-6,.3),(1e-6,-.3),(.2,.3),(.2,-.3)]:
        mapping=a-max(1e-6,a-g);assert (mapping==0)==(a==1e-6 and g>0)
        tests.append(dict(a=a,gradient=g,projected_gradient_mapping=mapping))
    source=(ROOT/'eval_harness.py').read_text(encoding='utf-8')
    assert 'projected[0]=a-max(A_MIN,a-gradient[0])' in source
    return dict(analytic_vs_finite_difference_max_error=error,projection_cases=tests,study_fits=0,
        derivative='(sum((sigmoid(a*z+b)-y)*z)+a/1e6, sum(sigmoid(a*z+b)-y))',
        KKT='at a_min, grad_a>=0; b gradient zero; mapping theta-project(theta-grad)',
        objective_convex=True,active_bound_is_tolerance_label_not_gradient_certificate=True)

def main():
    h=load_harness();manifest=h.manifest();raw=h.raw_tables();october=raw['oct'];jan=raw['jan']
    assert (len(october),int(october.y.sum()),len(jan),int(jan.y.sum()))==(21160,211,29368,230)
    assert not october.duplicated(KEY).any() and not jan.duplicated(KEY).any()
    helper=next(Path(p) for p in manifest['sources'] if Path(p).name=='run_rfm_2x2.py')
    bounded=runpy.run_path(str(helper));reference_oct,reference_jan=bounded['read_dev']()
    for tag,f,reference,group_file in [('oct',october,reference_oct,'train_clusters.csv'),('jan',jan,reference_jan,'validation_clusters.csv')]:
        aligned=f[KEY+BASE+['y']].merge(reference[KEY+BASE+['y']],on=KEY,how='outer',validate='one_to_one',indicator=True,suffixes=('','_source'))
        assert aligned._merge.eq('both').all() and aligned.y.eq(aligned.y_source).all()
        assert aligned.state.astype(str).eq(aligned.state_source.astype(str)).all()
        for field in BASE[:-1]:assert np.allclose(aligned[field],aligned[field+'_source'],rtol=0,atol=1e-12)
        group_path=next(Path(p) for p in manifest['sources'] if Path(p).name==group_file)
        authority=__import__('pandas').read_csv(group_path,dtype={KEY[0]:'string'})
        matched=f[KEY+['cluster_id']].merge(authority[KEY+['cluster_id']],on=KEY,how='outer',validate='one_to_one',indicator=True,suffixes=('','_authority'))
        assert matched._merge.eq('both').all() and matched.cluster_id.eq(matched.cluster_id_authority).all()
    supports=[];matrix_audit=[]
    for split_id in SPLITS:
        directory=ROOT/f'shared/private/split-{split_id}';desc=manifest['splits'][str(split_id)]
        for file,digest in desc['files'].items():assert sha(directory/file)==digest
        idx=np.load(directory/'indices.npz');fit,cal=train_test_split(np.arange(len(october)),test_size=.2,stratify=october.y,random_state=split_id)
        assert np.array_equal(np.sort(fit),idx['fit']) and np.array_equal(np.sort(cal),idx['cal'])
        assert set(idx['fit']).isdisjoint(set(idx['cal'])) and len(set(idx['fit'])|set(idx['cal']))==21160
        frames=h.load_frames(split_id)
        for period,frame in frames.items():
            assert not frame.duplicated(KEY).any()
            for group in ['all',0,1,2]:
                part=frame if group=='all' else frame.loc[frame.cluster_id.eq(group)]
                supports.append(dict(split_id=split_id,period=period,group=str(group),n=len(part),events=int(part.y.sum()),F1=int(part.F.eq(1).sum())))
        fitkey='\n'.join(sorted(october.customer_unique_id.iloc[idx['fit']].astype(str)))+'\n'
        assert hashlib.sha256(fitkey.encode()).hexdigest()==desc['fit_key_sha256']
        lineage=json.loads((directory/'lineage.json').read_text());mask=np.load(directory/'base8-mask.npy')
        assert mask.dtype==bool and len(mask)==desc['dimension']==sum(desc['dims'])
        assert np.array_equal(mask,np.array([v['original8'] for v in lineage])) and mask.sum()==34
        assert all(v['field'] in BASE and v['kind'] in ['numeric','onehot'] for v,b in zip(lineage,mask) if b)
        assert all(not b for v,b in zip(lineage,mask) if v['kind']=='missing' or v['field'] not in BASE)
        assert [v['field'] for v,b in zip(lineage,mask) if b and v['kind']=='numeric']==BASE[:-1]
        assert all(v['field']=='state' for v,b in zip(lineage,mask) if b and v['kind']=='onehot')
        numeric=StandardScaler().fit(np.log1p(october[BASE[:-1]].iloc[idx['fit']]))
        category=OneHotEncoder(handle_unknown='ignore',sparse_output=False).fit(october[['state']].iloc[idx['fit']].astype(str))
        maxdifference=0
        # Inspect shared matrices only; root score records are never enumerated here.
        for period in ['fit','cal','jan']:
            full=sparse.load_npz(directory/f'{period}.npz');base=full.multiply(mask).tocsr();base.eliminate_zeros()
            source=october.iloc[idx[period]] if period!='jan' else jan
            expected=np.hstack([numeric.transform(np.log1p(source[BASE[:-1]])),category.transform(source[['state']].astype(str))])
            difference=float(np.max(np.abs(base[:,mask].toarray()-expected)));assert difference<1e-11
            maxdifference=max(maxdifference,difference)
            assert full.shape==base.shape and full.shape[1]==sum(desc['dims']) and base[:,~mask].nnz==0
            if period=='fit':
                nz=int((np.asarray(full.getnnz(axis=0))>0).sum())
                lo=full.min(axis=0).toarray().ravel();hi=full.max(axis=0).toarray().ravel()
                matrix_audit.append(dict(split_id=split_id,total_width=full.shape[1],view_dims=desc['dims'],base8_encoded_columns=int(mask.sum()),full_nonzero_columns=nz,full_nonconstant_columns=int((lo!=hi).sum()),base_nonconstant_columns=int((lo[mask]!=hi[mask]).sum()),base_extra_nonzeros=0))
        # Exercise the actual root loader at canonical split, rather than source text alone.
        if split_id==20261111:
            loaded=h.load_split(split_id,'base8')
            for period in ['fit','cal','jan']:
                explicit=sparse.load_npz(directory/f'{period}.npz').multiply(mask).tocsr();explicit.eliminate_zeros()
                assert (loaded['X_'+period]!=explicit).nnz==0
            del loaded
        matrix_audit[-1]['original8_independent_transform_max_abs_difference']=maxdifference
    df=__import__('pandas').DataFrame
    df(supports).to_csv(STAT/'shared-support-audit.csv',index=False,lineterminator='\n')
    df([{**r,'view_dims':json.dumps(r['view_dims'])} for r in matrix_audit]).to_csv(STAT/'shared-matrix-audit.csv',index=False,lineterminator='\n')
    receipt=dict(status='PASS_SHARED_BIND_ONLY',split_count=5,authoritative_counts={'oct':21160,'oct_events':211,'jan':29368,'jan_events':230,'long':12330,'long_events':90},
        shared_shapes_and_lineage_verified=True,fit_cal_indices_recomputed=True,actual_canonical_loader_mask_verified=True,
        bounded_H02_keys_y_original8_exactly_matched=True,authoritative_H05_Oct_Jan_groups_keyed_exactly_matched=True,
        Platt_math=math_checks(),matrix_audit=matrix_audit,model_records_read=False,study_scores_read=False,study_models_trained=0,study_bootstrap_replicates=0,
        producer_harness_sha256=sha(ROOT/'eval_harness.py'),protocol_addendum_sha256=sha(ROOT/'protocol-clarification.md'),code_sha256=sha(Path(__file__)))
    dump(STAT/'shared-source-audit.json',receipt);binding=freeze_binding(receipt)
    print('BOUND_WAITING_ROOT_RUN_STATS; score records/NPZ read: 0')
    print(json.dumps(matrix_audit,indent=2));print('Synthetic derivative error',receipt['Platt_math']['analytic_vs_finite_difference_max_error'])
if __name__=='__main__':
    with threadpool_limits(limits=2):main()
