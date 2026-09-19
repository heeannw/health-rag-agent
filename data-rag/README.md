# 데이터 / RAG 엔지니어 (담당: 원희)

## 담당 데이터
- 질병관리청 국가건강정보포털 (건강정보검색 API)
- 법제처 국가법령정보 공유서비스
- 한국사회보장정보원 중앙부처·지자체 복지서비스
- 건강보험심사평가원 병원평가정보서비스
- 복지사업 월별 급여지급 현황
- 전국치매센터표준데이터 / 장기요양기관 검색 서비스

## 업무
- 공공데이터포털 활용신청 및 API 연동, 원문 크롤링/정제
- 텍스트 청킹(chunking) 전략 수립, 출처 메타데이터(법령 조항·서비스명 등) 태깅
- BGE-M3 임베딩 생성, 벡터DB(Chroma/Weaviate) 구축
- 검색기 성능 튜닝 (Recall@k, 하이브리드 검색 등)

## 폴더 구조
```
data-rag/
├── config.py              # .env에서 API 키 로드
├── requirements.txt
├── .env.example           # 필요한 키 목록 (실제 키는 .env에 본인이 채워넣기)
├── collectors/              # 소스별 공공데이터 API 클라이언트
│   ├── base.py              # 공통 요청 헬퍼 (XML/JSON/odcloud)
│   ├── law.py               # 법제처 법령정보
│   ├── hospital.py          # 병원평가정보
│   ├── ltc_institution.py   # 장기요양기관 검색
│   ├── welfare_central.py   # 중앙부처복지서비스
│   ├── welfare_local.py     # 지자체복지서비스
│   ├── dementia_center.py   # 전국치매센터
│   └── welfare_payment.py   # 복지사업 급여지급현황 (odcloud)
└── pipeline/                # 정제 -> 청킹 -> 임베딩 -> 벡터DB 적재
    ├── clean.py              # 텍스트 정제
    ├── normalize.py          # API 응답 -> 공통 Document 스키마
    ├── chunk.py              # 청킹 + Document -> 청크 레코드 변환
    ├── embed.py              # BGE-M3 임베딩
    ├── vectorstore.py        # Chroma 저장/조회
    ├── build_index.py        # 전체 파이프라인 실행 스크립트
    ├── search.py             # 검색 테스트 스크립트
    └── manual_check.py       # API 실호출 기반 파이프라인 점검 스크립트
```

## 실행 방법

### 1. 환경 설정
```bash
cd data-rag
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

`.env.example`을 참고해서 `.env` 파일을 만들고 본인이 발급받은 API 키를 채워 넣는다 (`.env`는 git에 커밋되지 않음).
```
DATA_GO_KR_API_KEY=...
KDCA_HEALTH_API_KEY=...
```

### 2. 벡터DB 인덱스 빌드
공공데이터 API를 호출해서 문서를 수집 → 정제 → 청킹 → BGE-M3 임베딩 → Chroma에 적재한다.
```bash
python -m pipeline.build_index
```
- 최초 실행 시 BGE-M3 모델(약 2GB)을 자동으로 다운로드하므로 시간이 걸린다.
- 결과물(`chroma_db/`)은 로컬에만 생성되고 git에는 올라가지 않는다 — **팀원 각자 로컬에서 한 번씩 실행해야 함**.
- 소스별 수집 건수는 `pipeline/build_index.py` 상단의 상수(`CENTRAL_WELFARE_LIMIT` 등)로 조절한다. 중앙부처복지서비스는 API 일일 트래픽이 100건뿐이라 보수적으로 제한되어 있으니 값을 올릴 때 주의.

### 3. 검색 테스트
```bash
python -m pipeline.search "65세 이상 받을 수 있는 의료 혜택"
```
질의를 BGE-M3로 임베딩해 Chroma에서 유사도 상위 5건을 출력한다.

## 알려진 제약
- 법제처 API는 신청한 것이 "목록조회"라 조문 원문은 못 가져오고 법령명·소관부처·시행일자 등 메타데이터만 확보됨. 조문 본문이 필요하면 `open.law.go.kr`에 별도로 OC(이메일ID 기반) 인증키를 신청해야 함.
- 질병관리청 건강정보검색 API는 별도 사이트(health.kdca.go.kr) 승인 대기 중. 승인되면 `.env`에 `KDCA_HEALTH_API_KEY`를 채우고 `collectors/`에 어댑터 추가 예정.
- 장기요양기관 검색 목록조회(`getLtcInsttSeachList02`)는 필수 검색조건(지역코드 등)이 아직 확인되지 않아 청구그린기관 목록만 사용 중.
