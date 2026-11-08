"""원희 담당 data-rag 파이프라인의 generate_answer()를 호출한다.

data-rag는 `sys.path.insert(0, ".")` 기준(data-rag 폴더에서 실행)으로 짜여 있어서,
그 폴더를 sys.path에 넣고 import한다. 의존성·Chroma 인덱스·GEMINI_API_KEY가 없거나
답변 생성이 실패하면 RagUnavailable을 낸다.

지역 우선 검색: data-rag의 hybrid_search는 지역을 모른다. 그래서 '서울 노인 돌봄'을 물어도
대구·부산 사업이 상위에 오고, LLM은 "검색결과에 없으면 못 찾았다고 하라"는 규칙대로
'관련 정보를 찾지 못했습니다'라고 답했다. 여기서는 후보를 넉넉히 받아 사용자가 고른 지역 →
전국 자료 순으로 다시 고른 뒤 generate_answer에 넘긴다 (data-rag 코드는 건드리지 않는다).
"""

import contextvars
import logging
import re
import sys
import threading
from pathlib import Path

from app.services import guard

logger = logging.getLogger(__name__)

DATA_RAG_DIR = Path(__file__).resolve().parents[4] / "data-rag"

# 최종으로 넘기는 개수의 몇 배를 후보로 받을지, RRF에 쓰는 dense·BM25 후보 수
CANDIDATE_MULTIPLIER = 4
CANDIDATE_K = 60
# 내 시군구·시도 자료를 원래 검색 순서보다 몇 칸 앞으로 당길지
REGION_BOOST = {3: 4, 2: 2}

_generate_answer = None
_guard_llm: list = []  # [client, model] — 질문 분류용
_hybrid_search = None
_region: contextvars.ContextVar[tuple[str, str | None] | None] = contextvars.ContextVar("rag_region", default=None)


class RagUnavailable(Exception):
    """data-rag 파이프라인을 쓸 수 없음."""


# ── 검색 결과의 지역 판별 ──────────────────────────────

# 전국 단위 자료 (중앙부처 복지사업, 법령, 급여 통계)
NATIONWIDE_SOURCES = {"welfare_central", "law", "welfare_payment"}

# 시도 이름 → 주소에 나올 수 있는 다른 표기 (전남광주통합특별시는 옛 주소도 남아 있다)
PROVINCE_ALIASES = {
    "서울특별시": ("서울",), "부산광역시": ("부산",), "대구광역시": ("대구",), "인천광역시": ("인천",),
    "대전광역시": ("대전",), "울산광역시": ("울산",), "세종특별자치시": ("세종",), "경기도": ("경기",),
    "강원특별자치도": ("강원",), "충청북도": ("충북",), "충청남도": ("충남",),
    "전북특별자치도": ("전북", "전라북도"), "경상북도": ("경북",), "경상남도": ("경남",),
    "제주특별자치도": ("제주",),
    "전남광주통합특별시": ("전남", "전라남도", "광주광역시", "광주"),
}

# 장기요양기관 데이터의 시도 코드 (행정표준코드, 12는 전남광주통합특별시)
SIDO_CODES = {
    "11": "서울특별시", "26": "부산광역시", "27": "대구광역시", "28": "인천광역시", "30": "대전광역시",
    "31": "울산광역시", "36": "세종특별자치시", "41": "경기도", "51": "강원특별자치도", "43": "충청북도",
    "44": "충청남도", "52": "전북특별자치도", "47": "경상북도", "48": "경상남도", "50": "제주특별자치도",
    "12": "전남광주통합특별시", "29": "전남광주통합특별시", "46": "전남광주통합특별시",
    "42": "강원특별자치도", "45": "전북특별자치도",
}


def _split_region(region: str) -> tuple[str, str | None]:
    """'서울특별시 마포구' → ('서울특별시', '마포구')"""
    province, _, municipality = region.strip().partition(" ")
    return province, municipality or None


def _region_in_question(query: str, region: str | None) -> str | None:
    """질문에 다른 지역이 나오면 그 지역을 쓴다 ('내 지역'은 노원구인데 '중랑구에 살고 있어' 같은 경우).

    시군구는 '중랑구'처럼 전체 이름만 본다. '중랑'처럼 줄인 이름까지 보면 '고령자'(고령군),
    '영양'(영양군) 같은 일반 단어가 지역으로 잡힌다. '중구'처럼 여러 시도에 있는 이름은
    질문에 나온 시도 → 내 시도 순으로 고르고, 그래도 하나로 안 정해지면 원래 지역을 쓴다."""
    from app.services.facilities import REGIONS  # noqa: PLC0415

    current = _split_region(region)[0] if region else None
    provinces = [
        p for p in dict.fromkeys(r["province"] for r in REGIONS)
        if any(n in query for n in (p, *PROVINCE_ALIASES.get(p, ())))
    ]
    found = [
        r for r in REGIONS
        if r["municipality"] and re.search(rf"(?<![가-힣]){re.escape(r['municipality'])}", query)
    ]
    for preferred in (provinces, [current]):
        narrowed = [r for r in found if r["province"] in preferred]
        if narrowed:
            found = narrowed
            break
    places = {(r["province"], r["municipality"]) for r in found}
    if len(places) == 1:
        return " ".join(places.pop())
    if not places and len(provinces) == 1 and provinces[0] != current:
        return provinces[0]  # '부산에 사는데'처럼 시도만 말한 경우
    return region


def _hit_place(meta: dict) -> str | None:
    """검색 결과가 어느 지역 자료인지 '시도 시군구 …' 문자열로. 전국 자료나 알 수 없으면 None."""
    source = meta.get("source")
    if source == "welfare_local":
        return meta.get("지역")
    if source in ("hospital", "dementia_center"):
        return meta.get("주소")
    if source in ("ltc_institution", "ltc_institution_search"):
        return SIDO_CODES.get(str(meta.get("siDoCd") or meta.get("시도코드") or ""))
    return None


def _in_province(place: str, province: str) -> bool:
    names = (province, *PROVINCE_ALIASES.get(province, ()))
    return any(place.startswith(n) for n in names)


def _region_rank(meta: dict, province: str, municipality: str | None) -> int:
    """3: 내 시군구, 2: 내 시도, 1: 전국·지역 미상, 0: 다른 지역"""
    if meta.get("source") in NATIONWIDE_SOURCES:
        return 1
    place = _hit_place(meta)
    if not place:
        return 1
    if not _in_province(place, province):
        return 0
    if municipality and municipality in place:
        return 3
    # 다른 시군구의 지자체 사업은 그 주민만 받을 수 있다 (병원·센터 같은 기관은 옆 구도 갈 수 있어 둔다).
    # '서울특별시'처럼 시도 전체 사업은 그대로 둔다
    if municipality and meta.get("source") == "welfare_local" and place.strip().count(" ") >= 1:
        return 0
    return 2


# 질문에서 핵심어를 뽑을 때 버리는 말 (어떤 사업 설명에나 나오는 말)
_STOPWORDS = {
    "알려줘", "알려주세요", "지원", "서비스", "받을", "있는", "있어", "있나요", "어디", "어떻게", "방법",
    "관련", "대한", "정보", "무엇", "뭐가", "가능", "하는", "해줘", "주세요", "혜택", "사업",
}


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", text)
    return [w for w in words if w not in _STOPWORDS]


def _mentions(hit: dict, keywords: list[str]) -> bool:
    """제목·본문에 질문 핵심어가 하나라도 있는지. '의료비를'처럼 조사가 붙은 말은 끝 글자를 떼고도 본다."""
    body = f"{hit['metadata'].get('title', '')} {hit.get('text', '')}"
    return any(w in body or (len(w) >= 3 and w[:-1] in body) for w in keywords)


def _interleave(first: list[dict], second: list[dict]) -> list[dict]:
    out = []
    for i in range(max(len(first), len(second))):
        out.extend(lst[i] for lst in (first, second) if i < len(lst))
    return out


def _regional_search(query_text: str, n_results: int = 5, **kwargs) -> list[dict]:
    """generate_answer 안의 hybrid_search 대신 불린다. 지역이 없으면 원래 검색 그대로."""
    region = _region.get()
    if not region:
        return _hybrid_search(query_text, n_results=n_results, **kwargs)
    province, municipality = region
    size = n_results * CANDIDATE_MULTIPLIER
    # 질문 앞 '[경기도 구리시]'를 붙인 채 검색하면 BM25가 지역 이름만 맞는 엉뚱한 사업
    # (구리시 보훈수당 등)을 끌어오고, 떼면 '마포구치매안심센터'처럼 지역 이름이 핵심인 자료를 놓친다.
    # 그래서 둘 다 검색하고, 지역을 붙여서만 나온 자료는 질문의 핵심어가 들어 있을 때만 쓴다
    plain_text = re.sub(r"^\s*\[[^\]]*\]\s*", "", query_text) or query_text
    plain = _hybrid_search(plain_text, n_results=size, candidate_k=CANDIDATE_K)
    seen = {h["chunk_id"] for h in plain}
    keywords = _keywords(plain_text)
    extra = [
        h for h in _hybrid_search(query_text, n_results=size, candidate_k=CANDIDATE_K)
        if h["chunk_id"] not in seen and _mentions(h, keywords)
    ]
    candidates = _interleave(plain, extra)
    # 관련도(원래 검색 순서)를 기본으로 두고, 다른 지역 자료만 빼고 내 지역 자료를 몇 칸 끌어올린다.
    # 지역만으로 정렬하면 '구리시 임산부'에 구리시 보훈수당처럼 지역만 맞는 자료가 올라온다
    ranks = [_region_rank(h["metadata"], province, municipality) for h in candidates]
    order = sorted(
        (i for i, r in enumerate(ranks) if r > 0),
        key=lambda i: i - REGION_BOOST.get(ranks[i], 0),
    )
    picked = [candidates[i] for i in order[:n_results]]
    # 내 지역·전국 자료가 하나도 없으면 원래 결과라도 넘겨 LLM이 판단하게 한다
    return picked or candidates[:n_results]


# ── data-rag 연결 ─────────────────────────────────────

# data-rag 프롬프트는 "검색결과에 없으면 못 찾았다고 하라"만 있어서, '노원구 치매 무료 검사'처럼
# 전국 공통 제도(치매안심센터 무료 진단검사)는 찾았는데 노원구 기관만 없을 때도 통째로 거절했다.
# 답변에 문서 제목이 안 나오니 출처도 0건이 된다. 찾은 만큼은 안내하도록 규칙을 덧붙인다
PARTIAL_ANSWER_RULES = """
- 질문 앞 [지역]은 사용자가 사는 지역입니다. 질문이 그 지역의 기관·장소를 찾는데 검색결과에 없으면,
  전국 공통 제도나 같은 시도의 기관처럼 관련된 내용을 안내하고, 그 지역 기관은 찾지 못했다고 한 줄로 밝힌 뒤
  제도 안내에 나온 문의처(거주지 보건소·주민센터 등)를 알려 주세요. 검색결과로 답할 수 있는 질문이면
  찾지 못한 지역 자료를 굳이 언급하지 않습니다.
- "관련 정보를 찾지 못했습니다"는 질문과 관련된 내용이 검색결과에 전혀 없을 때만 씁니다.
- 본문과 [출처]에 문서 제목을 쓸 때는 검색결과의 제목을 바꾸지 말고 그대로 씁니다."""

_load_lock = threading.Lock()


def _load():
    global _generate_answer, _hybrid_search
    if _generate_answer:
        return
    # 서버 시작 때 warm_up 스레드와 첫 질문이 동시에 들어와도 한 번만 바꿔 끼운다
    with _load_lock:
        if _generate_answer:
            return
        try:
            if str(DATA_RAG_DIR) not in sys.path:
                sys.path.insert(0, str(DATA_RAG_DIR))
            import pipeline.embed as embed  # noqa: PLC0415
            import pipeline.generate as generate  # noqa: PLC0415
            import pipeline.hybrid_search as hybrid  # noqa: PLC0415
        except Exception as e:  # 의존성 미설치 등
            raise RagUnavailable(f"data-rag 불러오기 실패 ({type(e).__name__}: {e})") from e
        # BGE-M3와 BM25도 이 잠금 안에서 불러온다. data-rag의 get_model()엔 잠금이 없어서, 서버 켜자마자
        # 질문하면 warm_up 스레드와 질문 스레드가 모델을 동시에 불러오다 'Cannot copy out of meta tensor'로 죽었다
        try:
            embed.get_model()
            hybrid._get_bm25_index()
        except Exception as e:
            raise RagUnavailable(f"검색 모델·인덱스 불러오기 실패 ({type(e).__name__}: {e})") from e
        # 원본은 hybrid_search 모듈에서 가져온다 (generate 쪽 이름은 이미 바꿔 끼운 것일 수 있다)
        _hybrid_search = hybrid.hybrid_search
        # generate_answer가 모듈 안에서 부르는 hybrid_search를 지역 우선 검색으로 바꿔 끼운다
        generate.hybrid_search = _regional_search
        if PARTIAL_ANSWER_RULES not in generate.SYSTEM_PROMPT:
            generate.SYSTEM_PROMPT += PARTIAL_ANSWER_RULES
        _generate_answer = generate.generate_answer
        _guard_llm.extend(_guard_client(generate))


def _guard_client(generate) -> list:
    """질문 분류(guard)에 쓸 LLM. data-rag와 같은 Gemini 키·모델을 쓴다. 없으면 규칙 검사만."""
    try:
        from config import GEMINI_API_KEY  # noqa: PLC0415 (data-rag/config.py)
        from openai import OpenAI  # noqa: PLC0415

        if not GEMINI_API_KEY:
            return []
        # 분류는 빨리 끝나야 해서 재시도하지 않는다 (실패하면 통과시키고 답변 단계로 넘어감)
        client = OpenAI(api_key=GEMINI_API_KEY, base_url=generate.GEMINI_BASE_URL, max_retries=0, timeout=15)
        return [client, generate.MODEL]
    except Exception:
        logger.warning("질문 분류용 LLM 준비 실패 — 규칙 검사만 함", exc_info=True)
        return []


def warm_up() -> None:
    """BGE-M3·Chroma·BM25를 미리 불러온다. 안 하면 서버 켜고 첫 질문이 1분 가까이 걸린다.
    LLM은 부르지 않는다(검색만 한 번 돌림)."""
    try:
        _load()
        _hybrid_search("의료 혜택", n_results=1)
        logger.info("RAG 모델·인덱스 미리 불러오기 완료")
    except Exception:  # 실패해도 서버는 뜨고, 질문할 때 503으로 사유가 나간다
        logger.warning("RAG 미리 불러오기 실패", exc_info=True)


def ask(query: str, n_results: int, region: str | None = None, history: list[dict] | None = None) -> dict:
    _load()
    # 서비스 범위를 벗어난 질문(잡담·진단 요청·욕설·프롬프트 조작 등)은 검색 전에 안내 문구로 돌려보낸다
    reason = guard.check(query, history, llm=_guard_llm or None)
    if reason:
        logger.info("질문 차단 (%s): %s", reason, query[:80])
        return guard.blocked_response(reason)
    asked = _region_in_question(query, region)
    if asked != region:
        logger.info("질문에 나온 지역으로 검색: %s → %s", region, asked)
        region = asked
    if region:
        # 답변도 지역 맞춤이 되도록 질문 앞에 사용자가 고른 지역을 붙인다
        query = f"[{region}] {query}"
    token = _region.set(_split_region(region) if region else None)
    try:
        return _generate_answer(query, n_results=n_results, history=history or None)
    except Exception as e:  # chroma_db 없음, LLM 호출 실패 등
        logger.exception("generate_answer 실패")
        if type(e).__name__ == "RateLimitError":
            # 무료 등급은 하루 요청 수 한도가 작다(모델별 하루 20회 등). 하루 한도와 분당 한도를 구분해 안내
            if "per day" in str(e).lower() or "perday" in str(e).lower():
                raise RagUnavailable(
                    "오늘 쓸 수 있는 답변 생성 한도(Gemini 무료 사용량)를 다 썼어요. 내일 다시 시도하거나 API 키 요금제를 확인해 주세요."
                ) from e
            raise RagUnavailable("질문이 몰려 답변 한도(Gemini 사용량)에 걸렸어요. 1분쯤 뒤에 다시 물어봐 주세요.") from e
        raise RagUnavailable(f"답변 생성 실패 ({type(e).__name__})") from e
    finally:
        _region.reset(token)
