"""화면 ↔ API 응답 스키마. 원희(챗봇)·가은(매칭) 담당과 협의할 계약서 역할."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, examples=["65세 이상 받을 수 있는 의료 혜택"])
    n_results: int = Field(5, ge=1, le=20)
    region: str | None = Field(None, examples=["서울특별시 마포구"])  # 사용자가 고른 지역 (선택)


class Source(BaseModel):
    title: str
    source: str | None = None  # welfare_central | welfare_local | law | hospital | dementia_center | ...
    metadata: dict = {}        # 근거법령, 소관부처 등 data-rag normalize 결과 그대로


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    mock: bool = False  # RAG 모듈을 못 불러와 샘플 응답을 돌려준 경우 True


class Region(BaseModel):
    province: str
    municipality: str
    lat: float  # 거리 계산 기준점 (시군구청 근처)
    lng: float


class Benefit(BaseModel):
    """가은 health-benefits 브랜치의 benefit / healty_benefit 테이블 컬럼 기준."""

    id: int
    source: str  # central | local
    name: str
    summary_text: str | None = None
    criteria_text: str | None = None  # 소득 등 공식 선정기준 (사용자에게 묻지 않고 그대로 노출)
    source_url: str | None = None
    provider_province: str | None = None
    provider_municipality: str | None = None
    life_cycle_names: list[str] = []
    target_group_names: list[str] = []
    theme_codes: list[str] = []  # 010 신체건강 | 020 정신건강 | 080 임신·출산
    application_status: str = "unknown"  # unknown | scheduled | open | closed
    apply_method: str | None = None  # 신청 방법·장소
    documents: str | None = None     # 구비서류
    legal_basis: str | None = None   # 근거법령
    related_facility_type: str | None = None  # 이 혜택을 받으러 가는 기관 유형 (지도 연결용)


class Facility(BaseModel):
    id: str
    type: str  # hospital | public_health_center | dementia_center | ltc_institution
    name: str
    address: str | None = None
    phone: str | None = None
    lat: float | None = None
    lng: float | None = None
    province: str | None = None
    municipality: str | None = None
    summary: str | None = None  # 목록에 보일 한 줄 설명
    grades: list[str] = []      # 병원평가 등급 (예: "고혈압 1등급")
    services: list[dict] = []   # [{"name": 서비스명, "cost": 비용·조건}]
    stats: list[dict] = []      # [{"label": 항목, "value": 값}] 이용현황
    details: dict = {}          # 운영시간 등 유형별 상세
    data_source: str | None = None  # 출처 데이터셋 이름
    distance_km: float | None = None  # 요청 기준점이 있을 때만 계산
