# 건강 정보·의료 혜택 AI 에이전트

공공데이터 기반 RAG 챗봇과 지역 맞춤 혜택 매칭·지도 서비스를 결합한
"의료 혜택/건강정보를 한눈에 안내하는 AI 에이전트"

## 프로젝트 개요

- **챗봇 화면**: 사용자가 자연어로 질문하면 RAG 파이프라인이 법령·복지·병원평가 등 공공데이터를 검색해 근거·출처와 함께 답변
- **혜택 추천 화면**: 사용자 조건(연령대·지역 등)에 맞는 복지 혜택을 매칭해 추천. 소득은 개인정보 수집 없이 혜택별 공식 선정기준만 노출
- **지도 화면 / 병원·보건소 상세 화면**: 지역 기반으로 의료기관·보건소 위치와 상세정보를 지도에서 확인

> 개인 건강 위험도를 예측·판정하는 기능은 의료법 리스크로 범위에서 제외했습니다. 모든 기능은 "정보 제공·연계"에 한정됩니다.

## 시스템 구성 (React 웹)

```
React 웹
  ├─ 챗봇 화면              (RAG 검색 + LLM 답변생성 + 출처표시 — 원희)
  ├─ 혜택 추천 화면          (지역·혜택 매칭 — 가은)
  ├─ 지도 화면               (지도 연동 — 소현)
  └─ 병원/보건소 상세 화면    (지도 연동 — 소현)
```

## 역할 분담 (3인)

| 담당 | 역할 | 폴더 | 세부 업무 |
| --- | --- | --- | --- |
| 원희 | 1. RAG·챗봇 담당 (AI 핵심 기능) | [`data-rag/`](./data-rag) | 공공 의료·복지 데이터 수집/전처리, 청킹·임베딩, 벡터DB, RAG 검색, LLM 답변 생성, 근거·출처 표시 |
| 가은 | 2. 매칭·데이터 담당 (지역 맞춤 추천) | [`prediction-model/`](./prediction-model) | 사용자 조건 처리, 복지 혜택 조건 매칭, 지역별 의료기관/보건소 데이터 가공, 지역·혜택 매칭 로직, 관련 API |
| 소현 | 3. 웹·지도·통합 담당 (서비스 구현) | [`agent/`](./agent) | 웹 프론트엔드, 백엔드 API 연결, 지도 API 연동, 병원/보건소 마커 및 상세정보, 챗봇·매칭 결과 화면 연결 |

각 담당 상세 업무는 폴더별 README.md 참고.

> **폴더명 안내**: `prediction-model/`, `agent/`는 이전 기획(개인 위험 예측 모델 / 의도분류 에이전트) 당시 이름이 그대로 남아있습니다. 실제 내용은 각각 매칭·데이터(가은), 웹·지도·통합(소현)으로 바뀌었으니 혼동되면 팀 합의 후 `git mv`로 폴더명 변경을 고려하세요.

## 환경변수 (.env)

API 키·DB 접속 정보는 **저장소 루트의 `.env` 하나**로 관리합니다. `data-rag`, `agent/backend`, `agent/frontend`(Vite `envDir`), `health_benefits` 모두 이 파일을 읽습니다.

```bash
copy .env.example .env    # 루트에서 실행 후 값 채우기 (.env는 커밋되지 않음)
```

## 실행 방법 (웹 서비스)

백엔드와 프론트엔드를 터미널 두 개에서 각각 켭니다. 처음 설치, 필요한 키, 자주 나오는 문제는 [`agent/README.md`](./agent/README.md#실행-방법)를 참고하세요.

```bash
# 터미널 1 — 백엔드 (http://localhost:8000)
cd agent/backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

```bash
# 터미널 2 — 프론트엔드 (http://localhost:5173)
cd agent/frontend
npm run dev
```

챗봇 인덱스 빌드 등 RAG 파이프라인 단독 실행은 [`data-rag/README.md`](./data-rag/README.md), 혜택 데이터 수집은 [`health_benefits/`](./health_benefits)를 참고하세요.

## 데이터 출처

| 데이터 | 링크 | 제공 형태 | 쓰는 곳 | 비고 |
| --- | --- | --- | --- | --- |
| 한국사회보장정보원 중앙부처복지서비스 | [15090532](https://www.data.go.kr/data/15090532/openapi.do) | Open API | 챗봇(RAG), 혜택 추천 (`healty_benefit`) | 대상·선정기준·지원내용과 신청방법·신청서식·근거법령 저장 (구비서류는 미저장) |
| 한국사회보장정보원 지자체복지서비스 | [15108347](https://www.data.go.kr/data/15108347/openapi.do) | Open API | 챗봇(RAG), 혜택 추천 (`healty_benefit`) | 위와 같음 |
| 한국사회보장정보원 복지사업 월별 급여지급 현황 | [15009571](https://www.data.go.kr/data/15009571/fileData.do) | 파일데이터(odcloud API) | 챗봇(RAG) | 지급 통계 |
| 건강보험심사평가원 병원평가정보서비스 | [15094093](https://www.data.go.kr/data/15094093/openapi.do) | Open API | 챗봇(RAG), 지도·기관 상세 | 주소만 제공 → 카카오 주소 검색으로 좌표 변환. `asmGrdNN` 항목명은 활용가이드(2025-02-19) 기준 |
| 전국치매센터표준데이터 | [15021138](https://www.data.go.kr/data/15021138/standard.do) | 표준데이터 API | 챗봇(RAG), 지도·기관 상세 | 위도·경도, 인력, 프로그램 포함 |
| 국민건강보험공단 장기요양기관 검색 | [15059029](https://www.data.go.kr/data/15059029/openapi.do) | Open API | 챗봇(RAG), 지도 | 주소·전화 없음(시도·시군구 코드만) → 카카오 키워드 검색 후 시군구 코드 일치 확인 |
| 법제처 국가법령정보 공유서비스 | [15000115](https://www.data.go.kr/data/15000115/openapi.do) | Open API | 챗봇(RAG) | 목록조회만 사용 — 법령명·소관부처·시행일자 등 메타데이터 (조문 원문 미포함) |
| 카카오 로컬 API (장소·주소 검색, 좌표→행정구역) | [Kakao Developers](https://developers.kakao.com/docs/latest/ko/local/dev-guide) | Open API | 지도(내 주변 병원·보건소·치매안심센터·요양원), 현재 위치 → 지역, 공공데이터 좌표 변환 | 보건소 위치는 이것 외 출처 없음 |
| Supabase (PostgreSQL) | — | DB | 혜택 추천 | 위 복지서비스 수집 결과(`benefit`, `healty_benefit`) 저장소 |
