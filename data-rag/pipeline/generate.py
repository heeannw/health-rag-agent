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


# 이전 대화는 최근 몇 턴만, 긴 답변은 잘라서 넣는다 (토큰 절약)
MAX_HISTORY_MESSAGES = 6
MAX_HISTORY_CHARS = 1500
# 후속 질문을 LLM으로 독립 질문으로 바꿀지 (True면 후속 질문마다 LLM 호출 +1)
REWRITE_WITH_LLM = False

REWRITE_PROMPT = """아래 [이전 대화]와 [후속 질문]을 보고, 후속 질문을 이전 대화 없이도 이해되는
독립적인 검색용 질문 한 문장으로 다시 쓰세요.
- 생략된 대상(어떤 혜택·제도·기관인지)을 이전 대화에서 찾아 채웁니다.
- 질문 앞의 [지역] 표시는 그대로 둡니다.
- 후속 질문이 이미 독립적이면 그대로 돌려줍니다.
- 설명 없이 다시 쓴 질문만 출력합니다."""


def _trim_history(history: list[dict] | None) -> list[dict]:
    """[{role: user|assistant, content}] 중 최근 것만, 내용이 있는 것만 남긴다."""
    turns = [
        {"role": t["role"], "content": t["content"][:MAX_HISTORY_CHARS]}
        for t in (history or [])
        if t.get("role") in ("user", "assistant") and (t.get("content") or "").strip()
    ]
    return turns[-MAX_HISTORY_MESSAGES:]


def _standalone_query(client: OpenAI, query: str, history: list[dict]) -> str:
    """'신청은 어떻게 해?' 같은 후속 질문을 검색이 되는 질문으로 바꾼다.

    기본은 직전 사용자 질문을 붙여서 검색한다 (LLM 호출 없음).
    REWRITE_WITH_LLM이면 LLM이 독립 질문으로 다시 쓴다. 검색은 더 정확하지만
    후속 질문마다 LLM 호출이 1번 더 든다 (무료 등급은 하루 호출 수가 적음)."""
    last_user = next((t["content"] for t in reversed(history) if t["role"] == "user"), "")
    fallback = f"{query} {last_user}".strip()
    if not REWRITE_WITH_LLM:
        return fallback

    dialog = "\n".join(f"{'사용자' if t['role'] == 'user' else '안내'}: {t['content']}" for t in history)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": REWRITE_PROMPT},
                {"role": "user", "content": f"[이전 대화]\n{dialog}\n\n[후속 질문]\n{query}"},
            ],
        )
        rewritten = (response.choices[0].message.content or "").strip()
        if rewritten:
            return rewritten
    except Exception:  # noqa: BLE001 - 재작성 실패는 답변 실패로 이어지지 않게
        pass
    return fallback


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


def generate_answer(query: str, n_results: int = 5, history: list[dict] | None = None) -> dict:
    """사용자 질문에 대해 RAG 검색 + LLM 답변 생성을 수행한다.

    history: 같은 대화의 이전 메시지 [{"role": "user"|"assistant", "content": str}, ...] (선택).
             있으면 후속 질문을 독립 질문으로 바꿔 검색하고, 답변할 때도 이전 대화를 참고한다.

    Returns: {"answer": str, "sources": [{"title": str, "source": str, "metadata": dict}, ...],
              "search_query": str}
    """
    client = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
    turns = _trim_history(history)
    search_query = _standalone_query(client, query, turns) if turns else query

    hits = hybrid_search(search_query, n_results=n_results)
    if not hits:
        return {"answer": "관련 정보를 찾지 못했습니다.", "sources": [], "search_query": search_query}

    # 이전 대화 자체는 messages로 넘기므로, LLM이 다시 쓴 질문이 있을 때만 덧붙인다
    rewritten = REWRITE_WITH_LLM and search_query != query
    question = f"{query}\n(이전 대화를 반영한 질문: {search_query})" if rewritten else query
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *turns,
            {"role": "user", "content": f"[검색결과]\n{_build_context(hits)}\n\n[질문]\n{question}"},
        ],
    )

    answer = response.choices[0].message.content or ""
    return {
        "answer": answer,
        "sources": _format_sources(hits, answer),
        "search_query": search_query,
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
