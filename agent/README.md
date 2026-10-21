# 3. 웹·지도·통합 담당 (담당: 소현)

> 기존 "에이전트/오케스트레이션 엔지니어" 역할에서 내용이 바뀌었습니다. 의도 분류·응답 통합 대신, React 웹 전체(4개 화면)와 백엔드 API 연결, 지도 연동을 담당하는 풀스택 역할입니다.

## 담당 업무
- React 웹 프론트엔드 구축 — 챗봇 화면, 혜택 추천 화면, 지도 화면, 병원/보건소 상세 화면
- FastAPI 백엔드 서버 구축 및 각 화면-API 연결
- 지도 API(Kakao/Naver 등) 연동, 병원/보건소 마커 및 상세정보 표시
- 챗봇 화면 ↔ 원희(RAG·챗봇) API 연결, 혜택추천/지도 화면 ↔ 가은(매칭·데이터) API 연결

## 화면 구성
```
React 웹
 ├─ 챗봇 화면              → 원희(RAG + LLM 답변생성) API
 ├─ 혜택 추천 화면          → 가은(매칭) API
 ├─ 지도 화면               → 가은(지역 데이터) + 지도 API
 └─ 병원/보건소 상세 화면    → 가은(지역 데이터) + 지도 API
```

## 협업 포인트
- 원희: 챗봇 질문 → 답변+출처 API 응답 스키마 협의
- 가은: 혜택 매칭 / 지역 매칭 결과 API 응답 스키마 협의

## 실행 방법

백엔드 (FastAPI, `agent/backend`):
```bash
cd agent/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- `/api/chat`은 `data-rag/pipeline/generate.py`의 `generate_answer()`를 그대로 부른다. 실제 답변을 받으려면 같은 venv에 `pip install -r ../../data-rag/requirements.txt`를 하고, `data-rag/.env`(GEMINI_API_KEY)와 `data-rag/chroma_db/`(build_index 실행 결과)가 있어야 한다. 하나라도 없으면 화면 개발이 막히지 않도록 `"mock": true` 샘플 응답을 돌려준다.
- `/api/benefits`, `/api/facilities`는 아직 **샘플 데이터**(`app/services/sample_data.py`)다. 가은 매칭·지역 데이터가 나오면 교체.
- API 문서: http://localhost:8000/docs

프론트엔드 (React + Vite, `agent/frontend`):
```bash
cd agent/frontend
npm install
copy .env.example .env    # VITE_KAKAO_MAP_KEY에 카카오 JavaScript 키 입력
npm run dev               # http://localhost:5173, /api는 8000번으로 프록시
```

| 화면 | 경로 | 호출 API |
| --- | --- | --- |
| 챗봇 | `/` | `POST /api/chat` |
| 혜택 추천 | `/benefits` | `GET /api/benefits?province=&municipality=&life_cycle=` |
| 지도 | `/map` | `GET /api/facilities?type=` |
| 병원/보건소 상세 | `/facilities/:id` | `GET /api/facilities/{id}`, `GET /api/benefits` |

응답 스키마는 `agent/backend/app/schemas.py` 참고 (원희·가은과 협의용).
