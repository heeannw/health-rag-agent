"""Recall@k 측정 스크립트 (사람이 라벨링한 쿼리셋이 없어 self-retrieval 방식 사용).

각 청크에서 쿼리를 두 가지 방식으로 자동 생성한다:
  - title 쿼리: 청크의 title(서비스명/법령명/기관명 등) 그대로 사용 -> "정확한 대상 검색" 시뮬레이션
  - snippet 쿼리: 청크 본문 중 제목이 아닌 한 줄을 뽑아 앞부분만 사용 -> "내용 기반 검색" 시뮬레이션
그 다음 해당 쿼리로 검색했을 때 원래 청크가 top-k 안에 다시 잡히는지로 Recall@k를 계산한다.
dense(BGE-M3 단독)와 hybrid(BGE-M3 + BM25 RRF)를 비교한다.

사용법: python -m pipeline.eval [--sample 150]
"""

import argparse
import random
import re
import sys

sys.path.insert(0, ".")

from pipeline.embed import embed_query
from pipeline.hybrid_search import hybrid_search
from pipeline.vectorstore import get_collection, query as dense_query

K_VALUES = [1, 3, 5, 10]


def _snippet_query(text: str, title: str) -> str | None:
    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip() and not line.strip().startswith("#") and line.strip() != title
    ]
    if not lines:
        return None
    line = random.choice(lines)
    line = re.sub(r"^[①②③④⑤⑥⑦⑧⑨\-\s]+", "", line)
    return line[:40] if len(line) > 40 else line


def build_eval_queries(sample_size: int) -> list[dict]:
    collection = get_collection()
    all_docs = collection.get(include=["documents", "metadatas"])
    n = len(all_docs["ids"])
    sample_idx = random.sample(range(n), min(sample_size, n))

    queries = []
    for i in sample_idx:
        chunk_id = all_docs["ids"][i]
        text = all_docs["documents"][i]
        title = all_docs["metadatas"][i].get("title", "")

        if title:
            queries.append({"chunk_id": chunk_id, "query": title, "type": "title"})

        snippet = _snippet_query(text, title)
        if snippet:
            queries.append({"chunk_id": chunk_id, "query": snippet, "type": "snippet"})

    return queries


def recall_at_k(eval_queries: list[dict], max_k: int, mode: str) -> dict[int, float]:
    hits = {k: 0 for k in K_VALUES if k <= max_k}

    for item in eval_queries:
        if mode == "dense":
            result = dense_query(embed_query(item["query"]), n_results=max_k)
            retrieved_ids = result["ids"][0]
        else:
            hits_list = hybrid_search(item["query"], n_results=max_k)
            retrieved_ids = [h["chunk_id"] for h in hits_list]

        for k in hits:
            if item["chunk_id"] in retrieved_ids[:k]:
                hits[k] += 1

    total = len(eval_queries)
    return {k: hits[k] / total for k in hits}


def main(sample_size: int):
    random.seed(42)
    eval_queries = build_eval_queries(sample_size)
    print(f"평가 쿼리 수: {len(eval_queries)}")

    max_k = max(K_VALUES)
    for mode in ["dense", "hybrid"]:
        recalls = recall_at_k(eval_queries, max_k, mode)
        print(f"\n[{mode}]")
        for k, v in recalls.items():
            print(f"  Recall@{k}: {v:.3f}")

        by_type: dict[str, list[dict]] = {}
        for item in eval_queries:
            by_type.setdefault(item["type"], []).append(item)
        for qtype, items in by_type.items():
            r = recall_at_k(items, max_k, mode)
            print(f"  ({qtype}) Recall@{max_k}: {r[max_k]:.3f} (n={len(items)})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=150)
    args = parser.parse_args()
    main(args.sample)
