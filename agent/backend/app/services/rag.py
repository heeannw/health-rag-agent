"""원희 담당 data-rag 파이프라인의 generate_answer()를 호출한다.

data-rag는 `sys.path.insert(0, ".")` 기준(data-rag 폴더에서 실행)으로 짜여 있어서,
그 폴더를 sys.path에 넣고 import한다. Chroma 인덱스나 GEMINI_API_KEY가 없으면
화면 개발이 막히지 않도록 샘플 응답을 돌려준다(mock=True).
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_RAG_DIR = Path(__file__).resolve().parents[4] / "data-rag"

_generate_answer = None
_import_error: str | None = None


def _load():
    global _generate_answer, _import_error
    if _generate_answer or _import_error:
        return
    try:
        sys.path.insert(0, str(DATA_RAG_DIR))
        from pipeline.generate import generate_answer  # noqa: PLC0415

        _generate_answer = generate_answer
    except Exception as e:  # 의존성 미설치, chroma_db 없음 등
        _import_error = f"{type(e).__name__}: {e}"
        logger.warning("data-rag 불러오기 실패, 샘플 응답 사용: %s", _import_error)


def ask(query: str, n_results: int, region: str | None = None) -> dict:
    _load()
    if region:
        # 지역 맞춤 검색이 되도록 질문 앞에 사용자가 고른 지역을 붙인다
        query = f"[{region}] {query}"
    if _generate_answer:
        try:
            return {**_generate_answer(query, n_results=n_results), "mock": False}
        except Exception as e:
            logger.exception("generate_answer 실패")
            return _mock(query, f"{type(e).__name__}: {e}")
    return _mock(query, _import_error)


def _mock(query: str, reason: str | None) -> dict:
    return {
        "answer": (
            f"[샘플 응답] '{query}'에 대한 실제 답변은 RAG 파이프라인 연결 후 표시됩니다.\n"
            f"(사유: {reason})"
        ),
        "sources": [{"title": "샘플 출처", "source": "mock", "metadata": {}}],
        "mock": True,
    }
