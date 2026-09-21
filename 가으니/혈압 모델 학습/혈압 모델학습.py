"""혈압 3개 모델 첫 비교 실험. 검증 AP로 선택, 미보정 확률. 재실행 결과는 별도 폴더."""
from pathlib import Path
from datetime import datetime
import json, hashlib, warnings
import numpy as np
import pandas as pd
import joblib
import sklearn
import xgboost
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, brier_score_loss, confusion_matrix, precision_recall_curve
from xgboost import XGBClassifier
from threadpoolctl import threadpool_limits

BASE=Path(__file__).resolve().parent
SOURCE=BASE/'혈압모델_기초데이터.csv'
NUM=['age','HE_BMI','HE_wc']
CAT=['sex','sm_presnt','dr_month','pa_aerobic','HE_HPfh1','HE_HPfh2','HE_HPfh3']
FEATURES=NUM+CAT
TARGET='target_bp'
SEED=42

def preprocessing():
    return ColumnTransformer([
        ('numeric',Pipeline([('impute',SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True)),('scale',StandardScaler())]),NUM),
        ('category',Pipeline([('impute',SimpleImputer(strategy='constant',fill_value=-1,keep_empty_features=True)),('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),CAT)])

def scores(y,p,t,w=None):
    pred=(p>=t).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1],sample_weight=w).ravel()
    return dict(Accuracy=accuracy_score(y,pred,sample_weight=w),Precision=precision_score(y,pred,sample_weight=w,zero_division=0),Recall=recall_score(y,pred,sample_weight=w,zero_division=0),F1=f1_score(y,pred,sample_weight=w,zero_division=0),ROC_AUC=roc_auc_score(y,p,sample_weight=w),PR_AP=average_precision_score(y,p,sample_weight=w),Brier=brier_score_loss(y,p,sample_weight=w),TN=float(tn),FP=float(fp),FN=float(fn),TP=float(tp))

def candidates():
    for depth in [5,10]:
        yield 'RF',f'depth{depth}',RandomForestClassifier(n_estimators=300,max_depth=depth,min_samples_leaf=5,random_state=SEED,n_jobs=4)
    for depth in [2,4]:
        yield 'XGBoost',f'depth{depth}',XGBClassifier(n_estimators=250,max_depth=depth,learning_rate=0.03,subsample=0.8,colsample_bytree=0.8,reg_lambda=5,objective='binary:logistic',eval_metric='logloss',tree_method='hist',n_jobs=4,random_state=SEED)
    for layers in [(32,16),(64,32)]:
        yield 'DNN',str(layers),MLPClassifier(hidden_layer_sizes=layers,alpha=0.01,batch_size=128,max_iter=600,early_stopping=False,n_iter_no_change=30,random_state=SEED)

def main():
    df=pd.read_csv(SOURCE,dtype={'ID':str,'ID_fam':str,'psu':str})
    assert not df.ID.duplicated().any()
    assert df[TARGET].isin([0,1]).all() and df.wt_itvex.gt(0).all()
    assert df[['ID','ID_fam','psu','kstrata']].notna().all().all()
    assert not np.isinf(df[FEATURES+['wt_itvex']].to_numpy()).any()
    assert not df.groupby('ID_fam').psu.nunique().gt(1).any()
    for c in CAT:
        allowed=[1,2] if c=='sex' else ([0,1,2] if c=='HE_HPfh3' else [0,1])
        assert df[c].dropna().isin(allowed).all(),c
    fold=np.full(len(df),-1)
    for i,(_,ix) in enumerate(StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=SEED).split(df[FEATURES],df[TARGET],df.psu)):
        fold[ix]=i
    split=np.where(fold==0,'test',np.where(fold==1,'validation','train'))
    parts={s:df.loc[split==s].copy() for s in ['train','validation','test']}
    for key in ['psu','ID_fam','ID']:
        a,b,c=[set(x[key]) for x in parts.values()]
        assert not(a&b or a&c or b&c)
    for x in parts.values(): assert x[TARGET].nunique()==2
    train,val,test=[parts[s] for s in ['train','validation','test']]
    out=BASE/'혈압_모델학습_결과'/datetime.now().strftime('%Y%m%d_%H%M%S')
    out.mkdir(parents=True)
    member=df[['ID','ID_fam','psu','kstrata']].copy();member['split']=split
    member.to_csv(out/'데이터분할.csv',index=False,encoding='utf-8-sig')
    summary=pd.DataFrame([{'split':s,'인원':len(x),'정답1':int(x[TARGET].sum()),'조사구수':x.psu.nunique()} for s,x in parts.items()])
    print(summary.to_string(index=False),flush=True)
    best={};records=[]
    for family,setting,est in candidates():
        print('학습:',family,setting,flush=True)
        pipe=Pipeline([('preprocess',preprocessing()),('model',est)])
        with warnings.catch_warnings(record=True) as caught, threadpool_limits(limits=4):
            warnings.simplefilter('always')
            pipe.fit(train[FEATURES],train[TARGET],model__sample_weight=train.wt_itvex/train.wt_itvex.mean())
        p=pipe.predict_proba(val[FEATURES])[:,1]
        pr,re,th=precision_recall_curve(val[TARGET],p,sample_weight=val.wt_itvex)
        f=2*pr[:-1]*re[:-1]/np.maximum(pr[:-1]+re[:-1],1e-12)
        t=float(th[np.argmax(f)])
        metric=scores(val[TARGET],p,t,val.wt_itvex)
        records.append({'model':family,'setting':setting,'threshold':t,'warnings':' | '.join(str(w.message) for w in caught),**metric})
        if family not in best or metric['PR_AP']>best[family]['validation_AP']:
            best[family]={'pipeline':pipe,'threshold':t,'features':FEATURES,'model_name':family,'setting':setting,'validation_AP':metric['PR_AP'],'calibrated':False,'target':TARGET}
        print('검증 가중 AP:',round(metric['PR_AP'],4),flush=True)
    pd.DataFrame(records).to_csv(out/'검증_튜닝비교.csv',index=False,encoding='utf-8-sig')
    winner=max(best,key=lambda k:best[k]['validation_AP']) # 최종 평가를 보기 전에 고정
    results=[];prediction=test[['ID',TARGET,'wt_itvex']].copy()
    for name,bundle in best.items():
        p=bundle['pipeline'].predict_proba(test[FEATURES])[:,1]
        prediction[name+'_probability']=p
        prediction[name+'_prediction']=(p>=bundle['threshold']).astype(int)
        for mode,w in [('unweighted',None),('survey_weighted',test.wt_itvex)]:
            for rule,t in [('validation_F1',bundle['threshold']),('fixed_0.5',0.5)]:
                results.append({'model':name,'weighting':mode,'threshold_rule':rule,'threshold':t,'selected':name==winner,**scores(test[TARGET],p,t,w)})
    p=np.full(len(test),np.average(train[TARGET],weights=train.wt_itvex))
    for mode,w in [('unweighted',None),('survey_weighted',test.wt_itvex)]:
        results.append({'model':'Constant_baseline','weighting':mode,'threshold_rule':'fixed_0.5','threshold':0.5,'selected':False,**scores(test[TARGET],p,0.5,w)})
    result=pd.DataFrame(results)
    result.to_csv(out/'모델성능비교.csv',index=False,encoding='utf-8-sig')
    prediction.to_csv(out/'평가예측.csv',index=False,encoding='utf-8-sig')
    # 파일 수를 줄이기 위해 세 모델과 선택 모델 이름을 한 파일에 보관.
    joblib.dump({'selected_model':winner,'models':best},out/'학습모델.joblib')
    config={'seed':SEED,'selected_model':winner,'features':FEATURES,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'sklearn':sklearn.__version__,'xgboost':xgboost.__version__,'numpy':np.__version__,'pandas':pd.__version__,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    report=['# 혈압 학습 결과','',f'검증 가중 AP로 선택한 모델: {winner}','','## 데이터 분리','',summary.to_string(index=False),'','## 해석','',
        '조사구 단위 5개 묶음에서 학습 3개/검증 1개/평가 1개를 고정 사용. 5겹 교차검증은 아님.',
        '동일 가구·조사구의 세트 간 중복 없음. 혈당 실험과 별도 분할.',
        '전처리는 학습 데이터에서만 학습. 수치 결측 중앙값+결측 표시, 범주 결측 -1 및 원핫 인코딩.',
        '모델 학습은 조사 가중치를 평균 1로 정규화하여 적용. 전처리 통계는 비가중.',
        '각 모델 설정 2개 비교. 모델은 검증 가중 AP, 임계값은 검증 가중 F1 최대 기준.',
        'PR_AP는 average precision. 임상적 기준이 아니며 미보정 확률은 미래 발병 확률이 아님.',
        '정답 0에는 주의혈압·고혈압전단계 포함. 진단/치료 이력 없는 비임신 성인 대상.',
        '불균형 클래스 가중치, 특징 선택, 반복 교차검증, 외부 검증, 확률 보정은 아직 미실시.',
        '평가 데이터 결과로 재튜닝하지 말 것. survey_weighted 혼동행렬은 실제 인원수가 아님.',
        '학습모델.joblib: models에 세 모델 저장, selected_model에 선택 이름 저장.',
        '검증_튜닝비교.csv의 warnings에 미수렴 등 학습 경고 기록.','', '## 실행 설정','',json.dumps(config,ensure_ascii=False,indent=2)]
    (out/'결과요약.md').write_text('\n'.join(report),encoding='utf-8')
    print(result.query("weighting=='unweighted' and threshold_rule=='validation_F1'")[['model','Precision','Recall','F1','ROC_AUC','PR_AP']].to_string(index=False))
    print('선택:',winner,'결과:',out)

if __name__=='__main__':
    main()
