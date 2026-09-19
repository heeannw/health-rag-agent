"""벡터DB 검색 테스트용 스크립트. 기본은 하이브리드(BGE-M3 + BM25) 검색.

사용법:
  python -m pipeline.search "65세 이상 받을 수 있는 의료 혜택"
  python -m pipeline.search --dense-only "질의문"   # dense 단독 검색과 비교하고 싶을 때
"""

import argparse
import sys

sys.path.insert(0, ".")

from pipeline.embed import embed_query
from pipeline.hybrid_search import hybrid_search
from pipeline.vectorstore import query as dense_query


def search(text: str, n_results: int = 5, dense_only: bool = False):
    if dense_only:
        result = dense_query(embed_query(text), n_results=n_results)
        hits = [
            {"score": -dist, "source": meta.get("source"), "title": meta.get("title"), "text": doc}
            for doc, meta, dist in zip(
                result["documents"][0], result["metadatas"][0], result["distances"][0]
            )
        ]
    else:
        hits = [
            {"score": h["score"], "source": h["metadata"].get("source"), "title": h["metadata"].get("title"), "text": h["text"]}
            for h in hybrid_search(text, n_results=n_results)
        ]

    for h in hits:
        print(f"--- score={h['score']:.4f} | source={h['source']} | title={h['title']} ---")
        print(h["text"][:200])
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="*", default=["65세 이상 받을 수 있는 의료 혜택"])
    parser.add_argument("--dense-only", action="store_true", help="BM25 없이 BGE-M3 dense 검색만 사용")
    parser.add_argument("--n", type=int, default=5)
    args = parser.parse_args()
    search(" ".join(args.query), n_results=args.n, dense_only=args.dense_only)
