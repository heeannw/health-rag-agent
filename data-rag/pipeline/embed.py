"""BGE-M3 임베딩 래퍼. 최초 호출 시 모델을 로드하고 이후 재사용한다."""

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("BAAI/bge-m3")
    return _model


def embed_texts(texts: list[str], batch_size: int = 16) -> list[list[float]]:
    """텍스트 목록을 정규화된 dense 임베딩 벡터 목록으로 변환."""
    model = get_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]
