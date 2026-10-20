from pathlib import Path
import pandas as pd
import pyreadstat

# HN24_ALL.sav 파일 읽기 
source = Path(r'C:\Users\rkdms\health-rag-agent\가으니\자료\KNHANES 원시 자료\HN24_ALL.sav')

assert source.is_file(), f'파일 위치를 확인하세요: {source}'

# 변수 선택 
columns = ['age', 'DE1_dg', 'DE1_31', 'DE1_32', 'HE_prg', 'HE_fst', 'HE_glu', 
           'HE_HbA1c', 'HE_DM_HbA1c', 'sex', 'HE_ht', 'HE_wt', 'HE_BMI', 'HE_wc', 
           'HE_sbp', 'HE_dbp', 'sm_presnt', 'dr_month', 'pa_aerobic', 'HE_DMfh1', 
           'HE_DMfh2', 'HE_DMfh3', 'ID', 'ID_fam', 'psu', 'kstrata', 'wt_itvex']

# 데이터 읽기 
df, meta = pyreadstat.read_sav(str(source), usecols=columns, apply_value_formats=False, user_missing=True)

print("전체 응답자 수:", len(df))
print("선택한 변수 수: ", len(df.columns))

# 데이터 설명 표 
dictionary = pd.DataFrame([{'variable': c, 'label': meta.column_names_to_labels.get(c, ''), 
                            'value_labels': str(meta.variable_value_labels.get(c, {})), 
                            'declared_missing': str(meta.missing_ranges.get(c, []))} for c in df.columns])

print(dictionary.to_string(index=False))

# 빈칸 확인 
summary = pd.DataFrame({'variable': df.columns, 'dtype': [str(df[c].dtype) for c in df], 
                        'blank_count': [df[c].isna().sum() for c in df], 'blank_percent': [round(df[c].isna().mean()*100, 2) 
                                                                                           for c in df], 
                        'unique_count': [df[c].nunique(dropna=True) for c in df]})
print(summary.to_string(index=False))

for c in ['DE1_dg','DE1_31','DE1_32','HE_prg','HE_DM_HbA1c','sm_presnt','dr_month','pa_aerobic','HE_DMfh1','HE_DMfh2','HE_DMfh3']:
    print('\n', c, meta.column_names_to_labels.get(c,''))
    print(df[c].value_counts(dropna=False).sort_index().to_string())

# 성인 응답, 검사 수치 확인 
adult = df.loc[df['age'].ge(19)].copy()
print('19세 이상 응답자:',len(adult))
# 중복 갯수 세기 
print('개인 ID 중복 행:',df['ID'].duplicated().sum())
print(adult[['HE_fst','HE_glu','HE_HbA1c','HE_BMI','HE_wc','HE_sbp','HE_dbp','wt_itvex']].describe().T.to_string())
print('혈당·당화혈색소 모두 빈칸이 아닌 성인:',adult[['HE_glu','HE_HbA1c']].notna().all(axis=1).sum())
print('위 숫자는 공복 조건·특수 코드 검증 전 집계입니다.')


result_dir = Path(__file__).resolve().parent / '혈당_전처리_점검결과'
result_dir.mkdir(exist_ok=True)
dictionary.to_csv(result_dir/'01_변수와코드.csv',index=False,encoding='utf-8-sig')
summary.to_csv(result_dir/'02_빈칸현황.csv',index=False,encoding='utf-8-sig')

# 성인 대상 주요 응답 코드별 인원수 저장
check_columns = [
    'DE1_dg',       # 당뇨병 진단 여부
    'DE1_31',      # 인슐린 주사
    'DE1_32',      # 당뇨병약
    'HE_prg',      # 임신 여부
    'HE_fst',      # 공복시간
    'HE_DM_HbA1c', # 당뇨병 유병 분류
    'HE_DMfh1',    # 아버지 당뇨병 가족력
    'HE_DMfh2',    # 어머니 당뇨병 가족력
    'HE_DMfh3'     # 형제자매 당뇨병 가족력
]

rows = []

for column in check_columns:
    counts = adult[column].value_counts(dropna=False).sort_index()

    for value, count in counts.items():
        rows.append({
            '변수명': column,
            '변수설명': meta.column_names_to_labels.get(column, ''),
            '응답값': '빈칸' if pd.isna(value) else value,
            '성인_인원수': int(count)
        })

code_counts = pd.DataFrame(rows)

code_counts.to_csv(
    result_dir / '03_성인_응답코드별인원.csv',
    index=False,
    encoding='utf-8-sig'
)

print('성인 응답 코드별 인원수 저장 완료')
print('저장 위치:', result_dir.resolve())



# 전처리 
# raw : 함수가 전달받은 원자료
# data : 원자료를 복사한 작업용 표
# flow : 단계별 제외 인원을 기록할 목록
def prepare_glucose_data(raw):
    data = raw.copy()
    flow = []

    def keep(condition, reason):
        nonlocal data
        before = len(data)
        data = data.loc[condition.fillna(False)].copy()
        flow.append({'단계': reason, '이전인원': before,
                     '제외인원': before - len(data), '남은인원': len(data)})


    # 분석에 남길 사람만 조견별로 구분 
    keep(data['age'].ge(19), '만 19세 이상')
    # DE1_dg: 0 없음, 1 있음, 8 소아/청소년 비해당, 9 모름
    keep(data['DE1_dg'].eq(0), '당뇨병 의사진단 없음이 확인됨')
    # 진단 없음 대상에서는 치료 문항의 8(비해당)을 정상 건너뛰기로 인정.
    # 치료 1, 모름 9, 빈칸은 제외. 8을 데이터 전체에서 0으로 바꾸지는 않음.

    #DE1_31 -> 인슐린 주사 사용 여부 DE1_32 -> 당뇨병약 사용 여부 
    keep(data['DE1_31'].isin([0, 8]) & data['DE1_32'].isin([0, 8]),
         '인슐린/당뇨병약 사용 응답 및 미확인 제외')
    keep((data['sex'].eq(1) & data['HE_prg'].eq(8)) |
         (data['sex'].eq(2) & data['HE_prg'].eq(0)),
         '남성 비해당 또는 여성 비임신 확인')
    # 첫 버전은 양성/음성 모두 같은 검사 완비 조건을 적용.
    # HbA1c만 있어도 판정 가능한 일부 응답자는 이번 분석에서 제외됨.
    for col in ['HE_fst', 'HE_glu', 'HE_HbA1c', 'wt_itvex']:
        data[col] = pd.to_numeric(data[col], errors='raise').replace(
            [float('inf'), -float('inf')], float('nan'))
    keep(data['HE_fst'].ge(8), '공복 8시간 이상 확인')
    keep(data['HE_glu'].gt(0) & data['HE_HbA1c'].gt(0),
         '공복혈당과 당화혈색소 모두 유효한 양수')
    keep(data['wt_itvex'].gt(0), '건강설문-검진 가중치 양수')
    keep(data[['ID', 'ID_fam', 'psu', 'kstrata']].notna().all(axis=1),
         '개인/가구/조사구/층화 정보 존재')
    if data['ID'].duplicated().any():
        raise ValueError('개인 ID 중복이 있습니다. 원자료를 확인하세요.')
    if data.empty:
        raise ValueError('조건을 만족하는 대상자가 없습니다.')

    # y=0은 정상 확진이 아님: 당뇨병전단계도 포함한 기준 비해당.
    data['target_glucose'] = (
        data['HE_glu'].ge(126) | data['HE_HbA1c'].ge(6.5)
    ).astype('int64')

    # 공식 유병 분류는 입력에서 제외하고 결과 점검에만 사용.
    available = data['HE_DM_HbA1c'].isin([1, 2, 3])
    disagreement = int((data.loc[available, 'target_glucose'] !=
                       data.loc[available, 'HE_DM_HbA1c'].eq(3).astype(int)).sum())
    if disagreement:
        raise ValueError(f'공식 당뇨병 유병 분류와 {disagreement}건 불일치. 저장 전 확인 필요.')

    # 코드 매핑: 모름은 결측으로, 형제자매 비해당은 별도 범주로 보존.
    for col in ['HE_DMfh1', 'HE_DMfh2']:
        unexpected = set(data[col].dropna().unique()) - {0, 1, 9}
        if unexpected:
            raise ValueError(f'{col} 예상 밖 코드: {unexpected}')
        data[col] = data[col].replace({9: float('nan')})
    unexpected = set(data['HE_DMfh3'].dropna().unique()) - {0, 1, 8, 9}
    if unexpected:
        raise ValueError(f'HE_DMfh3 예상 밖 코드: {unexpected}')
    data['HE_DMfh3'] = data['HE_DMfh3'].replace({8: 2, 9: float('nan')})

    features = ['age', 'sex', 'HE_BMI', 'HE_wc', 'HE_sbp', 'HE_dbp',
                'sm_presnt', 'dr_month', 'pa_aerobic',
                'HE_DMfh1', 'HE_DMfh2', 'HE_DMfh3']
    for col in ['sm_presnt', 'dr_month', 'pa_aerobic']:
        unexpected = set(data[col].dropna().unique()) - {0, 1}
        if unexpected:
            raise ValueError(f'{col} 예상 밖 코드: {unexpected}')
    # 입력 결측은 그대로 보존. 데이터 분리 후 학습 세트에서 대체 규칙을 학습.
    missing = pd.DataFrame({
        '입력변수': features,
        '결측인원': [int(data[c].isna().sum()) for c in features],
        '결측률_퍼센트': [round(data[c].isna().mean()*100, 2) for c in features]
    })
    management = ['ID', 'ID_fam', 'psu', 'kstrata', 'wt_itvex']
    model_data = data[management + features + ['target_glucose']].copy()
    labels = (model_data['target_glucose'].value_counts()
              .reindex([0, 1], fill_value=0).rename_axis('target_glucose')
              .reset_index(name='인원'))
    labels['비율_퍼센트_가중치미적용'] = labels['인원'] / len(data) * 100
    return model_data, pd.DataFrame(flow), missing, labels, int(available.sum())

model_data, flow, feature_missing, label_counts, compared = prepare_glucose_data(df)
flow.to_csv(result_dir / '04_대상자선정흐름.csv', index=False, encoding='utf-8-sig')
model_data.to_csv(result_dir / '05_혈당모델_기초데이터.csv', index=False, encoding='utf-8-sig')
feature_missing.to_csv(result_dir / '06_입력변수_결측현황.csv', index=False, encoding='utf-8-sig')
label_counts.to_csv(result_dir / '07_정답분포.csv', index=False, encoding='utf-8-sig')
notes = """혈당 모델 기초 전처리 기록
대상: 만 19세 이상, 당뇨병 의사진단 없음, 약물 사용 없음/문항 비해당, 비임신.
검사: 공복 8시간 이상이며 공복혈당과 당화혈색소 모두 유효한 양수.
정답 1: 공복혈당 >=126 mg/dL 또는 당화혈색소 >=6.5%.
정답 0: 두 기준 모두 미만. 당뇨병전단계도 포함하며 건강/정상 확진을 뜻하지 않음.
조사 시점의 검사 기준 해당 여부이며 미래 발병이나 임상적 확진을 예측하지 않음.
근거: 제9기 원시자료 이용지침서 PDF 112~113, 182~184, 188쪽.
가족력: 부모 9는 결측. 형제자매 8은 2(비해당/외동)로 매핑, 9는 결측.
형제자매 가족력 2는 순서 없는 범주이며 이후 범주형 인코딩 대상.
입력 결측값은 보존. 평균 대체, 스케일링, 특징 선택, 데이터 분리, 학습은 미실시.
05 파일의 ID, ID_fam, psu, kstrata, wt_itvex, target_glucose는 예측 입력이 아님.
공복혈당, HbA1c, 공식 당뇨병 유병변수, 본인 진단/치료변수는 입력 파일에서 제외.
가중치 wt_itvex는 원값 보존. 아직 학습이나 가중 성능평가에 적용하지 않음.
결측으로 인한 표본 선택 편향과 입력 측정값의 이상 여부는 후속 검토 필요.
연령은 공개자료의 상단코딩을 그대로 보존하며 정확한 고령 나이로 해석하지 않음.
"""
(result_dir / '08_전처리설명.txt').write_text(notes, encoding='utf-8')
print('\n=== 대상자 선정 결과 ===')
print(flow.to_string(index=False))
print('\n=== 정답 분포 (가중치 미적용) ===')
print(label_counts.to_string(index=False))
print(f'공식 유병 분류와 비교: {compared}명, 불일치 0명')
print('기초 데이터 저장 완료. 입력 결측 대체와 모델 학습은 아직 하지 않았습니다.')
print('저장 위치:', result_dir.resolve())
