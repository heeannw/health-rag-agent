"""형태소분석기 없이 쓰는 가벼운 한국어 BM25 인덱스.

정식 형태소 분석(mecab/konlpy 등) 없이도 어느 정도 조사(-을/-를/-이/-가 등) 변화에
강건하도록, 단어 토큰과 함께 한글 2-gram을 같이 색인한다.
"""

import re

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[가-힣]+|[A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    tokens = []
    for word in _TOKEN_RE.findall(text):
        tokens.append(word)
        if re.match(r"^[가-힣]+$", word) and len(word) >= 2:
            tokens.extend(word[i : i + 2] for i in range(len(word) - 1))
    return tokens


class BM25Index:
    def __init__(self, chunk_ids: list[str], texts: list[str]):
        self.chunk_ids = chunk_ids
        self._bm25 = BM25Okapi([tokenize(t) for t in texts])

    def search(self, query: str, n_results: int = 5) -> list[tuple[str, float]]:
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n_results]
        return [(self.chunk_ids[i], float(scores[i])) for i in ranked]


def build_bm25_index() -> BM25Index:
    from pipeline.vectorstore import get_collection

    collection = get_collection()
    result = collection.get(include=["documents"])
    return BM25Index(result["ids"], result["documents"])
