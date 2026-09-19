"""파이프라인 수동 점검용 스크립트. 실제 API를 호출해 정규화+청킹 결과를 확인한다."""
import json
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


def get_list_items(resp, path):
    node = resp
    for key in path:
        node = node[key]
    return [node] if isinstance(node, dict) else node


def main():
    all_chunks = []

    # 1) 중앙부처복지서비스 상세
    lst = welfare_central.search_welfare_list(num_of_rows=2)
    for item in get_list_items(lst, ["wantedList", "servList"]):
        detail = welfare_central.get_welfare_detail(item["servId"])
        doc = normalize_welfare_central_detail(detail)
        all_chunks.extend(chunk_document(doc))

    # 2) 지자체복지서비스 상세
    lst = welfare_local.search_welfare_list(num_of_rows=2)
    for item in get_list_items(lst, ["wantedList", "servList"]):
        detail = welfare_local.get_welfare_detail(item["servId"])
        doc = normalize_welfare_local_detail(detail)
        all_chunks.extend(chunk_document(doc))

    # 3) 법령정보 (메타데이터 중심)
    lst = law.search_law("국민건강보험법")
    for item in get_list_items(lst, ["LawSearch", "law"]):
        doc = normalize_law_item(item)
        all_chunks.extend(chunk_document(doc))

    # 4) 병원평가
    resp = hospital.search_hospital_assessment(num_of_rows=2)
    for item in get_list_items(resp, ["response", "body", "items", "item"]):
        doc = normalize_hospital_item(item)
        all_chunks.extend(chunk_document(doc))

    # 5) 치매센터
    resp = dementia_center.search_dementia_centers(num_of_rows=2)
    for item in get_list_items(resp, ["body", "items", "item"]):
        doc = normalize_dementia_center_item(item)
        all_chunks.extend(chunk_document(doc))

    with open("pipeline/_manual_check_output.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"total chunks: {len(all_chunks)}")


if __name__ == "__main__":
    main()
