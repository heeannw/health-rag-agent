"""원희 담당 data-rag 파이프라인의 generate_answer()를 호출한다.

data-rag는 `sys.path.insert(0, ".")` 기준(data-rag 폴더에서 실행)으로 짜여 있어서,
그 폴더를 sys.path에 넣고 import한다. 의존성·Chroma 인덱스·GEMINI_API_KEY가 없거나
답변 생성이 실패하면 RagUnavailable을 낸다.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_RAG_DIR = Path(__file__).resolve().parents[4] / "data-rag"

_generate_answer = None


class RagUnavailable(Exception):
    """data-rag 파이프라인을 쓸 수 없음."""


def _load():
    global _generate_answer
    if _generate_answer:
        return
    try:
        if str(DATA_RAG_DIR) not in sys.path:
            sys.path.insert(0, str(DATA_RAG_DIR))
        from pipeline.generate import generate_answer  # noqa: PLC0415
    except Exception as e:  # 의존성 미설치 등
        raise RagUnavailable(f"data-rag 불러오기 실패 ({type(e).__name__}: {e})") from e
    _generate_answer = generate_answer


def ask(query: str, n_results: int, region: str | None = None) -> dict:
    _load()
    if region:
        # 지역 맞춤 검색이 되도록 질문 앞에 사용자가 고른 지역을 붙인다
        query = f"[{region}] {query}"
    try:
        return _generate_answer(query, n_results=n_results)
    except Exception as e:  # chroma_db 없음, LLM 호출 실패 등
        logger.exception("generate_answer 실패")
        raise RagUnavailable(f"답변 생성 실패 ({type(e).__name__})") from e
