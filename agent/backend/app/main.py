"""웹 4개 화면이 호출하는 FastAPI 서버.

실행 (agent/backend 폴더에서):
    uvicorn app.main:app --reload --port 8000
"""

from math import asin, cos, radians, sin, sqrt

from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import Benefit, ChatRequest, ChatResponse, Facility, Region
from app.services import rag
from app.services.sample_data import BENEFITS, FACILITIES, REGIONS

app = FastAPI(title="건강 정보·의료 혜택 AI 에이전트 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _split(value: str | None) -> list[str]:
    return [v for v in (value or "").split(",") if v]


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 사이 직선거리 (하버사인)."""
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # 임베딩·LLM 호출이 동기 코드라 스레드풀에서 실행
    return await run_in_threadpool(rag.ask, req.query, req.n_results, req.region)


# TODO(가은 API 연동): 아래 엔드포인트는 샘플 데이터. 매칭 로직/DB 연결되면 교체.
@app.get("/api/regions", response_model=list[Region])
def regions():
    return REGIONS


@app.get("/api/benefits", response_model=list[Benefit])
def benefits(
    province: str | None = None,
    municipality: str | None = None,
    life_cycle: str | None = Query(None, description="예: 노년, 청년, 임신·출산"),
    themes: str | None = Query(None, description="쉼표 구분 주제코드. 예: 010,020"),
):
    result = BENEFITS
    if province:
        # 중앙부처(central) 혜택은 지역 제한 없이 항상 포함
        result = [b for b in result if b["source"] == "central" or b["provider_province"] == province]
    if municipality:
        result = [b for b in result if b["source"] == "central" or b["provider_municipality"] == municipality]
    if life_cycle:
        result = [b for b in result if life_cycle in b["life_cycle_names"]]
    if theme_list := _split(themes):
        result = [b for b in result if set(theme_list) & set(b["theme_codes"])]
    return result


@app.get("/api/facilities", response_model=list[Facility])
def facilities(
    types: str | None = Query(None, description="쉼표 구분 기관 유형. 예: hospital,dementia_center"),
    q: str | None = Query(None, description="기관명·설명 검색어"),
    province: str | None = None,
    municipality: str | None = None,
    lat: float | None = Query(None, description="거리 기준점 위도"),
    lng: float | None = Query(None, description="거리 기준점 경도"),
):
    result = FACILITIES
    if type_list := _split(types):
        result = [f for f in result if f["type"] in type_list]
    if q:
        result = [f for f in result if q in f["name"] or q in (f.get("summary") or "")]
    if province:
        result = [f for f in result if f["province"] == province]
    if municipality:
        result = [f for f in result if f["municipality"] == municipality]
    if lat is not None and lng is not None:
        result = [
            {**f, "distance_km": round(_distance_km(lat, lng, f["lat"], f["lng"]), 1)} if f.get("lat") else f
            for f in result
        ]
        result.sort(key=lambda f: f.get("distance_km") if f.get("distance_km") is not None else float("inf"))
    return result


@app.get("/api/facilities/{facility_id}", response_model=Facility)
def facility_detail(facility_id: str, lat: float | None = None, lng: float | None = None):
    for f in FACILITIES:
        if f["id"] == facility_id:
            if lat is not None and lng is not None and f.get("lat"):
                return {**f, "distance_km": round(_distance_km(lat, lng, f["lat"], f["lng"]), 1)}
            return f
    raise HTTPException(404, "기관을 찾을 수 없습니다")
