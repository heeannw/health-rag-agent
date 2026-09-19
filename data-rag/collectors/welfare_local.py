from config import DATA_GO_KR_API_KEY
from collectors.base import fetch_xml

BASE_URL = "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations"

ENDPOINTS = {
    "list": "/LcgvWelfarelist",  # 지자체복지서비스 목록조회
    "detail": "/LcgvWelfaredetailed",  # 지자체복지서비스 상세조회
}


def search_welfare_list(page_no: int = 1, num_of_rows: int = 10, **extra) -> dict:
    return fetch_xml(
        BASE_URL,
        ENDPOINTS["list"],
        DATA_GO_KR_API_KEY,
        {"pageNo": page_no, "numOfRows": num_of_rows, **extra},
    )


def get_welfare_detail(service_id: str, **extra) -> dict:
    """service_id: 목록조회 결과의 서비스ID(servId)."""
    return fetch_xml(
        BASE_URL,
        ENDPOINTS["detail"],
        DATA_GO_KR_API_KEY,
        {"servId": service_id, **extra},
    )


if __name__ == "__main__":
    print(search_welfare_list())
