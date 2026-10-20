"""2024 KNHANES 혈압 스크리닝용 기초 전처리. 원본 및 혈당 결과는 수정하지 않음.
실행: .venv/Scripts/python.exe "혈압 전처리.py"
근거: 제9기 이용지침서 PDF 110, 182~185쪽, 고혈압 기준 PDF 52쪽.
"""
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
import pyreadstat

BASE = Path(__file__).resolve().parent
SOURCE = BASE / 'KNHANES 원시 자료' / 'HN24_ALL.sav'
OUTPUT = BASE / '혈압_전처리_결과'
FEATURES = ['age', 'sex', 'HE_BMI', 'HE_wc', 'sm_presnt', 'dr_month',
            'pa_aerobic', 'HE_HPfh1', 'HE_HPfh2', 'HE_HPfh3']
MANAGEMENT = ['ID', 'ID_fam', 'psu', 'kstrata', 'wt_itvex']
COLUMNS = list(dict.fromkeys(MANAGEMENT + FEATURES +
                            ['DI1_dg', 'DI1_2', 'HE_prg', 'HE_sbp', 'HE_dbp', 'HE_HP']))


def prepare_blood_pressure(raw):
    """정해진 코드/기준만 적용. 결측 대체·특징 선택·학습은 하지 않음."""
    data = raw[COLUMNS].copy()
    for c in ['ID', 'ID_fam', 'psu']:
        data[c] = data[c].astype('string').str.replace('\x00', '', regex=False).str.strip()
        data[c] = data[c].replace('', pd.NA)
    for c in set(COLUMNS) - {'ID', 'ID_fam', 'psu'}:
        data[c] = pd.to_numeric(data[c], errors='raise').replace([np.inf, -np.inf], np.nan)
    # 예상 밖 코드는 추측해서 처리하지 않고 중단.
    allowed = {'sex': [1, 2], 'DI1_dg': [0, 1, 8, 9],
               'DI1_2': [1, 2, 3, 4, 5, 8, 9], 'HE_prg': [0, 1, 8],
               'HE_HP': [1, 2, 3, 4], 'HE_HPfh1': [0, 1, 9],
               'HE_HPfh2': [0, 1, 9], 'HE_HPfh3': [0, 1, 8, 9],
               'sm_presnt': [0, 1], 'dr_month': [0, 1], 'pa_aerobic': [0, 1]}
    for c, values in allowed.items():
        unexpected = set(data[c].dropna().unique()) - set(values)
        if unexpected:
            raise ValueError(f'{c} 예상 밖 코드: {unexpected}. 지침서 확인 필요.')

    flow = []
    def keep(condition, description):
        nonlocal data
        before = len(data)
        data = data.loc[condition.fillna(False)].copy()
        flow.append((description, before - len(data), len(data)))

    keep(data.age.ge(19), '만 19세 이상')
    keep(data.DI1_dg.eq(0), '고혈압 의사진단 없음 확인')
    # 1~4는 복용 빈도가 달라도 모두 약물 사용. 9/결측은 미확인.
    keep(data.DI1_2.isin([5, 8]), '혈압약 비복용 또는 미진단자의 문항 비해당')
    # 비임신 성인 모델이라는 연구 범위 제한. 공식 HE_HP 정의 자체의 조건과 구분.
    keep((data.sex.eq(1) & data.HE_prg.eq(8)) |
         (data.sex.eq(2) & data.HE_prg.eq(0)), '남성 비해당 또는 여성 비임신 확인')
    keep(data.HE_sbp.gt(0) & data.HE_dbp.gt(0), '수축기·이완기 최종 혈압 모두 양수')
    keep(data.wt_itvex.gt(0), '건강설문-검진 가중치 양수')
    keep(data[['ID', 'ID_fam', 'psu', 'kstrata']].notna().all(axis=1), '식별·표본설계 정보 존재')
    if data.empty:
        raise ValueError('대상자가 없습니다.')
    if data.ID.duplicated().any():
        raise ValueError('개인 ID 중복. 자동 삭제하지 않습니다.')
    if data.groupby('ID_fam').psu.nunique().gt(1).any():
        raise ValueError('하나의 가구가 여러 조사구에 기록되어 있습니다.')
    if data.HE_sbp.le(data.HE_dbp).any():
        raise ValueError('수축기 <= 이완기인 혈압이 있습니다. 원자료를 검토하세요.')

    # 최종 혈압은 원자료 제공값(2·3차 평균). 단회 조사 기준 해당 여부.
    data['target_bp'] = (data.HE_sbp.ge(140) | data.HE_dbp.ge(90)).astype(int)
    known = data.HE_HP.isin([1, 2, 3, 4])
    differences = (data.loc[known, 'target_bp'] != data.loc[known, 'HE_HP'].eq(4).astype(int)).sum()
    if differences:
        raise ValueError(f'공식 고혈압 분류와 {differences}건 불일치. 저장을 중단합니다.')

    # 가족력: 모름은 결측. 외동은 별도 범주 2로 유지하며 순서형으로 사용하지 않음.
    for c in ['HE_HPfh1', 'HE_HPfh2']:
        data[c] = data[c].replace({9: np.nan})
    data['HE_HPfh3'] = data['HE_HPfh3'].replace({8: 2, 9: np.nan})
    for c in ['HE_BMI', 'HE_wc']:
        if data[c].dropna().le(0).any():
            raise ValueError(f'{c}에 0 이하 값 존재. 임의 대체 전 확인 필요.')
    model = data[MANAGEMENT + FEATURES + ['target_bp']].copy()
    counts = model.target_bp.value_counts().reindex([0, 1], fill_value=0)
    missing = [(c, int(model[c].isna().sum()), float(model[c].isna().mean()*100)) for c in FEATURES]
    return model, flow, counts, missing, int(known.sum())


def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(f'원자료 위치 확인: {SOURCE}')
    raw, meta = pyreadstat.read_sav(str(SOURCE), usecols=COLUMNS,
                                   apply_value_formats=False, user_missing=True)
    model, flow, counts, missing, compared = prepare_blood_pressure(raw)
    # 모든 확인이 끝난 뒤 저장. 재실행 시 두 결과 파일만 갱신.
    OUTPUT.mkdir(exist_ok=True)
    model.to_csv(OUTPUT / '혈압모델_기초데이터.csv', index=False, encoding='utf-8-sig')
    lines = [
        '# 혈압 전처리 요약', '',
        f'- 원자료: {SOURCE}', f'- 전체 원자료: {len(raw):,}명',
        f'- 분석 대상: {len(model):,}명 / {len(model.columns)}개 열',
        f'- 정답 1: {counts[1]:,}명 ({counts[1]/len(model)*100:.2f}%, 비가중)',
        f'- 정답 0: {counts[0]:,}명',
        f'- 공식 HE_HP와 비교: {compared:,}명, 불일치 0명',
        f'- 공식 분류 미확인: {len(model)-compared:,}명', '',
        '## 대상 및 정답', '',
        '만 19세 이상, 고혈압 의사진단 없음, 혈압약 비복용/문항 비해당, 비임신 대상.',
        '1 = 최종 수축기혈압 >=140 mmHg 또는 이완기혈압 >=90 mmHg.',
        '0 = 두 기준 미만. 주의혈압·고혈압전단계도 포함하며 정상 확진을 뜻하지 않음.',
        '조사 시점의 혈압 기준 해당 여부이며 임상적 확진이나 미래 발병을 예측하지 않음.',
        '혈압·신체계측·설문만 사용하므로 공복시간/혈당 검사 여부로 대상을 제한하지 않음.',
        '혈당 모델의 선정 대상과 다르므로 혈당용 05 파일이 아닌 SAV에서 새로 선정.', '',
        '## 대상자 선정', '', '| 단계 | 제외 인원 | 남은 인원 |', '|---|---:|---:|',
    ]
    lines += [f'| {step} | {removed} | {remaining} |' for step, removed, remaining in flow]
    lines += ['', '## 입력 변수와 결측', '', '| 변수 | 의미 | 결측 인원 | 결측률(%) |', '|---|---|---:|---:|']
    lines += [f'| {c} | {meta.column_names_to_labels.get(c, c)} | {n} | {pct:.2f} |' for c,n,pct in missing]
    lines += ['', '## 사용 방법 및 처리 규칙', '',
        '입력 X: ' + ', '.join(FEATURES),
        '정답 y: target_bp',
        '관리용(입력 아님): ' + ', '.join(MANAGEMENT),
        '부/모 가족력: 0 없음, 1 있음, 9 -> 결측.',
        '형제자매 가족력: 0 없음, 1 있음, 8 -> 2(외동/비해당), 9 -> 결측.',
        '혈압, 공식 HE_HP, 본인 고혈압 진단·치료 문항은 정답 누출 방지를 위해 입력에서 제외.',
        '입력 결측은 남겨 둠. 학습/검증/평가 분리 후 학습 세트에서만 대체 기준을 학습할 것.',
        '가중치는 원값 보존만 했으며 아직 가중 학습이나 성능평가는 하지 않음.',
        '동일 가구·조사구가 학습과 평가에 겹치지 않도록 관리 정보를 보존.',
        '연령 80은 80세 이상 상단코딩. 정확한 고령 나이로 해석하지 않음.',
        '이상치에 대한 임의 상한 절단은 하지 않음. 분포 및 선택 편향 검토는 후속 단계.',
        '기존 혈당 학습 코드는 혈압 변수가 다르므로 이 CSV에 그대로 사용할 수 없음.', '',
        '## 근거', '',
        '국민건강영양조사 제9기(2022–2024) 원시자료 이용지침서:',
        '- PDF 110쪽(인쇄 102쪽): DI1_dg 및 DI1_2 코드',
        '- PDF 182~184쪽(인쇄 174~176쪽): 임신 및 가족력 코드',
        '- PDF 185쪽(인쇄 177쪽), 52쪽(인쇄 44쪽): 최종 혈압 및 고혈압 분류',
        f'- 원자료 SHA256: {hashlib.sha256(SOURCE.read_bytes()).hexdigest()}',
    ]
    (OUTPUT / '전처리요약.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(f'전체 {len(raw):,}명 -> 분석 대상 {len(model):,}명')
    print(f'정답 1: {counts[1]:,}명 / 정답 0: {counts[0]:,}명')
    print(f'공식 분류 비교 {compared:,}명, 불일치 0명')
    print('저장 위치:', OUTPUT)


if __name__ == '__main__':
    main()
