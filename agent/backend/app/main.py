"""웹 4개 화면이 호출하는 FastAPI 서버.

실행 (agent/backend 폴더에서):
    uvicorn app.main:app --reload --port 8000
"""

import threading
from contextlib import asynccontextmanager
from math import asin, cos, radians, sin, sqrt

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import Benefit, BenefitsResponse, ChatRequest, ChatResponse, Facility, Region
from app.services import benefits as benefit_search
from app.services import rag
from app.services.facilities import FACILITIES, REGIONS

@asynccontextmanager
async def lifespan(_: FastAPI):
    # 모델 로딩(수십 초)이 서버 시작을 막지 않도록 백그라운드에서 미리 불러온다
    threading.Thread(target=rag.warm_up, daemon=True).start()
    yield


app = FastAPI(title="보듬 · 의료·복지 안내 AI 에이전트 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(rag.RagUnavailable)
@app.exception_handler(benefit_search.BenefitsUnavailable)
async def unavailable(_: Request, exc: Exception):
    # 연결된 담당 모듈(RAG·혜택 DB)을 못 쓰면 503으로 사유를 알려준다
    return JSONResponse(status_code=503, content={"detail": str(exc)})


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
    history = [t.model_dump() for t in req.history]
    return await run_in_threadpool(rag.ask, req.query, req.n_results, req.region, history)


# 지역은 data/regions.json, 혜택은 health_benefits 검색, 기관은 data/facilities.json.
@app.get("/api/regions", response_model=list[Region])
def regions():
    return REGIONS


@app.get("/api/benefits", response_model=BenefitsResponse)
async def benefits(
    province: str | None = None,
    municipality: str | None = None,
    life_cycle: str | None = Query(None, description="쉼표 구분 생애주기(OR). 예: 노년, 청년, 임신·출산"),
    target_group: str | None = Query(None, description="쉼표 구분 대상특성(OR). 예: 장애인"),
    themes: str | None = Query(None, description="쉼표 구분 주제코드. 예: 010,020"),
):
    if municipality and not province:
        raise HTTPException(400, "시군구를 선택하려면 시도를 함께 입력하세요.")
    # 첫 호출은 DB 조회라 스레드풀에서 실행
    return await run_in_threadpool(
        benefit_search.search,
        province, municipality, _split(life_cycle), _split(target_group), _split(themes),
    )


@app.get("/api/benefits/by-service/{source}/{service_id}", response_model=Benefit)
async def benefit_by_service(source: str, service_id: str):
    """챗봇 인용 출처의 복지서비스 코드(source_service_id)로 혜택 한 건 조회."""
    if source not in ("welfare_central", "welfare_local", "central", "local"):
        raise HTTPException(400, "source는 welfare_central 또는 welfare_local 이어야 합니다.")
    found = await run_in_threadpool(benefit_search.find_by_service, source, service_id.strip())
    if found is None:
        raise HTTPException(404, "혜택을 찾을 수 없습니다")
    return found


@app.get("/api/facilities", response_model=list[Facility])
def facilities(
    types: str | None = Query(None, description="쉼표 구분 기관 유형. 예: hospital,dementia_center"),
    q: str | None = Query(None, description="기관명·설명 검색어"),
    province: str | None = None,
    municipality: str | None = None,
    lat: float | None = Query(None, description="거리 기준점 위도"),
    lng: float | None = Query(None, description="거리 기준점 경도"),
    radius_km: float | None = Query(None, gt=0, description="기준점에서 이 거리 안의 기관만 (lat·lng 필요)"),
    limit: int | None = Query(None, ge=1, le=2000, description="가까운 순으로 이 개수까지만"),
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
        if radius_km is not None:
            result = [f for f in result if f.get("distance_km") is not None and f["distance_km"] <= radius_km]
        result.sort(key=lambda f: f.get("distance_km") if f.get("distance_km") is not None else float("inf"))
    return result[:limit] if limit else result


@app.get("/api/facilities/{facility_id}", response_model=Facility)
def facility_detail(facility_id: str, lat: float | None = None, lng: float | None = None):
    for f in FACILITIES:
        if f["id"] == facility_id:
            if lat is not None and lng is not None and f.get("lat"):
                return {**f, "distance_km": round(_distance_km(lat, lng, f["lat"], f["lng"]), 1)}
            return f
    raise HTTPException(404, "기관을 찾을 수 없습니다")
