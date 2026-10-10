"""검색된 문서를 근거로 LLM이 답변을 생성한다 (RAG 파이프라인의 마지막 단계).

hybrid_search 결과를 프롬프트에 넣어 자연어 답변을 만들고, 답변에 쓰인 출처를 함께 반환한다.
Gemini는 OpenAI 호환 엔드포인트를 제공하므로 openai 클라이언트를 그대로 쓴다.
"""

import argparse
import sys

sys.path.insert(0, ".")

from openai import OpenAI

from config import GEMINI_API_KEY
from pipeline.hybrid_search import hybrid_search

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL = "gemini-3.5-flash"

SYSTEM_PROMPT = """당신은 대한민국 공공 의료정보·복지혜택 안내 AI 에이전트입니다.
아래 [검색결과]에 있는 내용만 근거로 답변하세요. 검색결과에 없는 내용은 추측하지 말고
"관련 정보를 찾지 못했습니다"라고 답하세요.

반드시 지켜야 할 규칙:
- 질병 진단, 치료 처방, 개인 건강 위험도 판정을 하지 않습니다. 정보 제공·안내로만 답변합니다.
- 소득 등 개인정보를 묻거나 추정하지 않습니다. 혜택의 공식 선정기준만 안내합니다.
- 답변 마지막에 "[출처]" 항목으로 실제로 사용한 문서의 제목을 모두 나열합니다."""


def _build_context(hits: list[dict]) -> str:
    return "\n\n".join(
        f"[{i + 1}] {h['metadata'].get('title', '')} ({h['metadata'].get('source', '')})\n{h['text']}"
        for i, h in enumerate(hits)
    )


def _format_sources(hits: list[dict], answer: str) -> list[dict]:
    """검색된 후보 전체가 아니라, LLM이 실제로 답변 본문에서 언급한 제목만 출처로 남긴다."""
    seen = set()
    sources = []
    for h in hits:
        meta = h["metadata"]
        title = meta.get("title")
        if not title or title not in answer:
            continue
        key = (meta.get("source"), title)
        if key in seen:
            continue
        seen.add(key)
        sources.append({"title": title, "source": meta.get("source"), "metadata": meta})
    return sources


def generate_answer(query: str, n_results: int = 5) -> dict:
    """사용자 질문에 대해 RAG 검색 + LLM 답변 생성을 수행한다.

    Returns: {"answer": str, "sources": [{"title": str, "source": str, "metadata": dict}, ...]}
    """
    hits = hybrid_search(query, n_results=n_results)
    if not hits:
        return {"answer": "관련 정보를 찾지 못했습니다.", "sources": []}

    client = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"[검색결과]\n{_build_context(hits)}\n\n[질문]\n{query}"},
        ],
    )

    answer = response.choices[0].message.content
    return {
        "answer": answer,
        "sources": _format_sources(hits, answer),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="*", default=["65세 이상 받을 수 있는 의료 혜택"])
    parser.add_argument("--n", type=int, default=5)
    args = parser.parse_args()

    result = generate_answer(" ".join(args.query), n_results=args.n)
    print(result["answer"])
    print("\n[출처 메타데이터]")
    for s in result["sources"]:
        print(f"- {s['title']} ({s['source']})")
