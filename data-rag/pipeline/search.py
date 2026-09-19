"""벡터DB에서 유사도 검색 테스트용 스크립트.

사용법: python -m pipeline.search "65세 이상 받을 수 있는 의료 혜택"
"""

import sys

sys.path.insert(0, ".")

from pipeline.embed import embed_query
from pipeline.vectorstore import query


def search(text: str, n_results: int = 5):
    q_embedding = embed_query(text)
    result = query(q_embedding, n_results=n_results)

    for doc, meta, dist in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        print(f"--- distance={dist:.4f} | source={meta.get('source')} | title={meta.get('title')} ---")
        print(doc[:200])
        print()


if __name__ == "__main__":
    query_text = " ".join(sys.argv[1:]) or "65세 이상 받을 수 있는 의료 혜택"
    search(query_text)
