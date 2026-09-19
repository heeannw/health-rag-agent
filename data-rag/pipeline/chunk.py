"""가벼운 재귀적 텍스트 청커. 외부 의존성 없이 문단 -> 문장 -> 강제분할 순으로
구분자를 시도해 chunk_size를 넘지 않는 청크를 만들고, 청크 사이에 overlap을 둔다.
"""

DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " "]


def _split_by_separator(text: str, separators: list[str]) -> list[str]:
    if not separators:
        return [text]

    sep, rest = separators[0], separators[1:]
    if sep not in text:
        return _split_by_separator(text, rest)

    pieces = [p for p in text.split(sep) if p.strip()]
    return pieces if pieces else [text]


def _units(text: str, chunk_size: int, separators: list[str]) -> list[str]:
    """chunk_size 이하가 될 때까지 구분자를 바꿔가며 재귀적으로 쪼갠 최소 단위 목록."""
    if len(text) <= chunk_size:
        return [text]

    pieces = _split_by_separator(text, separators)
    if len(pieces) == 1:
        # 더 쪼갤 구분자가 없으면 강제로 chunk_size 단위로 자른다.
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    units: list[str] = []
    for piece in pieces:
        if len(piece) > chunk_size:
            units.extend(_units(piece, chunk_size, separators))
        else:
            units.append(piece)
    return units


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100,
    separators: list[str] | None = None,
) -> list[str]:
    """text를 chunk_size(문자수) 이하 청크로 나눈다. 인접 청크는 overlap만큼 겹친다."""
    text = text.strip()
    if not text:
        return []

    separators = separators or DEFAULT_SEPARATORS
    units = _units(text, chunk_size, separators)

    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = f"{current[-overlap:]}\n\n{unit}" if overlap else unit
        else:
            current = unit

    if current:
        chunks.append(current)

    return chunks


def chunk_document(doc: dict, chunk_size: int = 800, overlap: int = 100) -> list[dict]:
    """normalize.py가 만든 Document를 청크 레코드 목록으로 변환.

    각 청크는 벡터DB에 넣을 최종 형태로, 원본 메타데이터에 청크 위치 정보를 더한다.
    """
    pieces = chunk_text(doc["text"], chunk_size=chunk_size, overlap=overlap)
    total = len(pieces)
    return [
        {
            "chunk_id": f"{doc['source']}:{doc['id']}:{i}",
            "source": doc["source"],
            "title": doc["title"],
            "text": piece,
            "metadata": {**doc["metadata"], "chunk_index": i, "total_chunks": total},
        }
        for i, piece in enumerate(pieces)
    ]
