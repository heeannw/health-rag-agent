"""API 요청·응답 스키마."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    """같은 대화의 이전 메시지 한 건."""

    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=8000)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, examples=["65세 이상 받을 수 있는 의료 혜택"])
    n_results: int = Field(5, ge=1, le=20)
    region: str | None = Field(None, examples=["서울특별시 마포구"])  # 사용자가 고른 지역 (선택)
    # 이전 대화(오래된 것부터), 후속 질문 맥락용
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)


class Source(BaseModel):
    title: str
    source: str | None = None  # welfare_central | welfare_local | law | hospital | dementia_center | ...
    metadata: dict = {}        # 근거법령, 소관부처 등 data-rag normalize 결과 그대로


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    # 범위 밖 질문으로 막힌 사유: off_topic | diagnosis | abusive | injection | gibberish | too_long | crisis
    blocked: str | None = None


class Region(BaseModel):
    province: str
    municipality: str | None = None  # None이면 시도 전체
    lat: float  # 거리 계산 기준점 (시군구청 근처)
    lng: float


class BenefitDisplay(BaseModel):
    """search_benefits가 만들어 주는 화면 표시 문구. 값이 없으면 '대상 원문 확인'."""

    life_cycle: str
    target_group: str
    region: str


class ApplicationForm(BaseModel):
    name: str
    link: str | None = None


class Benefit(BaseModel):
    """가은 health_benefits의 healty_benefit 테이블 컬럼 + search_benefits 판정 결과."""

    id: int
    source: str  # central | local
    name: str
    summary_text: str | None = None
    target_text: str | None = None
    criteria_text: str | None = None  # 공식 선정기준 원문
    benefit_text: str | None = None
    source_url: str | None = None
    provider_province: str | None = None
    provider_municipality: str | None = None
    life_cycle_names: list[str] | None = None  # NULL은 '전체 대상'이 아니라 원문 미확인
    target_group_names: list[str] | None = None
    theme_codes: list[str] = []  # 010 신체건강 | 020 정신건강 | 080 임신·출산
    application_status: str = "unknown"  # unknown | scheduled | open | closed
    application_start_date: str | None = None
    application_deadline: str | None = None
    application_method: str | None = None  # 신청 방법·장소
    application_forms: list[ApplicationForm] | None = None  # 신청 서식·안내 첨부파일 (복지로)
    legal_basis: list[str] | None = None   # 근거법령·조례 이름
    related_facility_types: list[str] = []  # 키워드로 추정한 관련 기관 유형
    display: BenefitDisplay
    region_scope: str  # nationwide | regional | unknown
    review_fields: list[str] = []  # 원문 확인이 필요한 조건


class BenefitsResponse(BaseModel):
    matched: list[Benefit]       # 선택한 조건과 분류가 일치
    needs_review: list[Benefit]  # 불일치는 없지만 조건 정보가 없어 원문 확인이 필요
    notice: str


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
