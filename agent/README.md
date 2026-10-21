# 3. 웹·지도·통합 담당 (담당: 소현)

React 웹 4개 화면과 FastAPI 백엔드를 만들고, 원희(RAG·챗봇)·가은(매칭·데이터) 결과를 화면에 연결하는 역할입니다.

## 진행 현황

| 구분 | 상태 | 내용 |
| --- | --- | --- |
| 웹 기본 틀 | ✅ | React + Vite, 4개 화면 라우팅, 데스크톱 사이드바 / 모바일 하단 탭바 |
| 디자인 | ✅ | 색상(메인 `#D7F6F7`, 강조 `#71BAF6`·`#FFC9CA`), 유리 패널, 전체 배경 그라데이션, Lucide 아이콘 |
| 백엔드 API | ✅ | FastAPI. 챗봇은 data-rag와 연결, 혜택·기관은 **샘플 데이터** |
| 챗봇 ↔ RAG 연동 | 🟡 | `generate_answer()` 호출 구조 완료. 실제 답변은 data-rag 설치·인덱스·키 필요 |
| 혜택·기관 ↔ 가은 데이터 | ⬜ | 응답 형식만 정해둠(`schemas.py`). 가은 DB/API 확정 후 교체 |
| 카카오맵 | 🟡 | 컴포넌트 완료. JavaScript 키 발급·도메인 등록 필요 |

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
│           ├── rag.py        # data-rag generate_answer() 호출, 실패 시 샘플 응답
│           └── sample_data.py  # 임시 혜택·기관·지역 데이터 (가은 데이터로 교체 예정)
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
| POST | `/api/chat` | `{query, region}` → `{answer, sources, mock}` |
| GET | `/api/regions` | 선택 가능한 지역과 기준 좌표 |
| GET | `/api/benefits` | `province`, `municipality`, `life_cycle`, `themes`(쉼표 구분) |
| GET | `/api/facilities` | `types`(쉼표 구분), `q`, `lat`, `lng`(거리 계산) |
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
- 챗봇 실제 답변을 받으려면 같은 venv에 `pip install -r ../../data-rag/requirements.txt`, 그리고 `data-rag/.env`(GEMINI_API_KEY)와 `data-rag/chroma_db/`(build_index 결과)가 필요합니다. 없으면 `"mock": true` 샘플 응답이 나옵니다.

프론트엔드:
```bash
cd agent/frontend
npm install
copy .env.example .env    # VITE_KAKAO_MAP_KEY에 카카오 JavaScript 키 입력
npm run dev               # http://localhost:5173 (/api는 8000번으로 프록시)
```
- React는 `~19.2.9`로 고정되어 있습니다 (`@react-three/fiber`가 19.3 미만만 지원).

## 남은 일

- [ ] 카카오 JavaScript 키 발급, `http://localhost:5173` 도메인 등록
- [ ] 가은 혜택·기관 데이터 연동 (`sample_data.py` → 실제 DB/API), 지역코드 통일
- [ ] 보건소 위치 데이터 확보 (현재 확정 데이터 목록에 없음)
- [ ] 병원평가 데이터 주소 → 좌표 변환 (카카오 주소 검색 API)
- [ ] 기관-혜택 직접 매핑 (현재는 같은 지역 + 기관 유형 기준)
- [ ] `feature/web` → `main` PR
