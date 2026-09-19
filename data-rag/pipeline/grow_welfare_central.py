"""중앙부처복지서비스는 개발계정 일일 트래픽이 100건뿐이라 하루에 조금씩 늘려간다.

실행할 때마다 Chroma에 이미 들어있는 서비스ID를 확인하고, 목록조회 페이지를 넘겨가며
아직 수집하지 않은 서비스만 골라 상세조회 -> 정규화 -> 청킹 -> 임베딩 -> 적재한다.
매일 이 스크립트만 다시 실행하면 이어서 커버리지가 늘어난다.

사용법: python -m pipeline.grow_welfare_central [--batch 30]
"""

import argparse
import sys

sys.path.insert(0, ".")

from collectors import welfare_central
from pipeline.normalize import normalize_welfare_central_detail
from pipeline.chunk import chunk_document
from pipeline.embed import embed_texts
from pipeline.vectorstore import add_chunks, get_collection

SOURCE = "welfare_central"
MAX_PAGES_PER_RUN = 50  # 무한루프 방지 안전장치


def _existing_service_ids() -> set[str]:
    collection = get_collection()
    result = collection.get(where={"source": SOURCE}, include=[])
    # chunk_id 형식: "welfare_central:<servId>:<chunk_index>"
    return {chunk_id.split(":")[1] for chunk_id in result["ids"]}


def grow(batch_size: int = 30) -> int:
    existing_ids = _existing_service_ids()
    print(f"기존 수집된 서비스 수: {len(existing_ids)}")

    new_docs = []
    seen_this_run: set[str] = set()
    page_no = 1

    while len(new_docs) < batch_size and page_no <= MAX_PAGES_PER_RUN:
        lst = welfare_central.search_welfare_list(page_no=page_no, num_of_rows=batch_size)
        items_node = lst["wantedList"].get("servList")
        items = [items_node] if isinstance(items_node, dict) else (items_node or [])
        if not items:
            print("더 이상 가져올 서비스가 없음 (목록 끝)")
            break

        for item in items:
            serv_id = item["servId"]
            if serv_id in existing_ids or serv_id in seen_this_run:
                continue
            seen_this_run.add(serv_id)
            detail = welfare_central.get_welfare_detail(serv_id)
            new_docs.append(normalize_welfare_central_detail(detail))
            if len(new_docs) >= batch_size:
                break

        page_no += 1

    print(f"신규 수집 문서 수: {len(new_docs)}")
    if not new_docs:
        return 0

    chunks = []
    for doc in new_docs:
        chunks.extend(chunk_document(doc))

    embeddings = embed_texts([c["text"] for c in chunks])
    add_chunks(chunks, embeddings)
    print(f"적재 완료: 신규 {len(chunks)}개 청크 (누적 서비스 {len(existing_ids) + len(new_docs)}건)")
    return len(chunks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=30, help="오늘 새로 가져올 서비스 수")
    args = parser.parse_args()
    grow(args.batch)
