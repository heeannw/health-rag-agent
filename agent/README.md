# 3. 웹·지도·통합 담당 (담당: 소현)

React 웹 4개 화면과 FastAPI 백엔드를 만들고, 원희(RAG·챗봇)·가은(매칭·데이터) 결과를 화면에 연결하는 역할입니다.

## 진행 현황

| 구분 | 상태 | 내용 |
| --- | --- | --- |
| 웹 기본 틀 | ✅ | React + Vite, 4개 화면 라우팅, 데스크톱 사이드바 / 모바일 하단 탭바 |
| 디자인 | ✅ | 색상(메인 `#D7F6F7`, 강조 `#71BAF6`·`#FFC9CA`), 유리 패널, 전체 배경 그라데이션, Lucide 아이콘 |
| 백엔드 API | ✅ | FastAPI. 샘플 데이터 없음 — 연결 모듈을 못 쓰면 503 + 사유 |
| 챗봇 ↔ RAG 연동 | ✅ | `generate_answer()` 호출, 이전 대화(`history`)를 같이 보내 후속 질문 처리. 서버 시작 때 모델·인덱스 미리 로딩 |
| 챗봇 대화 기록 | ✅ | 브라우저(localStorage)에 저장. 사이드바 목록, 이어서 질문, 한 건/여러 건 삭제 |
| 혜택 ↔ 가은 DB | ✅ | `health_benefits` `search_benefits`로 `healty_benefit` 조회. 신청 방법·서식·근거법령 표시 |
| 지역 목록 | ✅ | 전국 16개 시도 + 228개 시군구 (`data/regions.json`) |
| 지도 기관 데이터 | ✅ | 공공데이터 13,314곳 (`data/facilities.json`, 중복 id 제거). 2,331곳은 좌표 없음 |
| 카카오맵 | ✅ | 지도·장소 검색. 들어오면 현재 위치 기준(반경 10km), 실패하면 서울 전체. 가까운 순 300곳까지 |

## 화면별 기능

- **공통** — 내 지역 선택(사이드바, 모바일은 상단). 고른 지역이 모든 화면에 적용되고 다음 방문 때도 유지
- **챗봇** (`/`) — 예시 질문, 마크다운 답변, 답변별 근거 건수·출처 번호, 인용 출처 패널, 혜택/기관 바로가기. 질문에 선택 지역과 이전 대화를 함께 전달. 대화 기록은 사이드바(모바일은 "대화 기록" 서랍)에서 열기·삭제, '챗봇' 메뉴를 다시 누르면 새 대화
- **혜택 추천** (`/benefits`) — 생애주기·분야(신체건강/정신건강/임신·출산) 필터, 신청 상태, 공식 선정기준·신청 방법·신청 서식(복지로 첨부파일)·근거법령, "가까운 ○○ 보기"로 지도 연결. 소득 등 개인정보는 묻지 않음
- **지도** (`/map`) — 기관명 검색, 기관 유형 다중 선택, 내 지역 기준 거리순 정렬, 병원 평가등급
- **기관 상세** (`/facilities/:id`) — 길찾기(카카오맵 링크)·전화, 이용현황, 제공 서비스, 연계 혜택, "챗봇에 이 기관 물어보기"

## 폴더 구조

```
agent/
├── backend/                  # FastAPI
│   ├── app/
│   │   ├── main.py           # API 엔드포인트
│   │   ├── schemas.py        # 요청·응답 형식 (원희·가은과 협의용)
│   │   └── services/
│   │       ├── rag.py        # data-rag generate_answer() 호출
│   │       ├── benefits.py   # health_benefits 혜택 검색 호출
│   │       └── facilities.py # data/facilities.json, data/regions.json 로드
│   ├── scripts/
│   │   ├── collect_facilities.py  # 공공데이터 기관 수집 → data/facilities.json
│   │   └── build_regions.py       # 전국 시도·시군구 + 기준 좌표 → data/regions.json
│   └── data/                 # 위 스크립트 결과
└── frontend/                 # React + Vite
    └── src/
        ├── pages/            # Chat, Benefits, Map, FacilityDetail
        ├── components/       # KakaoMap, ConversationList(대화 기록), AppBackground(그라데이션), BrandMark
        ├── chatHistory.jsx   # 챗봇 대화 기록 (localStorage)
        ├── region.jsx        # 전역 지역 선택
        ├── api.js            # 백엔드 호출
        └── index.css         # 디자인 토큰·스타일
```

## API

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| POST | `/api/chat` | `{query, region, history: [{role: "user"\|"assistant", content}]}` → `{answer, sources}` |
| GET | `/api/regions` | 선택 가능한 지역과 기준 좌표 |
| GET | `/api/benefits` | `province`, `municipality`, `life_cycle`, `target_group`, `themes`(쉼표 구분) |
| GET | `/api/facilities` | `types`(쉼표 구분), `q`, `province`, `municipality`, `lat`, `lng`(거리 계산), `radius_km`, `limit` |
| GET | `/api/facilities/{id}` | 기관 상세 (`lat`, `lng` 주면 거리 포함) |
| GET | `/api/health` | 서버 상태 확인 |

전체 문서: 백엔드 실행 후 http://localhost:8000/docs

## 실행 방법

### 0. 준비

- Python 3.12, Node.js 20 이상
- 저장소 루트에 `.env` (루트에서 `copy .env.example .env` 후 값 채우기). 화면별로 필요한 키:

| 기능 | 필요한 값 |
| --- | --- |
| 챗봇 | `GEMINI_API_KEY` + `data-rag/chroma_db/` (원희 인덱스 빌드 결과) |
| 혜택 추천 | `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` (Supabase) |
| 지도 | `VITE_KAKAO_MAP_KEY` (카카오 JavaScript 키, 플랫폼에 `http://localhost:5173` 등록 + 카카오맵 사용 ON) |
| 기관 데이터 다시 수집할 때만 | `DATA_GO_KR_API_KEY`, `KAKAO_REST_API_KEY` |

키가 없는 기능은 화면에 503 사유가 뜨고, 나머지 기능은 그대로 동작합니다.

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
- 확인: http://localhost:8000/api/health → `{"status":"ok"}`

### 2. 프론트엔드 (터미널 2)

```bash
cd agent/frontend
npm install
npm run dev
```
- http://localhost:5173 접속. `/api` 요청은 `vite.config.js` 프록시로 8000번 백엔드에 넘어가므로 백엔드를 먼저 켜 두세요.
- `.env`는 `vite.config.js`의 `envDir`가 루트를 가리켜서 루트 파일을 그대로 씁니다. `.env`를 바꾸면 `npm run dev`를 다시 실행하세요.
- React는 `~19.2.9`로 고정되어 있습니다 (`@react-three/fiber`가 19.3 미만만 지원).
- 배포용 빌드: `npm run build` → `dist/`. 린트: `npm run lint`

### 3. (선택) 지도 기관·지역 데이터 다시 만들기

`data/facilities.json`, `data/regions.json`은 저장소에 들어 있어서 보통은 건너뛰어도 됩니다. 새로 수집할 때만:
```bash
cd agent/backend
.venv\Scripts\activate
python scripts/collect_facilities.py   # → data/facilities.json (같은 id는 기준일이 최신인 것만 남김)
python scripts/build_regions.py        # → data/regions.json (facilities.json의 치매안심센터 기준)
```
- 주소 → 좌표 결과는 `data/geocode_cache.json`에 캐시되어, 다시 돌리면 이미 변환한 주소는 건너뜁니다. 원문은 `data/raw/`에 저장됩니다 (둘 다 git 제외).
- 두 파일은 백엔드 시작 때 한 번 읽으므로, 새로 만들면 백엔드를 다시 켜야 합니다.
- 지도 화면은 이 공공데이터에 카카오 장소 검색(내 주변 병원·보건소·치매안심센터·요양원) 결과를 합쳐 보여줍니다.

### 자주 나오는 문제

| 증상 | 원인·해결 |
| --- | --- |
| 챗봇이 `data-rag 불러오기 실패` | 백엔드 venv에 data-rag 의존성이 없음 → 1번의 두 번째 `pip install` |
| 챗봇이 `답변 생성 실패` | `GEMINI_API_KEY` 없음/한도 초과, 또는 `data-rag/chroma_db/` 없음 (`data-rag`에서 `python -m pipeline.build_index`) |
| 혜택 화면이 `혜택 DB 조회 실패` | 루트 `.env`의 `PG*` 값 확인 |
| 지도가 회색/안 뜸 | `VITE_KAKAO_MAP_KEY` 없음, 카카오 앱에 `http://localhost:5173` 미등록, 또는 `.env` 수정 후 `npm run dev` 재시작 안 함 |
| 프론트에서 `요청 실패 (500)`/프록시 오류 | 백엔드가 8000번에서 안 켜져 있음 |

## 남은 일

완료
- [x] 카카오 JavaScript 키 발급, `http://localhost:5173` 도메인 등록 (앱 설정에서 카카오맵 사용 ON 필요)
- [x] 가은 혜택 데이터 연동 (`services/benefits.py` → `health_benefits` 검색)
- [x] 보건소 위치 데이터 확보 (카카오 장소 검색으로 대체)
- [x] 샘플 데이터 제거 — 연결 모듈을 못 쓰면 503 + 사유
- [x] 전국 지역 목록 (`scripts/build_regions.py`, 시도 16 + 시군구 228)
- [x] 지도 진입 시 현재 위치 기준(반경 10km), 실패하면 서울특별시 전체
- [x] data-rag 의존성을 백엔드 venv에 설치 (`chromadb>=1.0`)
- [x] 챗봇 인덱스 빌드 (`data-rag/chroma_db/`)
- [x] 병원평가 주소 → 좌표 변환, 기관 중복 제거
- [x] 혜택 신청 방법·서식·근거법령 표시 (가은 DB 컬럼 `application_method`, `application_forms`, `legal_basis`)
- [x] 챗봇 대화 기록·후속 질문

진행 중 / 해야 할 일
- [ ] `data-rag/pipeline/generate.py`의 `history` 인자 추가를 원희와 확인 후 커밋
- [ ] 혜택 ↔ 기관 연결 — `related_facility_type` 컬럼을 가은과 조율 (혜택 카드 "가까운 ○○ 보기", 기관 상세 연계 혜택이 이걸 씀)
- [ ] 좌표 없는 기관 2,331곳 처리 (지금은 반경 검색에서 빠짐)
- [ ] `feature/web` → `main` PR
