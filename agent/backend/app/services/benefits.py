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
    return {**result, "notice": NOTICE}
