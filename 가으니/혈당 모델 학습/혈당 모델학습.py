"""05번 기초데이터 -> 조사구 분리 -> RF/XGBoost/DNN 학습 및 평가.

실행: .venv/Scripts/python.exe "혈당 모델학습.py"
첫 비교 실험용. 출력 확률은 보정되지 않았으며 미래 발병 확률이 아닙니다.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import warnings
import sys

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_selection import mutual_info_classif
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss,
                             confusion_matrix, f1_score, precision_recall_curve,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits
from xgboost import XGBClassifier


BASE = Path(__file__).resolve().parent
SOURCE = BASE / '05_혈당모델_기초데이터.csv'
SEED = 42
# 입력
NUMERIC = ['age', 'HE_BMI', 'HE_wc', 'HE_sbp', 'HE_dbp']
# 입력
CATEGORICAL = ['sex', 'sm_presnt', 'dr_month', 'pa_aerobic',
               'HE_DMfh1', 'HE_DMfh2', 'HE_DMfh3']
# 입력 전체 
FEATURES = NUMERIC + CATEGORICAL
# 정답 
TARGET = 'target_glucose'


def preprocessing():
    # 후보마다 새 파이프라인을 만들고 학습 데이터에서만 전처리를 학습합니다.
    # 수치 결측: 학습 중앙값. 결측 여부도 추가. 범주 결측: -1 별도 범주.
    return ColumnTransformer([
        ('numeric', Pipeline([
            ('impute', SimpleImputer(strategy='median', add_indicator=True,
                                    keep_empty_features=True)),
            ('scale', StandardScaler()),
        ]), NUMERIC),
        ('category', Pipeline([
            ('impute', SimpleImputer(strategy='constant', fill_value=-1,
                                    keep_empty_features=True)),
            ('encode', OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
        ]), CATEGORICAL),
    ])

# 데이터 읽기 
def load_data(path):
    # 이전 점검에서 저장된 문자열 패딩 NUL도 명시적으로 제거합니다.
    import io
    text = path.read_text(encoding='utf-8-sig').replace('\x00', '')
    df = pd.read_csv(io.StringIO(text), dtype={'ID': str, 'ID_fam': str, 'psu': str})
    required = FEATURES + [TARGET, 'ID', 'ID_fam', 'psu', 'kstrata', 'wt_itvex']
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f'필수 열 누락: {missing}')
    for col in ['ID', 'ID_fam', 'psu']:
        df[col] = df[col].str.strip()
        if df[col].isna().any() or df[col].eq('').any():
            raise ValueError(f'{col}에 빈 값이 있습니다.')
    if df.ID.duplicated().any():
        raise ValueError('개인 ID가 중복됩니다.')
    if not df[TARGET].isin([0, 1]).all() or df[TARGET].nunique() != 2:
        raise ValueError('정답은 0과 1 두 종류여야 합니다.')
    for c in FEATURES + ['wt_itvex']:
        df[c] = pd.to_numeric(df[c], errors='raise')
        if np.isinf(df[c]).any():
            raise ValueError(f'{c}에 무한대가 있습니다.')
    if not df.wt_itvex.gt(0).all():
        raise ValueError('가중치는 모두 양수여야 합니다.')
    if df.groupby('ID_fam').psu.nunique().gt(1).any():
        raise ValueError('한 가구가 여러 조사구에 속합니다.')
    allowed = {'sex': [1, 2], 'HE_DMfh3': [0, 1, 2]}
    for c in CATEGORICAL:
        if not df[c].dropna().isin(allowed.get(c, [0, 1])).all():
            raise ValueError(f'{c}의 범주 코드를 확인하세요.')
    return df

# train, validation, test 로 나누기 
def partition(df):
    # 고정된 5개 그룹 층화 폴드: 0=평가, 1=검증, 2~4=학습.
    # 조사구 크기 차이로 정확한 60/20/20 비율은 아닙니다.
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    fold = np.full(len(df), -1)
    for i, (_, index) in enumerate(cv.split(df[FEATURES], df[TARGET], df.psu)):
        fold[index] = i
    split = np.where(fold == 0, 'test', np.where(fold == 1, 'validation', 'train'))
    frames = {name: df.loc[split == name].copy() for name in ['train', 'validation', 'test']}
    for name, part in frames.items():
        if part[TARGET].nunique() != 2:
            raise ValueError(f'{name}에 두 정답 클래스가 모두 있어야 합니다.')
    for key in ['psu', 'ID_fam', 'ID']:
        sets = [set(part[key]) for part in frames.values()]
        assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]), key
    return frames, split


def metrics(y, probability, threshold, weight=None):
    pred = (np.asarray(probability) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1], sample_weight=weight).ravel()
    return {
        'Accuracy': accuracy_score(y, pred, sample_weight=weight),
        'Precision': precision_score(y, pred, sample_weight=weight, zero_division=0),
        'Recall': recall_score(y, pred, sample_weight=weight, zero_division=0),
        'F1': f1_score(y, pred, sample_weight=weight, zero_division=0),
        'ROC_AUC': roc_auc_score(y, probability, sample_weight=weight),
        'PR_AP': average_precision_score(y, probability, sample_weight=weight),
        'Brier': brier_score_loss(y, probability, sample_weight=weight),
        'TN': float(tn), 'FP': float(fp), 'FN': float(fn), 'TP': float(tp),
    }


def validation_threshold(y, p, weights):
    precision, recall, thresholds = precision_recall_curve(y, p, sample_weight=weights)
    f1 = 2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-12)
    return float(thresholds[int(np.argmax(f1))])

# 모델 설정 준비 
def candidates():
    # RF
    for depth in [5, 10]:
        yield 'RF', f'depth{depth}', RandomForestClassifier(
            n_estimators=300, max_depth=depth, min_samples_leaf=5,
            random_state=SEED, n_jobs=4)
    #XGBoost 
    for depth in [2, 4]:
        yield 'XGBoost', f'depth{depth}', XGBClassifier(
            n_estimators=250, max_depth=depth, learning_rate=0.03,
            subsample=0.8, colsample_bytree=0.8, reg_lambda=5,
            objective='binary:logistic', eval_metric='logloss',
            tree_method='hist', n_jobs=4, random_state=SEED)
    # DNN 
    for layers in [(32, 16), (64, 32)]:
        yield 'DNN', 'layers' + '_'.join(map(str, layers)), MLPClassifier(
            hidden_layer_sizes=layers, activation='relu', alpha=0.01,
            learning_rate_init=0.001, batch_size=128, max_iter=400,
            early_stopping=False, n_iter_no_change=30, random_state=SEED)


def save_training_mi(train, folder):
    # 상호정보량(Information Gain 관련) 참고 순위: 학습 세트만 사용.
    # sklearn MI는 표본가중치를 지원하지 않으므로 이 표는 비가중 탐색용.
    # 이 첫 실험에서는 순위로 변수를 삭제하지 않고 12개 공통 입력을 비교.
    values = train[FEATURES].copy()
    for c in NUMERIC:
        median = values[c].median()
        values[c] = values[c].fillna(0 if pd.isna(median) else median)
    values[CATEGORICAL] = values[CATEGORICAL].fillna(-1)
    score = mutual_info_classif(values, train[TARGET],
                               discrete_features=[c in CATEGORICAL for c in FEATURES],
                               random_state=SEED)
    pd.DataFrame({'feature': FEATURES, 'MI_unweighted': score}).sort_values(
        'MI_unweighted', ascending=False).to_csv(
            folder / '03_학습데이터_MI참고순위.csv', index=False, encoding='utf-8-sig')


def main():
    if tuple(map(int, sklearn.__version__.split('.')[:2])) < (1, 7):
        raise RuntimeError('DNN 표본가중치 학습을 위해 scikit-learn 1.7 이상이 필요합니다.')
    df = load_data(SOURCE)
    parts, split = partition(df)
    train, val, test = (parts[k] for k in ['train', 'validation', 'test'])
    run = BASE / '혈당_모델학습_결과' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    run.mkdir(parents=True)
    print('결과 폴더:', run, flush=True)
    membership = df[['ID', 'ID_fam', 'psu', 'kstrata']].copy()
    membership['split'] = split
    membership.to_csv(run / '01_데이터분할.csv', index=False, encoding='utf-8-sig')
    rows = [{'split': name, 'rows': len(p), 'positive': int(p[TARGET].sum()),
             'negative': int((1-p[TARGET]).sum()), 'psu_count': p.psu.nunique(),
             'positive_fraction': p[TARGET].mean(),
             'weighted_positive_fraction': np.average(p[TARGET], weights=p.wt_itvex)}
            for name, p in parts.items()]
    summary = pd.DataFrame(rows)
    summary.to_csv(run / '02_분할요약.csv', index=False, encoding='utf-8-sig')
    print(summary.to_string(index=False), flush=True)
    save_training_mi(train, run)
    # 조사 가중치는 평균 1로 정규화. 클래스 가중치와 혼동하지 않음.
    train_weight = train.wt_itvex / train.wt_itvex.mean()
    records, best = [], {}
    for family, variant, estimator in candidates():
        print(f'학습 중: {family} / {variant}', flush=True)
        pipe = Pipeline([('preprocess', preprocessing()), ('model', estimator)])
        with warnings.catch_warnings(record=True) as caught, threadpool_limits(limits=4):
            warnings.simplefilter('always', ConvergenceWarning)
            pipe.fit(train[FEATURES], train[TARGET], model__sample_weight=train_weight)
        warning_text = ' | '.join(str(w.message) for w in caught)
        probability = pipe.predict_proba(val[FEATURES])[:, 1]
        threshold = validation_threshold(val[TARGET], probability, val.wt_itvex)
        score = metrics(val[TARGET], probability, threshold, val.wt_itvex)
        records.append({'model': family, 'variant': variant, 'threshold': threshold,
                        'warning': warning_text, **score})
        if family not in best or score['PR_AP'] > best[family]['validation_AP']:
            best[family] = {'pipeline': pipe, 'threshold': threshold, 'features': FEATURES,
                            'model_name': family, 'variant': variant,
                            'validation_AP': score['PR_AP'], 'calibrated': False,
                            'target': '조사시점 당뇨병 범위 혈당 검사 결과 해당 여부',
                            'input_scope': '성인·비임신·당뇨병 진단/약물치료 이력 없음'}
        print(f"  검증 가중 AP={score['PR_AP']:.4f}, F1={score['F1']:.4f}", flush=True)
        pd.DataFrame(records).to_csv(run / '04_검증_튜닝비교.csv', index=False, encoding='utf-8-sig')

    # 평가 데이터를 보기 전에 최종 모델과 각 모델의 임계값을 확정.
    winner = max(best, key=lambda key: best[key]['validation_AP'])
    result_rows = []
    for family, bundle in best.items():
        joblib.dump(bundle, run / f'{family}_model.joblib')
        p = bundle['pipeline'].predict_proba(test[FEATURES])[:, 1]
        for mode, weight in [('unweighted', None), ('survey_weighted', test.wt_itvex)]:
            for rule, threshold in [('validation_F1', bundle['threshold']), ('fixed_0.5', 0.5)]:
                result_rows.append({'model': family, 'weighting': mode, 'threshold_rule': rule,
                                    'threshold': threshold, 'selected_by_validation': family == winner,
                                    **metrics(test[TARGET], p, threshold, weight)})
        predicted = test[['ID', TARGET, 'wt_itvex']].copy()
        predicted['uncalibrated_probability'] = p
        predicted['prediction'] = (p >= bundle['threshold']).astype(int)
        predicted.to_csv(run / f'{family}_평가예측.csv', index=False, encoding='utf-8-sig')
        # 확률 구간별 관측률: 사후 평가용, 이 결과로 모델을 다시 선택하지 않음.
        bins = pd.DataFrame({'p': p, 'y': test[TARGET].to_numpy(), 'w': test.wt_itvex.to_numpy()})
        bins['bin'] = pd.cut(bins.p, np.linspace(0, 1, 11), include_lowest=True)
        calibration = []
        for interval, group in bins.groupby('bin', observed=True):
            calibration.append({'bin': str(interval), 'n': len(group),
                                'mean_prediction': np.average(group.p, weights=group.w),
                                'observed_fraction': np.average(group.y, weights=group.w)})
        pd.DataFrame(calibration).to_csv(run / f'{family}_확률점검.csv', index=False, encoding='utf-8-sig')
    # 학습 유병 비율을 항상 반환하는 단순 기준선. 0.5에서는 모두 음성.
    constant = np.full(len(test), np.average(train[TARGET], weights=train.wt_itvex))
    for mode, weight in [('unweighted', None), ('survey_weighted', test.wt_itvex)]:
        result_rows.append({'model': 'Constant_baseline', 'weighting': mode,
                            'threshold_rule': 'fixed_0.5', 'threshold': 0.5,
                            'selected_by_validation': False,
                            **metrics(test[TARGET], constant, 0.5, weight)})
    results = pd.DataFrame(result_rows)
    results.to_csv(run / '05_최종평가_모델비교.csv', index=False, encoding='utf-8-sig')
    joblib.dump(best[winner], run / 'best_model.joblib')
    manifest = {'seed': SEED, 'selected_model': winner,
                'selection_rule': 'validation survey-weighted average precision',
                'threshold_rule': 'validation survey-weighted F1 maximum',
                'features': FEATURES, 'source': str(SOURCE),
                'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'python': sys.version, 'sklearn': sklearn.__version__,
                'xgboost': xgboost.__version__, 'pandas': pd.__version__,
                'numpy': np.__version__, 'joblib': joblib.__version__}
    (run / '실험설정.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    notes = f'''검증 데이터로 선택된 첫 실험 모델: {winner}
RF/XGBoost/DNN 각 2개 설정을 검증 AP로 비교한 소규모 튜닝입니다.
DNN은 은닉층 두 개의 MLP이며 학습 미수렴 경고는 04번 파일에 기록합니다.
전처리는 학습 데이터에서만 학습했습니다. 임퓨팅/스케일링은 비가중,
모델 fit은 평균 1로 정규화한 조사 가중치를 사용했습니다.
조사구 단위 약 60/20/20 분할이며 가구 중복도 검사했습니다.
이 그룹 층화는 정답 비율을 고려한 것으로 조사설계 층 kstrata 층화와 다릅니다.
평가 지표는 비가중/조사가중을 모두 저장합니다. 가중 혼동행렬은 인원수가 아닙니다.
PR_AP는 average precision이며 사다리꼴 PR-AUC와 구분합니다.
임계값은 검증 F1 최대 기준의 연구용 설정입니다. 임상적 기준이 아닙니다.
평가 세트 결과를 보고 모델이나 임계값을 다시 고르면 평가 누출입니다.
MI 순위는 비가중 탐색용이며 이번 실행에서 특징 선택으로 사용하지 않았습니다.
확률 보정은 아직 하지 않았습니다. 확률에 100을 곱해 검증된 위험점수로 제공하지 마세요.
현재 결과는 한 해 자료의 한 번의 내부 분할 평가입니다. 외부 검증, 반복 그룹 교차검증,
조사설계를 고려한 신뢰구간 및 하위집단 평가는 후속 단계입니다.
best_model.joblib은 전처리기와 모델, 입력 변수, 임계값을 함께 담고 있습니다.
가족력 HE_DMfh3의 2는 비해당/외동, 0은 없음, 1은 있음입니다.
사용자가 모르는 입력은 NaN으로 전달합니다. 나이 등 적용 대상 조건은 호출 전 확인합니다.
'''
    (run / '결과읽는법.txt').write_text(notes, encoding='utf-8')
    view = results[(results.weighting == 'unweighted') &
                   (results.threshold_rule == 'validation_F1')]
    print('\n최종 평가 (비가중, 검증에서 정한 임계값):', flush=True)
    print(view[['model', 'Accuracy', 'Precision', 'Recall', 'F1', 'ROC_AUC', 'PR_AP']].to_string(index=False))
    print('\n검증 기준 선택 모델:', winner)
    print('저장 완료:', run)


if __name__ == '__main__':
    main()
