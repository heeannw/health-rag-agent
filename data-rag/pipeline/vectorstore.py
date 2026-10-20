"""ChromaDB 기반 벡터스토어. 임베딩은 embed.py에서 미리 계산해 넘겨받는다(Chroma 기본 임베딩함수 미사용)."""

from pathlib import Path

import chromadb

PERSIST_DIR = str(Path(__file__).parent.parent / "chroma_db")
COLLECTION_NAME = "health_rag"


def _sanitize_metadata(metadata: dict) -> dict:
    """Chroma는 메타데이터 값으로 str/int/float/bool만 허용 -> None 제외, 그 외는 문자열화."""
    clean = {}
    for k, v in metadata.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            clean[k] = v
        else:
            clean[k] = str(v)
    return clean


def get_collection():
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    return client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def add_chunks(chunks: list[dict], embeddings: list[list[float]]) -> None:
    if not chunks:
        return
    collection = get_collection()
    collection.upsert(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=[
            _sanitize_metadata({**c["metadata"], "source": c["source"], "title": c["title"]})
            for c in chunks
        ],
    )


def query(query_embedding: list[float], n_results: int = 5, where: dict | None = None) -> dict:
    collection = get_collection()
    return collection.query(query_embeddings=[query_embedding], n_results=n_results, where=where)
