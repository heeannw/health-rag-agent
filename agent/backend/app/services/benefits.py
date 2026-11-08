"""가은 담당 health_benefits의 의료 혜택 검색(search_benefits)을 호출한다.

healty_benefit 테이블(770건 내외)을 통째로 읽어 메모리에 잠깐 캐시하고, 필터링은
가은의 extract_benefits()에 맡긴다. DB 접속 정보는 저장소 루트 .env(PGHOST 등)를
그대로 쓴다. 패키지를 못 불러오거나 DB를 못 읽으면 BenefitsUnavailable을 낸다.
"""

import logging
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]
CACHE_SECONDS = 600
NOTICE = (
    "분류 일치 후보이며 수급 자격 확정이 아닙니다. 제공기관 지역과 실제 거주 요건은 "
    "다를 수 있으므로 대상·선정기준 원문을 확인하세요."
)

_search = None
_cache: tuple[float, list[dict]] | None = None


class BenefitsUnavailable(Exception):
    """health_benefits 패키지나 healty_benefit DB를 쓸 수 없음."""


def _load():
    global _search
    if _search:
        return
    try:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from health_benefits.recommendation import search_benefits  # noqa: PLC0415
    except Exception as e:
        raise BenefitsUnavailable(f"health_benefits 불러오기 실패 ({type(e).__name__}: {e})") from e
    _search = search_benefits


def _rows() -> list[dict]:
    global _cache
    if _cache and time.monotonic() - _cache[0] < CACHE_SECONDS:
        return _cache[1]
    try:
        rows = _search.load_database()
    except Exception as e:  # psycopg 미설치, .env 없음, 접속 실패 등
        logger.exception("healty_benefit 조회 실패")
        raise BenefitsUnavailable(f"혜택 DB 조회 실패 ({type(e).__name__})") from e
    _cache = (time.monotonic(), rows)
    return rows


# 기관-혜택 직접 매핑 컬럼이 아직 없어서, 혜택 이름·요약·신청방법 키워드로 받으러 가는 기관 유형을 추정한다.
# 지도 기관 상세의 '연계된 혜택'과 혜택 카드의 '가까운 기관 보기'에 쓴다. (DB 컬럼이 생기면 교체)
_CORE_KEYWORDS = {
    "dementia_center": ("치매",),
    "ltc_institution": ("장기요양", "요양원", "요양시설", "방문요양", "노인요양"),
    "hospital": ("의료비", "진료비", "치료비", "수술비", "검사비", "입원", "의료기관", "병원"),
    "public_health_center": ("보건소", "검진", "예방접종"),
}
_METHOD_KEYWORDS = {"dementia_center": ("치매안심센터",), "public_health_center": ("보건소",)}


def _facility_types(b: dict) -> list[str]:
    core = f"{b.get('name') or ''} {b.get('summary_text') or ''}"
    method = b.get("application_method") or ""
    return [
        t for t, words in _CORE_KEYWORDS.items()
        if any(w in core for w in words) or any(w in method for w in _METHOD_KEYWORDS.get(t, ()))
    ]


def _with_facilities(b: dict) -> dict:
    types = _facility_types(b)
    return {**b, "related_facility_types": types, "related_facility_type": b.get("related_facility_type") or (types[0] if types else None)}


def find_by_service(source: str, service_id: str) -> dict | None:
    """챗봇 인용 출처(data-rag)의 서비스 코드로 혜택 한 건을 찾는다.

    source는 data-rag 구분자(welfare_central | welfare_local) 또는 DB 값(central | local).
    상세 화면이 쓰는 display·region_scope는 지역 조건 없이 extract_benefits로 채운다.
    """
    _load()
    source = source.removeprefix("welfare_")
    row = next(
        (r for r in _rows() if r.get("source") == source and str(r.get("source_service_id") or "").strip() == service_id),
        None,
    )
    if row is None:
        return None
    result = _search.extract_benefits([row])
    item = (result["matched"] + result["needs_review"])[0]
    return _with_facilities(item)


def search(
    province: str | None = None,
    municipality: str | None = None,
    life_cycles: list[str] | None = None,
    target_groups: list[str] | None = None,
    themes: list[str] | None = None,
) -> dict:
    _load()
    rows = _rows()
    if themes:
        rows = [r for r in rows if set(themes) & set(r.get("theme_codes") or [])]
    result = _search.extract_benefits(rows, life_cycles, target_groups, province, municipality)
    # 생애주기·대상특성을 골랐을 때 그 분류가 아예 비어 있는 혜택(예: 영유아 선택 시 '농업인 건강보험료')은
    # 목록에서 뺀다. 분류 없는 혜택은 '전체'에서만 보인다. 지역 미상은 그대로 '지역 확인'으로 둔다.
    chosen = {f for f, sel in (("life_cycle_names", life_cycles), ("target_group_names", target_groups)) if sel}
    needs_review = [b for b in result.get("needs_review", []) if not chosen & set(b.get("review_fields") or [])]
    return {
        **result,
        "matched": [_with_facilities(b) for b in result.get("matched", [])],
        "needs_review": [_with_facilities(b) for b in needs_review],
        "notice": NOTICE,
    }
