# 3. 웹·지도·통합 담당 (담당: 소현)

React 웹 4개 화면과 FastAPI 백엔드를 만들고, 원희(RAG·챗봇)·가은(매칭·데이터) 결과를 화면에 연결하는 역할입니다.

## 진행 현황

| 구분 | 상태 | 내용 |
| --- | --- | --- |
| 웹 기본 틀 | ✅ | React + Vite, 4개 화면 라우팅, 데스크톱 사이드바 / 모바일 하단 탭바 |
| 디자인 | ✅ | 색상(메인 `#D7F6F7`, 강조 `#71BAF6`·`#FFC9CA`), 유리 패널, 전체 배경 그라데이션, Lucide 아이콘 |
| 백엔드 API | ✅ | FastAPI. 샘플 데이터 없음 — 연결 모듈을 못 쓰면 503 + 사유 |
| 챗봇 ↔ RAG 연동 | 🟡 | `generate_answer()` 호출. data-rag 의존성·`chroma_db`·GEMINI 키 필요 |
| 혜택 ↔ 가은 DB | ✅ | `health_benefits` `search_benefits`로 `healty_benefit` 조회 |
| 지역 목록 | ✅ | 전국 16개 시도 + 228개 시군구 (`data/regions.json`) |
| 카카오맵 | ✅ | 지도·장소 검색. 들어오면 현재 위치 기준(반경 10km), 실패하면 서울 전체 |

## 화면별 기능

- **공통** — 내 지역 선택(사이드바, 모바일은 상단). 고른 지역이 모든 화면에 적용되고 다음 방문 때도 유지
- **챗봇** (`/`) — 예시 질문, 최근 질문, 답변별 근거 건수·출처 번호, 인용 출처 패널, 혜택/기관 바로가기. 질문에 선택 지역을 함께 전달
- **혜택 추천** (`/benefits`) — 생애주기·분야(신체건강/정신건강/임신·출산) 필터, 신청 상태, 공식 선정기준·신청·구비서류·근거법령, "가까운 ○○ 보기"로 지도 연결. 소득 등 개인정보는 묻지 않음
- **지도** (`/map`) — 기관명 검색, 기관 유형 다중 선택, 내 지역 기준 거리순 정렬, 병원 평가등급
- **기관 상세** (`/facilities/:id`) — 길찾기(카카오맵 링크)·전화, 이용현황, 제공 서비스, 연계 혜택, "챗봇에 이 기관 물어보기"

## 폴더 구조

```
agent/
├── backend/                  # FastAPI
│   └── app/
│       ├── main.py           # API 엔드포인트
│       ├── schemas.py        # 응답 형식 (원희·가은과 협의용)
│       └── services/
│           ├── rag.py        # data-rag generate_answer() 호출
│           ├── benefits.py   # health_benefits 혜택 검색 호출
│           └── facilities.py # data/facilities.json, data/regions.json 로드
│   ├── scripts/
│   │   ├── collect_facilities.py  # 공공데이터 기관 수집 → data/facilities.json
│   │   └── build_regions.py       # 전국 시도·시군구 + 기준 좌표 → data/regions.json
│   └── data/                 # 위 스크립트 결과
└── frontend/                 # React + Vite
    └── src/
        ├── pages/            # Chat, Benefits, Map, FacilityDetail
        ├── components/       # KakaoMap, AppBackground(그라데이션), BrandMark
        ├── region.jsx        # 전역 지역 선택
        ├── api.js            # 백엔드 호출
        └── index.css         # 디자인 토큰·스타일
```

## API

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| POST | `/api/chat` | `{query, region}` → `{answer, sources}` |
| GET | `/api/regions` | 선택 가능한 지역과 기준 좌표 |
| GET | `/api/benefits` | `province`, `municipality`, `life_cycle`, `themes`(쉼표 구분) |
| GET | `/api/facilities` | `types`(쉼표 구분), `q`, `province`, `municipality`, `lat`, `lng`(거리 계산), `radius_km` |
| GET | `/api/facilities/{id}` | 기관 상세 (`lat`, `lng` 주면 거리 포함) |

전체 문서: 백엔드 실행 후 http://localhost:8000/docs

## 실행 방법

백엔드:
```bash
cd agent/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- 챗봇 실제 답변을 받으려면 같은 venv에 `pip install -r ../../data-rag/requirements.txt`, 그리고 루트 `.env`(GEMINI_API_KEY)와 `data-rag/chroma_db/`(build_index 결과)가 필요합니다. 없으면 503과 사유가 나옵니다.
  - `chromadb==0.5.23`은 Windows·Python 3.12에서 C++ 빌드 도구가 없으면 설치가 안 돼서, 백엔드 venv에는 `chromadb>=1.0`을 설치했습니다.
- 혜택 추천(`/api/benefits`)은 가은 `health_benefits`의 `search_benefits`로 Supabase `healty_benefit`을 조회합니다. 루트 `.env`에 `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`가 필요하며, 없으면 503과 사유가 나옵니다.

지도 기관·지역 목록 (공공데이터 수집):
```bash
cd agent/backend
pip install -r ../../data-rag/requirements.txt
python scripts/collect_facilities.py   # → data/facilities.json
python scripts/build_regions.py        # → data/regions.json (facilities.json의 치매안심센터 기준)
```
- 루트 `.env`의 `DATA_GO_KR_API_KEY`(치매센터·병원평가·장기요양기관)와 `KAKAO_REST_API_KEY`(주소 → 좌표)가 필요합니다.
- 지도 화면은 이 공공데이터에 카카오 장소 검색(내 주변 병원·보건소·치매안심센터·요양원) 결과를 합쳐 보여줍니다.
- 두 파일은 백엔드 시작 때 한 번 읽으므로, 새로 만들면 백엔드를 다시 켜야 합니다.

프론트엔드:
```bash
cd agent/frontend
npm install
npm run dev               # http://localhost:5173 (/api는 8000번으로 프록시)
```
- 카카오 JavaScript 키는 루트 `.env`의 `VITE_KAKAO_MAP_KEY`에 넣습니다 (`vite.config.js`의 `envDir`가 루트를 가리킴).
- React는 `~19.2.9`로 고정되어 있습니다 (`@react-three/fiber`가 19.3 미만만 지원).

## 남은 일

완료
- [x] 카카오 JavaScript 키 발급, `http://localhost:5173` 도메인 등록 (앱 설정에서 카카오맵 사용 ON 필요)
- [x] 가은 혜택 데이터 연동 (`services/benefits.py` → `health_benefits` 검색)
- [x] 보건소 위치 데이터 확보 (카카오 장소 검색으로 대체)
- [x] 샘플 데이터 제거 — 연결 모듈을 못 쓰면 503 + 사유
- [x] 전국 지역 목록 (`scripts/build_regions.py`, 시도 16 + 시군구 228)
- [x] 지도 진입 시 현재 위치 기준(반경 10km), 실패하면 서울특별시 전체
- [x] data-rag 의존성을 백엔드 venv에 설치 (`chromadb>=1.0`)

진행 중 / 해야 할 일
- [ ] 챗봇 인덱스 빌드 — BGE-M3(약 2GB) 받고 `data-rag`에서 `python -m pipeline.build_index` (중앙부처 복지서비스 API 일일 한도 100건 중 약 30건 사용)
- [ ] 병원평가 주소 → 좌표 변환 — `scripts/collect_facilities.py` 실행 중. 끝나면 `facilities.json` 확인 후 백엔드 재시작
- [ ] 혜택 ↔ 기관 연결 — `related_facility_type`, 신청방법·구비서류·근거법령 컬럼을 가은과 조율 (혜택 카드 "가까운 ○○ 보기", 기관 상세 연계 혜택이 이걸 씀)
- [ ] `feature/web` → `main` PR
