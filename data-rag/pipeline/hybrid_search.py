"""BGE-M3 dense 검색 + BM25 키워드 검색을 Reciprocal Rank Fusion(RRF)으로 결합.

RRF는 각 랭커에서의 순위(rank)만 사용해 점수를 합산하므로, 서로 다른 스케일의
distance(코사인)와 BM25 score를 그대로 더하는 문제를 피할 수 있다.
score(d) = sum( 1 / (k + rank_in_ranker) )  for each ranker the doc appears in
"""

from pipeline.bm25_index import build_bm25_index
from pipeline.embed import embed_query
from pipeline.vectorstore import get_collection, query as dense_query

_bm25_index = None


def _get_bm25_index():
    global _bm25_index
    if _bm25_index is None:
        _bm25_index = build_bm25_index()
    return _bm25_index


def _rrf_merge(rank_lists: list[list[str]], k: int = 60) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranked_ids in rank_lists:
        for rank, chunk_id in enumerate(ranked_ids):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


def hybrid_search(query_text: str, n_results: int = 5, candidate_k: int = 20) -> list[dict]:
    dense_result = dense_query(embed_query(query_text), n_results=candidate_k)
    dense_ids = dense_result["ids"][0]

    bm25_hits = _get_bm25_index().search(query_text, n_results=candidate_k)
    bm25_ids = [chunk_id for chunk_id, _ in bm25_hits]

    fused_scores = _rrf_merge([dense_ids, bm25_ids])
    top_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)[:n_results]

    collection = get_collection()
    fetched = collection.get(ids=top_ids, include=["documents", "metadatas"])
    by_id = {
        cid: {"text": doc, "metadata": meta}
        for cid, doc, meta in zip(fetched["ids"], fetched["documents"], fetched["metadatas"])
    }

    return [
        {"chunk_id": cid, "score": fused_scores[cid], **by_id[cid]}
        for cid in top_ids
        if cid in by_id
    ]
