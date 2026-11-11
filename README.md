# 보듬 · 곁에서 챙기는 의료·복지 안내

공공데이터를 근거로 의료·복지 혜택, 관련 제도, 가까운 의료기관을 안내하는 AI 에이전트 웹 서비스입니다.
RAG 챗봇, 지역 맞춤 혜택 추천, 지도 기반 기관 찾기를 한 화면에서 제공합니다.

> 개인 건강 위험도를 예측·판정하는 기능은 의료법 리스크로 범위에서 제외했습니다. 모든 기능은 **정보 제공·연계**에 한정하며, 진단·처방은 하지 않습니다. 소득 등 개인정보도 묻지 않고 혜택별 공식 선정기준만 보여줍니다.


## 주요 기능

| 화면 | 경로 | 기능 |
| --- | --- | --- |
| 공통 | — | 내 지역 선택: 고른 지역이 모든 화면에 적용되고 다음 방문 때도 유지. 처음 방문하면 현재 위치로 찾고, 실패하면 서울특별시 전체 기준으로 잡는다. |
| 챗봇 | `/` | 예시 질문, 마크다운 답변, 인용 출처(복지 출처는 혜택 상세로 연결). 질문에 내 지역과 이전 대화를 함께 보내 후속 질문 처리. 범위 밖 질문(잡담·진단 요청·욕설·프롬프트 조작) 차단, 자살·자해 언급에는 상담 전화 안내. 대화 기록은 브라우저(localStorage)에 저장 |
| 혜택 추천 | `/benefits` | 생애주기·분야(신체건강/정신건강/임신·출산) 필터, 혜택 이름·대상 검색, 신청 상태, 페이지 나눔 |
| 혜택 상세 | `/benefits/:id` | 대상·공식 선정기준, 신청 방법(신청·조사·결정기관 단계별), 신청 서식(복지로 첨부파일)·근거법령, 복지로 원문 링크 |
| 지도 | `/map` | 내 지역 기준으로 병원·보건소·약국·장기요양기관 표시(공공데이터 + 카카오 장소 검색), 기관명 검색, 유형 다중 선택, 거리순 목록, "이 지역 검색", 마커 클러스터링 |
| 기관 상세 | `/facilities/:id` | 카카오맵 길찾기·전화, 병원 평가등급, 이용현황, 제공 서비스, 연계 혜택, "챗봇에 물어보기" |

## 시스템 구성

```
React 웹 (agent/frontend, Vite)
   │  /api 요청 (개발 중에는 Vite 프록시 → 8000번)
   ▼
FastAPI (agent/backend)
   ├─ /api/chat        → services/guard.py (질문 거르기)
   │                     → services/rag.py → data-rag generate_answer()
   │                                          ├─ BGE-M3 + BM25 하이브리드 검색 (Chroma)
   │                                          └─ Gemini 답변 생성 + 출처
   ├─ /api/benefits    → services/benefits.py → health_benefits search_benefits
   │                                             └─ Supabase PostgreSQL (healty_benefit)
   ├─ /api/facilities  → data/facilities.json (공공데이터 기관, 서버 시작 때 로드)
   └─ /api/regions     → data/regions.json (전국 시도·시군구 + 기준 좌표)

브라우저에서 직접: 카카오맵 JavaScript SDK (지도, 내 주변 장소 검색, 좌표 → 행정구역)
```

## 폴더 구조와 담당

| 폴더 | 내용 | 담당 |
| --- | --- | --- |
| [`agent/`](./agent) | 웹 프론트엔드(React), 백엔드 API(FastAPI), 지도 연동, 기관·지역 데이터 수집 스크립트 | 소현 (웹·지도·통합) |
| [`data-rag/`](./data-rag) | 공공데이터 수집기, 정제·청킹·임베딩, 벡터DB, 하이브리드 검색, LLM 답변 생성 | 원희 (RAG·챗봇) |
| [`health_benefits/`](./health_benefits) | 복지서비스 수집, Supabase 혜택 DB(`benefit`, `healty_benefit`), 혜택 조건 매칭 | 가은 (매칭·데이터) |

```
health-rag-agent/
├── .env.example                 # 공용 환경변수 예시
├── agent/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py          # API 엔드포인트
│   │   │   ├── schemas.py       # 요청·응답 형식
│   │   │   └── services/
│   │   │       ├── rag.py       # data-rag 호출 + 지역 우선 검색
│   │   │       ├── guard.py     # 범위 밖 질문 거르기 (규칙 + LLM 분류)
│   │   │       ├── benefits.py  # health_benefits 혜택 검색 호출
│   │   │       └── facilities.py# facilities.json, regions.json 로드
│   │   ├── scripts/
│   │   │   ├── collect_facilities.py  # 공공데이터 기관 수집 → data/facilities.json
│   │   │   └── build_regions.py       # 전국 시도·시군구 + 기준 좌표 → data/regions.json
│   │   └── data/                # 위 스크립트 결과
│   └── frontend/
│       └── src/
│           ├── pages/           # Chat, Benefits, BenefitDetail, Map, FacilityDetail
│           ├── components/      # KakaoMap, MapPin, RegionPicker, ConversationList, FormLink, BrandMark
│           ├── chatHistory.jsx  # 챗봇 대화 기록 (localStorage)
│           ├── region.jsx       # 전역 '내 지역'
│           ├── kakao.js         # 카카오 SDK, 장소 검색, 현재 위치
│           ├── api.js           # 백엔드 호출
│           └── index.css        # 디자인 토큰·스타일
├── data-rag/
│   ├── config.py                # 루트 .env에서 키 로드
│   ├── collectors/              # 소스별 공공데이터 API 클라이언트
│   └── pipeline/                # 정제 → 청킹 → 임베딩 → 벡터DB → 검색 → 답변 생성
└── health_benefits/
    ├── run.py                   # 공통 실행 진입점 (python health_benefits/run.py <명령>)
    ├── collection/              # 복지서비스 목록·상세 수집
    ├── database/                # 테이블 저장·이전, SQL 스키마
    ├── preprocessing/           # healty_benefit 생성, 생애주기·주제·신청기간 보충
    ├── recommendation/          # search_benefits (혜택 조건 매칭)
    ├── tests/
    └── docs/COLLECTION.md       # 혜택 DB 상세 설명 (컬럼, 판정 규칙, 실행 결과)
```

## 빠른 시작

### 0. 준비

- Python 3.12, Node.js 20 이상
- API 키·DB 접속 정보는 **저장소 루트의 `.env` 하나**로 관리합니다. `data-rag`, `agent/backend`, `agent/frontend`(Vite `envDir`), `health_benefits`가 모두 이 파일을 읽습니다. `.env`는 커밋되지 않습니다.

```bash
copy .env.example .env
```

| 기능 | 필요한 값 |
| --- | --- |
| 챗봇 | `GEMINI_API_KEY` + `data-rag/chroma_db/` (인덱스 빌드 결과, [RAG·챗봇](#rag챗봇-data-rag) 참고) |
| 혜택 추천 | `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` (Supabase) |
| 지도 | `VITE_KAKAO_MAP_KEY` (카카오 JavaScript 키. 카카오 앱 플랫폼에 `http://localhost:5173` 등록 + 카카오맵 사용 ON) |
| 데이터 다시 수집할 때만 | `DATA_GO_KR_API_KEY`, `DATA_GO_KR_SERVICE_KEY`, `KAKAO_REST_API_KEY` |

키가 없는 기능은 화면에 503 사유가 뜨고, 나머지 기능은 그대로 동작합니다.

> `VITE_`로 시작하는 키만 브라우저에 노출됩니다. 다른 비밀 키에 `VITE_`를 붙이지 마세요.

### 1. 백엔드 (터미널 1)

처음 한 번:
```bash
cd agent/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r ../../data-rag/requirements.txt "chromadb>=1.0"
```
- 두 번째 줄은 챗봇(RAG)용입니다. `chromadb==0.5.23`은 Windows·Python 3.12에서 C++ 빌드 도구가 없으면 설치가 안 돼서 `chromadb>=1.0`으로 덮어씁니다.
- 처음 실행할 때 BGE-M3 임베딩 모델(약 2GB)을 내려받습니다.

실행:
```bash
cd agent/backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```
- 서버가 뜨면 백그라운드에서 RAG 모델·인덱스를 미리 불러옵니다(수십 초). 로그에 `RAG 모델·인덱스 미리 불러오기 완료`가 나온 뒤부터 챗봇 답변이 빠릅니다.
- 확인: http://localhost:8000/api/health → `{"status":"ok"}`, API 문서: http://localhost:8000/docs

### 2. 프론트엔드 (터미널 2)

```bash
cd agent/frontend
npm install
npm run dev
```
- http://localhost:5173 접속. `/api` 요청은 `vite.config.js` 프록시로 8000번 백엔드에 넘어가므로 백엔드를 먼저 켜 두세요.
- `.env`를 바꾸면 `npm run dev`를 다시 실행하세요.
- 배포용 빌드: `npm run build` → `dist/`. 린트: `npm run lint`

## 웹·백엔드 (agent)

### API

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| POST | `/api/chat` | `{query, region, history: [{role: "user"\|"assistant", content}]}` → `{answer, sources, blocked}` |
| GET | `/api/regions` | 선택 가능한 지역과 기준 좌표 |
| GET | `/api/benefits` | `province`, `municipality`, `life_cycle`, `target_group`, `themes`(쉼표 구분) → `{matched, needs_review, notice}` |
| GET | `/api/benefits/by-service/{source}/{service_id}` | 챗봇 출처의 복지서비스 코드로 혜택 한 건 |
| GET | `/api/facilities` | `types`(쉼표 구분), `q`, `province`, `municipality`, `lat`, `lng`(거리 계산), `radius_km`, `limit` |
| GET | `/api/facilities/{id}` | 기관 상세 (`lat`, `lng` 주면 거리 포함) |
| GET | `/api/health` | 서버 상태 확인 |

### 챗봇 처리 흐름 (`services/rag.py`, `services/guard.py`)

1. **규칙 검사**: 너무 긴 질문, 의미 없는 입력, 자살·자해 언급, 프롬프트 조작, 욕설을 정규식으로 거릅니다. 모델 로딩 전에 하므로 RAG를 못 불러와도 위기 질문에는 상담 전화 안내가 나갑니다.
2. **LLM 분류**: 혜택·기관 관련 단어가 분명하고 증상·약 이야기가 없으면 건너뜁니다(Gemini 사용량 절약). 나머지는 잡담·진단 요청 등을 LLM으로 분류하고, 분류에 실패하면 통과시킵니다.
3. **지역 판단**: 질문이나 이전 질문에 다른 지역("중랑구에 살아")이 나오면 그 지역을, 없으면 사용자가 고른 지역을 씁니다.
4. **지역 우선 검색**: data-rag의 하이브리드 검색은 지역을 모르기 때문에, 후보를 넉넉히 받아 다른 지역 자료를 빼고 내 시군구·시도 자료를 앞으로 당긴 뒤 답변 생성에 넘깁니다.
5. **답변 생성**: data-rag `generate_answer()`가 이전 대화와 함께 Gemini로 답변을 만들고, 답변에 실제로 쓰인 문서만 출처로 돌려줍니다.

### 혜택 연결 (`services/benefits.py`)

- `healty_benefit` 테이블을 읽어 10분 동안 메모리에 캐시하고, 필터링은 `health_benefits`의 `extract_benefits()`에 맡깁니다.
- 생애주기·대상특성을 골랐을 때 그 분류가 비어 있는 혜택은 목록에서 뺍니다.
- 기관-혜택 매핑 컬럼이 아직 없어서, 혜택 이름·요약·신청방법 키워드로 관련 기관 유형(`related_facility_types`)을 추정해 기관 상세의 '연계된 혜택'에 씁니다.

### 지도 기관·지역 데이터 다시 만들기 (선택)

`agent/backend/data/facilities.json`, `regions.json`은 저장소에 들어 있어서 보통은 건너뛰어도 됩니다.

```bash
cd agent/backend
.venv\Scripts\activate
python scripts/collect_facilities.py                         # 기본: 서울특별시
python scripts/collect_facilities.py --provinces 서울특별시 부산광역시
python scripts/build_regions.py                              # → data/regions.json
```
- 치매안심센터는 항상 전국을, 병원·장기요양기관은 `--provinces`로 고른 시도만 수집합니다. 지금 파일은 기본값(서울)으로 만든 것이라 **서울 밖에서는 공공데이터 기관이 거의 없고 카카오 장소 검색 결과만 보입니다.**
- 병원평가 원문은 주소만 있어 카카오 주소 검색으로 좌표를 붙이고, 장기요양기관 원문은 주소가 없어 카카오 키워드 검색으로 위치를 찾습니다(시군구 코드가 일치할 때만 사용).
- 주소 → 좌표 결과는 `data/geocode_cache.json`에 캐시되고, 원문은 `data/raw/`에 저장됩니다(둘 다 git 제외).
- 두 파일은 백엔드 시작 때 한 번 읽으므로, 새로 만들면 백엔드를 다시 켜야 합니다.

## RAG·챗봇 (data-rag)

### 파이프라인

```
collectors/ (공공데이터 API) → normalize.py (공통 문서 형식) → clean.py → chunk.py
  → embed.py (BGE-M3) → vectorstore.py (Chroma) + bm25_index.py (한국어 BM25)
  → hybrid_search.py (RRF 결합) → generate.py (Gemini 답변 + 출처)
```

| 파일 | 역할 |
| --- | --- |
| `collectors/` | 법령, 병원평가, 장기요양기관, 중앙부처·지자체 복지서비스, 치매센터, 급여지급현황 API 클라이언트 |
| `pipeline/build_index.py` | 공공데이터 API 수집부터 Chroma 적재까지 전체 실행 |
| `pipeline/build_benefits_index.py` | 복지 자료를 `healty_benefit` DB 스냅샷으로 다시 만들기 |
| `pipeline/grow_welfare_central.py` | 중앙부처 복지서비스를 일일 한도 안에서 조금씩 추가 |
| `pipeline/hybrid_search.py` | BGE-M3(dense) + BM25(키워드) 결과를 RRF로 결합 |
| `pipeline/generate.py` | 검색 + Gemini 답변 생성. 웹이 호출하는 `generate_answer(query, n_results, history)` |
| `pipeline/search.py`, `eval.py`, `manual_check.py` | 검색 테스트, Recall@k 평가, API 실호출 점검 |

### 실행 (data-rag 단독)

```bash
cd data-rag
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**벡터DB 인덱스 빌드** — 공공데이터 API 수집 → 정제 → 청킹 → 임베딩 → Chroma 적재:
```bash
python -m pipeline.build_index
```
- 결과물 `data-rag/chroma_db/`는 git에 올라가지 않으므로 **팀원 각자 로컬에서 한 번씩 실행**해야 합니다.
- 소스별 수집 건수는 `build_index.py` 상단 상수(`CENTRAL_WELFARE_LIMIT` 등)로 조절합니다. 중앙부처 복지서비스는 API 일일 트래픽이 100건뿐이라 값을 올릴 때 주의하세요.

**중앙부처 복지서비스 조금씩 늘리기** — 이미 넣은 서비스는 건너뛰고 다음 것부터 추가합니다:
```bash
python -m pipeline.grow_welfare_central --batch 30
```

**혜택 DB로 복지 자료 다시 만들기** — 백엔드를 끈 상태에서:
```powershell
.\.venv\Scripts\python.exe -m pipeline.build_benefits_index --dry-run
.\.venv\Scripts\python.exe -m pipeline.build_benefits_index
```
- 루트 `.env`의 PG 접속 정보로 `public.healty_benefit`을 읽기 전용으로 읽습니다. 공공데이터 API나 Gemini는 부르지 않습니다.
- 복지 자료(`welfare_central`, `welfare_local`)만 DB 스냅샷으로 교체하고, 병원·법령 등 다른 출처 청크는 그대로 둡니다. 출처 이름과 서비스 ID도 그대로 유지합니다.
- 문서 스냅샷과 기존 Chroma 백업은 `health_benefits/data/rag_builds/`(git 제외)에 저장됩니다. 새 청크 ID를 확인한 뒤에만 옛 복지 청크를 지웁니다. 중간에 끊기면 일부만 바뀐 상태일 수 있으니, 다시 성공할 때까지 돌리거나 백엔드를 끈 채 백업을 복원하세요.
- 성공하면 백엔드를 다시 켜야 BM25 인덱스가 새로 만들어집니다.

**검색·평가·답변 테스트**:
```bash
python -m pipeline.search "65세 이상 받을 수 있는 의료 혜택"
python -m pipeline.search --dense-only "65세 이상 받을 수 있는 의료 혜택"   # BGE-M3 단독과 비교
python -m pipeline.eval --sample 150
python -m pipeline.generate "65세 이상 받을 수 있는 의료 혜택"
```
- 평가는 라벨링된 쿼리셋이 없어서, 청크 제목·본문 일부로 쿼리를 만들어 원래 청크가 top-k에 다시 잡히는지 보는 self-retrieval 방식입니다. 832개 청크 기준 dense 단독 대비 하이브리드가 Recall@10 0.877 → 0.983으로 좋아졌습니다.
- 답변 생성은 Gemini(`gemini-3.5-flash`, OpenAI 호환 엔드포인트)를 씁니다. 키는 aistudio.google.com/apikey 에서 무료로 발급합니다.

> Gemini 무료 등급은 요청 내용이 Google 제품 개선에 쓰일 수 있습니다. 공공데이터와 일반 질문만 보내고 개인식별정보는 보내지 않습니다. 무료 등급은 하루 요청 수 한도가 작으니 테스트는 아껴서 하세요.

## 혜택 DB (health_benefits)

복지로 중앙부처·지자체 복지서비스를 수집해 Supabase PostgreSQL에 저장하고, 의료 관련 혜택만 골라 조건 매칭합니다. 컬럼 정의, 판정 규칙, 실행 결과 수치는 [`health_benefits/docs/COLLECTION.md`](./health_benefits/docs/COLLECTION.md)에 자세히 있습니다.

### 테이블

| 테이블 | 내용 |
| --- | --- |
| `benefit` | 수집한 전체 복지서비스(목록 + 상세). 중복 방지 키는 `(source, source_service_id)`, `source`는 `central`/`local` |
| `healty_benefit` | `benefit`에서 주제코드 010(신체건강)·020(정신건강)·080(임신·출산)인 770건(중앙 141, 지자체 629)을 복사한 테이블. 생애주기·대상특성·주제코드·신청기간 컬럼 보충. **자동 동기화되지 않음** |

### 실행 (저장소 루트에서)

```powershell
# 수집
python health_benefits/run.py collect_catalog --source central
python health_benefits/run.py collect_many --source central --limit 0 --max-calls 1000 --refresh --skip-collected-today
python health_benefits/run.py verify_collection

# 의료 혜택 테이블 만들기·보충
python health_benefits/run.py create_healty_benefit
python health_benefits/run.py backfill_audience_fields
python health_benefits/run.py backfill_theme_codes
python health_benefits/run.py backfill_application_status

# 조건 매칭 (웹 혜택 화면이 쓰는 로직)
python health_benefits/run.py search --life-cycle 청년 --target-group 장애인 --province 서울특별시

# 테스트
python -m unittest discover -s health_benefits/tests -p test_search_benefits.py
python -m unittest discover -s health_benefits/tests -p test_application_period.py
python health_benefits/run.py test_benefit_store   # 실제 DB 임시 테이블로 저장 로직 확인
```

### 매칭 규칙 (`recommendation/search_benefits.py`)

- 같은 분류 안에서는 OR, 생애주기·대상특성·지역 사이는 AND입니다.
- `matched`: 고른 조건과 분류가 일치. 수급 자격 확정을 뜻하지는 않습니다.
- `needs_review`: 알려진 불일치는 없지만 조건 정보가 비어 있어 원문 확인이 필요한 후보입니다.
- 분류가 비어 있으면(NULL) '전체 대상'으로 바꾸지 않고 '대상 원문 확인'으로 표시합니다. 명시적인 `전체`/`전체 대상`만 전체로 인정합니다.
- 제공기관 지역은 신청자의 실제 거주 요건과 다를 수 있습니다.
- 신청 상태(`application_status`)는 저장된 값이라 시간이 지나도 자동으로 바뀌지 않습니다. `SELECT refresh_benefit_application_status();`로 갱신합니다.

## 데이터 출처

| 데이터 | 링크 | 제공 형태 | 쓰는 곳 | 비고 |
| --- | --- | --- | --- | --- |
| 한국사회보장정보원 중앙부처복지서비스 | [15090532](https://www.data.go.kr/data/15090532/openapi.do) | Open API | 챗봇(RAG), 혜택 추천 | 대상·선정기준·지원내용과 신청방법·신청서식·근거법령 저장 (구비서류는 미저장). 일일 트래픽 100건 |
| 한국사회보장정보원 지자체복지서비스 | [15108347](https://www.data.go.kr/data/15108347/openapi.do) | Open API | 챗봇(RAG), 혜택 추천 | 위와 같음 |
| 한국사회보장정보원 복지사업 월별 급여지급 현황 | [15009571](https://www.data.go.kr/data/15009571/fileData.do) | 파일데이터(odcloud API) | 챗봇(RAG) | 지급 통계 |
| 건강보험심사평가원 병원평가정보서비스 | [15094093](https://www.data.go.kr/data/15094093/openapi.do) | Open API | 챗봇(RAG), 지도·기관 상세 | 주소만 제공 → 카카오 주소 검색으로 좌표 변환. `asmGrdNN` 항목명은 활용가이드(2025-02-19) 기준 |
| 전국치매센터표준데이터 | [15021138](https://www.data.go.kr/data/15021138/standard.do) | 표준데이터 API | 챗봇(RAG), 지역 목록 생성 | 위도·경도, 인력, 프로그램 포함. 지도에는 표시하지 않음 |
| 국민건강보험공단 장기요양기관 검색 | [15059029](https://www.data.go.kr/data/15059029/openapi.do) | Open API | 챗봇(RAG), 지도 | 주소·전화 없음(시도·시군구 코드만) → 카카오 키워드 검색 후 시군구 코드 일치 확인. `siDoCd` 없이 부르면 빈 결과 |
| 법제처 국가법령정보 공유서비스 | [15000115](https://www.data.go.kr/data/15000115/openapi.do) | Open API | 챗봇(RAG) | 목록조회만 사용 — 법령명·소관부처·시행일자 등 메타데이터 (조문 원문 미포함) |
| 카카오 로컬 API (장소·주소 검색, 좌표 → 행정구역) | [Kakao Developers](https://developers.kakao.com/docs/latest/ko/local/dev-guide) | Open API | 지도(내 주변 병원·보건소·약국·요양원), 현재 위치 → 지역, 공공데이터 좌표 변환 | 보건소·약국 위치는 이것 외 출처 없음 |
| Supabase (PostgreSQL) | — | DB | 혜택 추천 | 복지서비스 수집 결과(`benefit`, `healty_benefit`) 저장소 |

## 알려진 제약

알려진 제약
- **법령 조문 원문 없음** — 법제처 API는 목록조회만 신청해서 법령명·소관부처·시행일자까지만 있습니다. 조문 본문은 `open.law.go.kr` 별도 인증키가 필요해 범위에서 뺐습니다. 법령 질문은 "관련 법령명 안내" 수준까지 지원합니다.
- **질병관리청 건강정보 API 미사용** — 브라우저 폼 제출로만 동작하는 HTML 위젯형이라 스크립트 호출이 모두 막혀 범위에서 뺐습니다.
- **지도 공공데이터는 서울 위주** — 병원·장기요양기관은 서울만 수집되어 있습니다. 다른 지역은 카카오 장소 검색 결과(유형마다 최대 15곳)만 보입니다.
- **혜택 테이블은 복사본** — `healty_benefit`은 생성 시점의 복사본이라 `benefit`을 다시 수집해도 자동으로 바뀌지 않습니다.
- **Gemini 무료 등급 한도** — 하루 요청 수가 작아서, 한도에 걸리면 챗봇이 안내 문구와 함께 503을 돌려줍니다.

## 자주 나오는 문제

| 증상 | 원인·해결 |
| --- | --- |
| 챗봇이 `data-rag 불러오기 실패` | 백엔드 venv에 data-rag 의존성이 없음 → [백엔드 설치](#1-백엔드-터미널-1)의 두 번째 `pip install` |
| 챗봇이 `답변 생성 실패` | `GEMINI_API_KEY` 없음/한도 초과, 또는 `data-rag/chroma_db/` 없음 (`data-rag`에서 `python -m pipeline.build_index`) |
| 챗봇이 "오늘 쓸 수 있는 답변 생성 한도를 다 썼어요" | Gemini 무료 등급 하루 한도 초과. 다음 날 다시 시도 |
| 혜택 화면이 `혜택 DB 조회 실패` | 루트 `.env`의 `PG*` 값 확인 |
| 지도가 회색/안 뜸 | `VITE_KAKAO_MAP_KEY` 없음, 카카오 앱에 `http://localhost:5173` 미등록, 또는 `.env` 수정 후 `npm run dev` 재시작 안 함. 5173이 아닌 포트로 뜨면 카카오가 막음(401) |
| 프론트에서 `요청 실패 (500)`/프록시 오류 | 백엔드가 8000번에서 안 켜져 있음 |
