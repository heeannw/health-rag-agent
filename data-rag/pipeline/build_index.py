"""공공데이터 API에서 문서를 수집 -> 정규화 -> 청킹 -> 임베딩 -> Chroma 적재까지 실행하는 스크립트.

사용법: python -m pipeline.build_index [--rows N]
"""

import argparse
import sys

sys.path.insert(0, ".")

from collectors import welfare_central, welfare_local, law, hospital, dementia_center
from pipeline.normalize import (
    normalize_welfare_central_detail,
    normalize_welfare_local_detail,
    normalize_law_item,
    normalize_hospital_item,
    normalize_dementia_center_item,
)
from pipeline.chunk import chunk_document
from pipeline.embed import embed_texts
from pipeline.vectorstore import add_chunks


def _as_list(node):
    return [node] if isinstance(node, dict) else (node or [])


def collect_documents(rows: int) -> list[dict]:
    docs = []

    lst = welfare_central.search_welfare_list(num_of_rows=rows)
    for item in _as_list(lst["wantedList"].get("servList")):
        detail = welfare_central.get_welfare_detail(item["servId"])
        docs.append(normalize_welfare_central_detail(detail))

    lst = welfare_local.search_welfare_list(num_of_rows=rows)
    for item in _as_list(lst["wantedList"].get("servList")):
        detail = welfare_local.get_welfare_detail(item["servId"])
        docs.append(normalize_welfare_local_detail(detail))

    lst = law.search_law("국민건강보험법", num_of_rows=rows)
    for item in _as_list(lst["LawSearch"].get("law")):
        docs.append(normalize_law_item(item))

    resp = hospital.search_hospital_assessment(num_of_rows=rows)
    for item in _as_list(resp["response"]["body"]["items"].get("item")):
        docs.append(normalize_hospital_item(item))

    resp = dementia_center.search_dementia_centers(num_of_rows=rows)
    for item in _as_list(resp["body"]["items"].get("item")):
        docs.append(normalize_dementia_center_item(item))

    return docs


def build(rows: int = 5) -> int:
    docs = collect_documents(rows)
    print(f"수집한 문서 수: {len(docs)}")

    all_chunks = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc))
    print(f"생성된 청크 수: {len(all_chunks)}")

    if not all_chunks:
        return 0

    texts = [c["text"] for c in all_chunks]
    embeddings = embed_texts(texts)
    add_chunks(all_chunks, embeddings)
    print(f"Chroma에 적재 완료: {len(all_chunks)}개 청크")
    return len(all_chunks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=5, help="소스별로 가져올 문서 수")
    args = parser.parse_args()
    build(args.rows)
