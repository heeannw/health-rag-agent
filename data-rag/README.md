# 1. RAG·챗봇 담당 (담당: 원희)

## 담당 데이터
- 법제처 국가법령정보 공유서비스 (메타데이터만, 조문 원문은 범위 제외)
- 한국사회보장정보원 중앙부처·지자체 복지서비스
- 건강보험심사평가원 병원평가정보서비스
- 복지사업 월별 급여지급 현황
- 전국치매센터표준데이터 / 장기요양기관 검색 서비스
- (미사용) 질병관리청 국가건강정보포털 — HTML 위젯형 API라 스크립트 호출 차단, 범위 제외

## 업무
- 공공데이터포털 활용신청 및 API 연동, 원문 크롤링/정제
- 텍스트 청킹(chunking) 전략 수립, 출처 메타데이터(법령 조항·서비스명 등) 태깅
- BGE-M3 임베딩 생성, 벡터DB(Chroma) 구축
- 검색기 성능 튜닝 (Recall@k, 하이브리드 검색 등)
- **LLM 답변 생성** — 검색된 청크를 LLM에 넣어 자연어 답변으로 생성 (신규 추가 범위)
- **근거·출처 표시** — 생성된 답변에 출처 메타데이터(법령명·복지서비스명 등)를 노출 (신규 추가 범위)

## 신규 추가 범위 (역할 개편 반영)
기존에는 RAG 검색까지만 담당이었으나(`pipeline/search.py`는 검색된 청크를 그대로 출력할 뿐 LLM 호출이 없음), 역할 개편으로 LLM 답변 생성과 출처 표시까지 이 담당으로 흡수되었다. 추가로 해야 할 작업:
- LLM 선정 및 연동 (Upstage Solar / GPT / Claude 등) — 검색 결과 → 프롬프트 → 자연어 답변
- 답변 안에 출처를 표시하는 포맷/프롬프트 설계
- 소현(웹·지도·통합)과 API 응답 스키마 협의 — 예: `{"answer": str, "sources": [{"title":, "source":, ...}]}`
- 가은(매칭·데이터)과 데이터 중복 수집 방지 — 이미 만든 `collectors/`를 공유해서 혜택·기관 매핑 테이블 쪽에서 재사용

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
└── pipeline/                # 정제 -> 청킹 -> 임베딩 -> 벡터DB 적재 -> 검색
    ├── clean.py              # 텍스트 정제
    ├── normalize.py          # API 응답 -> 공통 Document 스키마
    ├── chunk.py              # 청킹 + Document -> 청크 레코드 변환
    ├── embed.py              # BGE-M3 임베딩
    ├── vectorstore.py        # Chroma 저장/조회
    ├── build_index.py        # 전체 파이프라인 실행 스크립트
    ├── bm25_index.py         # 한국어 BM25 키워드 검색 인덱스
    ├── hybrid_search.py      # BGE-M3 + BM25 RRF 결합 검색
    ├── search.py             # 검색 테스트 스크립트 (기본: 하이브리드)
    ├── generate.py           # 검색 + LLM 답변 생성 (Gemini)
    ├── eval.py               # Recall@k 평가 스크립트
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
GEMINI_API_KEY=...
```

### 2. 벡터DB 인덱스 빌드
공공데이터 API를 호출해서 문서를 수집 → 정제 → 청킹 → BGE-M3 임베딩 → Chroma에 적재한다.
```bash
python -m pipeline.build_index
```
- 최초 실행 시 BGE-M3 모델(약 2GB)을 자동으로 다운로드하므로 시간이 걸린다.
- 결과물(`chroma_db/`)은 로컬에만 생성되고 git에는 올라가지 않는다 — **팀원 각자 로컬에서 한 번씩 실행해야 함**.
- 소스별 수집 건수는 `pipeline/build_index.py` 상단의 상수(`CENTRAL_WELFARE_LIMIT` 등)로 조절한다. 중앙부처복지서비스는 API 일일 트래픽이 100건뿐이라 보수적으로 제한되어 있으니 값을 올릴 때 주의.

### 2-1. 중앙부처복지서비스 커버리지 늘리기 (일일 트래픽 제한 대응)
```bash
python -m pipeline.grow_welfare_central --batch 30
```
Chroma에 이미 들어있는 서비스ID를 확인하고 다음 페이지부터 이어서 상세조회를 가져와 추가 적재한다. 매일(또는 며칠에 걸쳐) 이 명령만 반복 실행하면 100건 트래픽 제한 안에서 조금씩 커버리지가 늘어난다 — `build_index.py`를 다시 돌리는 것과 달리 이미 수집한 것을 중복으로 다시 받지 않는다.

### 3. 검색 테스트
```bash
python -m pipeline.search "65세 이상 받을 수 있는 의료 혜택"
python -m pipeline.search --dense-only "65세 이상 받을 수 있는 의료 혜택"   # BGE-M3 단독과 비교
```
기본은 BGE-M3(dense) + BM25(키워드) 하이브리드 검색(RRF 결합)이다.

### 4. 검색 성능 평가 (Recall@k)
```bash
python -m pipeline.eval --sample 150
```
사람이 라벨링한 쿼리셋이 없어서, 각 청크의 title/본문 일부를 쿼리로 역생성해 "원래 청크가 top-k에 다시 잡히는지"로 Recall@k를 측정하는 self-retrieval 방식을 쓴다. 832개 청크 기준 dense 단독 대비 하이브리드가 Recall@10 0.877 → 0.983으로 개선됨을 확인함.

### 5. LLM 답변 생성 테스트
```bash
python -m pipeline.generate "65세 이상 받을 수 있는 의료 혜택"
```
하이브리드 검색 결과를 Gemini(`gemini-3.5-flash`, OpenAI 호환 엔드포인트)에 넣어 근거 기반 답변을 생성하고, 답변에 쓰인 출처 메타데이터를 함께 출력한다. `GEMINI_API_KEY`가 `.env`에 설정돼 있어야 동작한다 (aistudio.google.com/apikey 에서 무료 발급). 소현(웹·지도·통합)이 FastAPI에서 호출할 함수는 `generate_answer(query, n_results)` — `{"answer": str, "sources": [...]}` 형태로 반환한다.

> **참고**: Gemini 무료 등급은 요청 입력 내용이 Google 제품 개선에 활용될 수 있다. 우리 시스템은 공공데이터+일반 질문만 LLM에 전달하고 개인식별정보는 보내지 않으므로 큰 리스크는 아니지만, 팀 내 공유해 둘 것.

## 알려진 제약
- **(의도된 범위 제외)** 법제처 API는 신청한 것이 "목록조회"라 조문 원문은 못 가져오고 법령명·소관부처·시행일자 등 메타데이터만 확보됨. 조문 본문을 가져오려면 `open.law.go.kr`에 별도 가입·OC(이메일ID 기반) 인증키 신청이 필요한데, 핵심 기능(복지혜택/건강정보 안내)에 필수는 아니라고 판단해 이번 범위에서 제외하기로 함. 법령 관련 질의는 "관련 법령명 안내" 수준까지만 지원.
- **(의도된 범위 제외)** 질병관리청 건강정보검색 API는 승인은 났으나 사용하지 않기로 함. REST(JSON/XML)가 아니라 브라우저에서 실제 폼 제출(페이지 네비게이션)로만 동작하는 HTML 위젯형 API라 `requests`/`curl` 등 스크립트 호출이 전부 차단됨(쿠키·Referer·User-Agent를 모두 맞춰도 실패, 브라우저 내부 `fetch()`조차 실패 — 실제 페이지 이동일 때만 동작). 정식 연동은 Playwright 같은 브라우저 자동화가 필요한데, 투입 대비 효과(어차피 "있으면 좋고 없어도 그만"인 일반 건강정보 콘텐츠)가 낮아 범위에서 제외. 신청 자체는 계정에 남아있지만 호출하지 않음.
- 장기요양기관 검색 목록조회(`getLtcInsttSeachList02`)는 `siDoCd`(시도코드) 필수 파라미터를 넣지 않으면 빈 결과가 나옴 — `collectors/ltc_institution.py`의 `SIDO_CODES` 참고, 현재는 16개 시도 전체를 순회해 수집 중.
