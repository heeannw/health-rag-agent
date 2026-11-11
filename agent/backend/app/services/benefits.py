"""health_benefits의 혜택 검색 연결. healty_benefit을 캐시하고 필터링은 extract_benefits()에 맡긴다."""

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
        if _cache:  # 예전 데이터가 있으면 그걸 계속 쓴다
            logger.warning("healty_benefit 조회 실패 — 예전 캐시 사용", exc_info=True)
            # 요청마다 접속을 기다리지 않게 1분 뒤에 다시 시도
            _cache = (time.monotonic() - CACHE_SECONDS + 60, _cache[1])
            return _cache[1]
        logger.exception("healty_benefit 조회 실패")
        raise BenefitsUnavailable(f"혜택 DB 조회 실패 ({type(e).__name__})") from e
    _cache = (time.monotonic(), rows)
    return rows


# 기관-혜택 매핑 컬럼이 없어 키워드로 관련 기관 유형을 추정 (기관 상세 '연계된 혜택'용)
_CORE_KEYWORDS = {
    "ltc_institution": ("장기요양", "요양원", "요양시설", "방문요양", "노인요양"),
    "hospital": ("의료비", "진료비", "치료비", "수술비", "검사비", "입원", "의료기관", "병원"),
    "public_health_center": ("보건소", "검진", "예방접종"),
}
_METHOD_KEYWORDS = {"public_health_center": ("보건소",)}


def _facility_types(b: dict) -> list[str]:
    core = f"{b.get('name') or ''} {b.get('summary_text') or ''}"
    method = b.get("application_method") or ""
    return [
        t for t, words in _CORE_KEYWORDS.items()
        if any(w in core for w in words) or any(w in method for w in _METHOD_KEYWORDS.get(t, ()))
    ]


def _with_facilities(b: dict) -> dict:
    return {**b, "related_facility_types": _facility_types(b)}


def find_by_service(source: str, service_id: str) -> dict | None:
    """챗봇 출처의 서비스 코드로 혜택 한 건. source는 welfare_central|welfare_local 또는 central|local."""
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
    # 고른 생애주기·대상특성 분류가 비어 있는 혜택은 뺀다 (지역 미상은 '지역 확인'으로 둔다)
    chosen = {f for f, sel in (("life_cycle_names", life_cycles), ("target_group_names", target_groups)) if sel}
    needs_review = [b for b in result.get("needs_review", []) if not chosen & set(b.get("review_fields") or [])]
    return {
        **result,
        "matched": [_with_facilities(b) for b in result.get("matched", [])],
        "needs_review": [_with_facilities(b) for b in needs_review],
        "notice": NOTICE,
    }
