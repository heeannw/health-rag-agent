# 보듬 · 곁에서 챙기는 의료·복지 안내 AI 챗봇 서비스

공공데이터를 근거로 의료·복지 혜택, 관련 제도, 가까운 의료기관을 안내하는 AI 에이전트 웹 서비스입니다.
RAG 챗봇, 지역 맞춤 혜택 추천, 지도 기반 기관 찾기를 제공합니다.

> 모든 기능은 **정보 제공·연계**에 한정합니다. 진단·처방과 개인 건강 위험도 판정은 하지 않고, 소득 등 개인정보도 묻지 않습니다.

## 주요 기능

| 화면 | 경로 | 기능 |
| --- | --- | --- |
| 공통 | — | 내 지역 선택 (모든 화면에 적용, 다음 방문에도 유지. 첫 방문은 현재 위치, 실패하면 서울 전체) |
| 챗봇 | `/` | 지역·이전 대화를 반영한 답변과 인용 출처, 범위 밖 질문 차단, 위기 언급 시 상담 전화 안내, 대화 기록(localStorage) |
| 혜택 추천 | `/benefits` | 생애주기·분야 필터, 검색, 신청 상태, 페이지 나눔 |
| 혜택 상세 | `/benefits/:id` | 대상·선정기준, 신청 방법, 신청 서식·근거법령, 복지로 원문 링크 |
| 지도 | `/map` | 병원·보건소·약국·장기요양기관 (공공데이터 + 카카오 장소 검색), 검색, 유형 선택, 거리순 목록, "이 지역 검색" |
| 기관 상세 | `/facilities/:id` | 길찾기, 병원 평가등급, 연계 혜택, "챗봇에 물어보기" |

## 시스템 구성

```
React 웹 (agent/frontend, Vite)  ──/api──▶  FastAPI (agent/backend)
   ├─ /api/chat        → guard.py (질문 거르기) → rag.py → data-rag generate_answer()
   │                       BGE-M3 + BM25 하이브리드 검색 (Chroma) → Gemini 답변 + 출처
   ├─ /api/benefits    → benefits.py → health_benefits search_benefits → Supabase (healty_benefit)
   ├─ /api/facilities  → data/facilities.json
   └─ /api/regions     → data/regions.json
브라우저에서 직접: 카카오맵 JavaScript SDK (지도, 장소 검색, 좌표 → 행정구역)
```

| 폴더 | 내용 | 담당 |
| --- | --- | --- |
| [`agent/`](./agent) | 웹 프론트엔드(React), 백엔드 API(FastAPI), 지도 연동, 기관·지역 데이터 수집 스크립트 | 소현 (웹·지도·통합) |
| [`data-rag/`](./data-rag) | 공공데이터 수집기(`collectors/`), 정제·청킹·임베딩·검색·답변 생성(`pipeline/`) | 원희 (RAG·챗봇) |
| [`health_benefits/`](./health_benefits) | 복지서비스 수집, Supabase 혜택 DB, 혜택 조건 매칭 | 가은 (매칭·데이터) |

## 빠른 시작

Python 3.12, Node.js 20 이상이 필요합니다. 키와 DB 접속 정보는 **저장소 루트의 `.env` 하나**로 관리합니다(커밋되지 않음).

```bash
copy .env.example .env
```

| 기능 | 필요한 값 |
| --- | --- |
| 챗봇 | `GEMINI_API_KEY` + `data-rag/chroma_db/` ([인덱스 빌드](#rag챗봇-data-rag)) |
| 혜택 추천 | `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` (Supabase) |
| 지도 | `VITE_KAKAO_MAP_KEY` (카카오 JavaScript 키, 앱 플랫폼에 `http://localhost:5173` 등록) |
| 데이터 다시 수집할 때만 | `DATA_GO_KR_API_KEY`, `DATA_GO_KR_SERVICE_KEY`, `KAKAO_REST_API_KEY` |

키가 없는 기능만 503 사유가 뜨고 나머지는 동작합니다. `VITE_`로 시작하는 키는 브라우저에 노출되니 다른 비밀 키에는 붙이지 마세요.

### 1. 백엔드 (터미널 1)

```bash
cd agent/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r ../../data-rag/requirements.txt "chromadb>=1.0"
uvicorn app.main:app --reload --port 8000
```

- 두 번째 `pip install`은 챗봇용입니다. `chromadb==0.5.23`은 Windows·Python 3.12에서 빌드 도구 없이는 설치가 안 돼 `chromadb>=1.0`으로 덮어씁니다.
- 처음 실행하면 BGE-M3 모델(약 2GB)을 내려받고, 서버가 뜬 뒤 수십 초 동안 모델·인덱스를 미리 불러옵니다.
- 확인: http://localhost:8000/api/health , API 문서: http://localhost:8000/docs

### 2. 프론트엔드 (터미널 2)

```bash
cd agent/frontend
npm install
npm run dev
```

http://localhost:5173 으로 접속합니다. `/api` 요청은 8000번 백엔드로 프록시되고, `.env`를 바꾸면 다시 실행해야 합니다.

## 웹·백엔드 (agent)

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| POST | `/api/chat` | `{query, region, history}` → `{answer, sources, blocked}` |
| GET | `/api/regions` | 선택 가능한 지역과 기준 좌표 |
| GET | `/api/benefits` | `province`, `municipality`, `life_cycle`, `target_group`, `themes` → `{matched, needs_review, notice}` |
| GET | `/api/benefits/by-service/{source}/{service_id}` | 챗봇 출처의 복지서비스 코드로 혜택 한 건 |
| GET | `/api/facilities` | `types`, `q`, `province`, `municipality`, `lat`·`lng`, `radius_km`, `limit` |
| GET | `/api/facilities/{id}` | 기관 상세 |

**챗봇 흐름**: 규칙 검사(길이·무의미 입력·위기·프롬프트 조작·욕설) → LLM 분류(분명한 혜택·기관 질문은 건너뜀) → 질문 속 지역 판단 → 다른 지역 자료를 빼고 내 지역 자료를 앞으로 당긴 검색 → Gemini 답변과 실제 쓰인 출처.

**혜택 연결**: `healty_benefit`을 10분 캐시하고 필터링은 `extract_benefits()`에 맡깁니다. 기관-혜택 매핑 컬럼이 없어 키워드로 관련 기관 유형을 추정합니다.

**기관·지역 데이터 다시 만들기 (선택)** — 결과 파일이 저장소에 들어 있어 보통은 필요 없습니다.

```bash
python scripts/collect_facilities.py --provinces 서울특별시 부산광역시   # 기본: 서울특별시
python scripts/build_regions.py
```

지금 파일은 서울만 수집한 것이라 다른 지역은 카카오 장소 검색 결과만 보입니다. 새로 만들면 백엔드를 다시 켜야 합니다.

## RAG·챗봇 (data-rag)

```
collectors/ → normalize → clean → chunk → embed (BGE-M3) → vectorstore (Chroma) + bm25_index
  → hybrid_search (RRF 결합) → generate (Gemini 답변 + 출처)
```

```bash
cd data-rag
python -m pipeline.build_index                         # 수집 → 임베딩 → Chroma 적재
python -m pipeline.grow_welfare_central --batch 30     # 중앙부처 복지서비스 조금씩 추가
python -m pipeline.build_benefits_index [--dry-run]    # 복지 자료를 healty_benefit DB로 교체
python -m pipeline.search "65세 이상 받을 수 있는 의료 혜택"
python -m pipeline.eval --sample 150
python -m pipeline.generate "65세 이상 받을 수 있는 의료 혜택"
```

- `chroma_db/`는 git에 올라가지 않으므로 **각자 로컬에서 한 번 빌드**해야 합니다.
- 중앙부처 복지서비스 API는 일일 트래픽이 100건입니다.
- `build_benefits_index`는 백엔드를 끈 상태에서 실행하고, 끝나면 백엔드를 다시 켭니다. 백업은 `health_benefits/data/rag_builds/`에 저장됩니다.
- self-retrieval 평가(832개 청크)에서 Recall@10이 dense 단독 0.877 → 하이브리드 0.983입니다.
- Gemini 무료 등급은 하루 요청 수가 적고 요청 내용이 제품 개선에 쓰일 수 있으니, 개인식별정보는 보내지 않고 테스트는 아껴서 합니다.

## 혜택 DB (health_benefits)

복지로 중앙부처·지자체 복지서비스를 Supabase에 저장하고(`benefit`), 의료 관련 주제(신체건강·정신건강·임신·출산) 770건을 복사해(`healty_benefit`) 조건 매칭합니다. 컬럼, 판정 규칙, 전체 실행 명령은 [`health_benefits/docs/COLLECTION.md`](./health_benefits/docs/COLLECTION.md)에 있습니다.

```powershell
python health_benefits/run.py collect_catalog --source central
python health_benefits/run.py create_healty_benefit
python health_benefits/run.py search --life-cycle 청년 --target-group 장애인 --province 서울특별시
python -m unittest discover -s health_benefits/tests -p test_search_benefits.py
```

- 같은 분류 안은 OR, 생애주기·대상특성·지역 사이는 AND입니다.
- `matched`는 분류 일치(수급 자격 확정 아님), `needs_review`는 조건 정보가 비어 원문 확인이 필요한 후보입니다.
- `healty_benefit`은 복사본이라 자동 동기화되지 않고, 신청 상태는 `SELECT refresh_benefit_application_status();`로 갱신합니다.

## 데이터 출처

| 데이터 | 쓰는 곳 | 비고 |
| --- | --- | --- |
| [중앙부처복지서비스](https://www.data.go.kr/data/15090532/openapi.do) · [지자체복지서비스](https://www.data.go.kr/data/15108347/openapi.do) (한국사회보장정보원) | 챗봇, 혜택 추천 | 중앙부처는 일일 100건 |
| [복지사업 월별 급여지급 현황](https://www.data.go.kr/data/15009571/fileData.do) | 챗봇 | 지급 통계 |
| [병원평가정보서비스](https://www.data.go.kr/data/15094093/openapi.do) (건강보험심사평가원) | 챗봇, 지도 | 주소만 제공 → 카카오로 좌표 변환 |
| [전국치매센터표준데이터](https://www.data.go.kr/data/15021138/standard.do) | 챗봇, 지역 목록 | 지도에는 표시하지 않음 |
| [장기요양기관 검색](https://www.data.go.kr/data/15059029/openapi.do) (국민건강보험공단) | 챗봇, 지도 | 주소 없음 → 카카오 키워드 검색으로 위치 확인 |
| [국가법령정보](https://www.data.go.kr/data/15000115/openapi.do) (법제처) | 챗봇 | 법령명 등 메타데이터만 (조문 원문 없음) |
| [카카오 로컬 API](https://developers.kakao.com/docs/latest/ko/local/dev-guide) | 지도, 현재 위치, 좌표 변환 | 보건소·약국은 이 출처뿐 |

## 알려진 제약

- **법령 조문 원문 없음** — 법령 질문은 관련 법령명 안내 수준까지 지원합니다.
- **지도 공공데이터는 서울 위주** — 다른 지역은 카카오 장소 검색 결과(유형마다 최대 15곳)만 보입니다.
- **혜택 테이블은 복사본** — `benefit`을 다시 수집해도 `healty_benefit`은 자동으로 바뀌지 않습니다.
- **Gemini 무료 등급 한도** — 한도에 걸리면 챗봇이 안내 문구와 함께 503을 돌려줍니다.

## 자주 나오는 문제

| 증상 | 원인·해결 |
| --- | --- |
| 챗봇 `data-rag 불러오기 실패` | 백엔드 venv에 data-rag 의존성 없음 → 백엔드 설치의 두 번째 `pip install` |
| 챗봇 `답변 생성 실패` | `GEMINI_API_KEY` 없음, 또는 `data-rag/chroma_db/` 없음 (`python -m pipeline.build_index`) |
| 챗봇 "답변 생성 한도를 다 썼어요" | Gemini 무료 등급 하루 한도 초과. 다음 날 다시 시도 |
| 혜택 화면 `혜택 DB 조회 실패` | 루트 `.env`의 `PG*` 값 확인 |
| 지도가 회색/안 뜸 | `VITE_KAKAO_MAP_KEY` 없음, 카카오 앱에 `http://localhost:5173` 미등록, `.env` 수정 후 재시작 안 함, 5173이 아닌 포트 |
| 프론트 `요청 실패 (500)`/프록시 오류 | 백엔드가 8000번에서 안 켜져 있음 |
