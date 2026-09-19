"""공공데이터 API에서 문서를 수집 -> 정규화 -> 청킹 -> 임베딩 -> Chroma 적재까지 실행하는 스크립트.

사용법: python -m pipeline.build_index

주의: 한국사회보장정보원_중앙부처복지서비스는 개발계정 일일 트래픽이 100건으로
매우 낮음 (목록조회 1건 + 상세조회 N건이 모두 트래픽에 포함). 그래서 이 소스만
CENTRAL_WELFARE_LIMIT을 보수적으로 제한한다. 나머지 소스는 일일 트래픽이
1,000~10,000건이라 여유 있게 가져온다.
"""

import sys

sys.path.insert(0, ".")

from collectors import welfare_central, welfare_local, law, hospital, dementia_center, ltc_institution, welfare_payment
from pipeline.normalize import (
    normalize_welfare_central_detail,
    normalize_welfare_local_detail,
    normalize_law_item,
    normalize_hospital_item,
    normalize_dementia_center_item,
    normalize_ltc_institution_item,
    normalize_ltc_institution_search_item,
    normalize_welfare_payment_item,
)
from pipeline.chunk import chunk_document
from pipeline.embed import embed_texts
from pipeline.vectorstore import add_chunks

# 일일 트래픽이 100건뿐이라 목록조회(1) + 상세조회(N)로 최대 N+1건을 쓴다.
CENTRAL_WELFARE_LIMIT = 30
LOCAL_WELFARE_LIMIT = 150
HOSPITAL_LIMIT = 200
DEMENTIA_LIMIT = 200
LTC_LIMIT = 200
WELFARE_PAYMENT_YEAR = 2025
WELFARE_PAYMENT_LIMIT = 100
LTC_SEARCH_ROWS_PER_REGION = 20

# 프로젝트 주제(건강정보/의료혜택/법제도)와 관련된 법령명으로 목록조회 검색
LAW_QUERIES = [
    "국민건강보험법",
    "노인복지법",
    "치매관리법",
    "장애인복지법",
    "의료급여법",
    "국민연금법",
    "국민기초생활 보장법",
    "노인장기요양보험법",
    "정신건강복지법",
    "사회보장기본법",
    "저출산고령사회기본법",
    "응급의료에 관한 법률",
]
LAW_ROWS_PER_QUERY = 10


def _as_list(node):
    return [node] if isinstance(node, dict) else (node or [])


def collect_welfare_central() -> list[dict]:
    docs = []
    lst = welfare_central.search_welfare_list(num_of_rows=CENTRAL_WELFARE_LIMIT)
    items = _as_list(lst["wantedList"].get("servList"))
    for item in items:
        detail = welfare_central.get_welfare_detail(item["servId"])
        docs.append(normalize_welfare_central_detail(detail))
    return docs


def collect_welfare_local() -> list[dict]:
    docs = []
    lst = welfare_local.search_welfare_list(num_of_rows=LOCAL_WELFARE_LIMIT)
    items = _as_list(lst["wantedList"].get("servList"))
    for item in items:
        detail = welfare_local.get_welfare_detail(item["servId"])
        docs.append(normalize_welfare_local_detail(detail))
    return docs


def collect_law() -> list[dict]:
    docs = []
    seen_ids = set()
    for query in LAW_QUERIES:
        lst = law.search_law(query, num_of_rows=LAW_ROWS_PER_QUERY)
        for item in _as_list(lst["LawSearch"].get("law")):
            law_id = item.get("법령ID")
            if law_id in seen_ids:
                continue
            seen_ids.add(law_id)
            docs.append(normalize_law_item(item))
    return docs


def collect_hospital() -> list[dict]:
    resp = hospital.search_hospital_assessment(num_of_rows=HOSPITAL_LIMIT)
    items = _as_list(resp["response"]["body"]["items"].get("item"))
    return [normalize_hospital_item(item) for item in items]


def collect_dementia_center() -> list[dict]:
    resp = dementia_center.search_dementia_centers(num_of_rows=DEMENTIA_LIMIT)
    items = _as_list(resp["body"]["items"].get("item"))
    return [normalize_dementia_center_item(item) for item in items]


def collect_ltc_institution() -> list[dict]:
    resp = ltc_institution.search_green_institutions(num_of_rows=LTC_LIMIT)
    items = _as_list(resp["response"]["body"]["items"].get("item"))
    return [normalize_ltc_institution_item(item) for item in items]


def collect_welfare_payment() -> list[dict]:
    resp = welfare_payment.search_welfare_payment(year=WELFARE_PAYMENT_YEAR, per_page=WELFARE_PAYMENT_LIMIT)
    return [normalize_welfare_payment_item(row, WELFARE_PAYMENT_YEAR) for row in resp.get("data", [])]


def collect_ltc_institution_search() -> list[dict]:
    docs = []
    for region_name, si_do_cd in ltc_institution.SIDO_CODES.items():
        resp = ltc_institution.search_institutions(si_do_cd=si_do_cd, num_of_rows=LTC_SEARCH_ROWS_PER_REGION)
        items_node = resp["response"]["body"].get("items") or {}
        items = _as_list(items_node.get("item"))
        docs.extend(normalize_ltc_institution_search_item(item) for item in items)
    return docs


COLLECTORS = {
    "welfare_central": collect_welfare_central,
    "welfare_local": collect_welfare_local,
    "law": collect_law,
    "hospital": collect_hospital,
    "dementia_center": collect_dementia_center,
    "ltc_institution": collect_ltc_institution,
    "ltc_institution_search": collect_ltc_institution_search,
    "welfare_payment": collect_welfare_payment,
}


def build() -> int:
    all_chunks = []
    for name, collect_fn in COLLECTORS.items():
        docs = collect_fn()
        print(f"[{name}] 문서 {len(docs)}건 수집")
        chunks = []
        for doc in docs:
            chunks.extend(chunk_document(doc))
        print(f"[{name}] 청크 {len(chunks)}건 생성")
        all_chunks.extend(chunks)

    dedup: dict[str, dict] = {}
    for chunk in all_chunks:
        dedup[chunk["chunk_id"]] = chunk
    all_chunks = list(dedup.values())

    print(f"총 청크 수: {len(all_chunks)} (중복 제거 후)")
    if not all_chunks:
        return 0

    batch_size = 64
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        embeddings = embed_texts([c["text"] for c in batch])
        add_chunks(batch, embeddings)
        print(f"적재 진행: {min(i + batch_size, len(all_chunks))}/{len(all_chunks)}")

    print(f"Chroma 적재 완료: 총 {len(all_chunks)}개 청크")
    return len(all_chunks)


if __name__ == "__main__":
    build()
