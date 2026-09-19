from config import DATA_GO_KR_API_KEY
from collectors.base import fetch_xml

BASE_URL = "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001"

ENDPOINTS = {
    "list": "/NationalWelfarelistV001",  # 복지서비스 목록조회
    "detail": "/NationalWelfaredetailedV001",  # 복지서비스 상세조회
}


def search_welfare_list(srch_key_code: str = "001", page_no: int = 1, num_of_rows: int = 10, **extra) -> dict:
    """중앙부처 복지서비스 목록조회. srchKeyCode는 필수 파라미터(검색조건 코드)."""
    return fetch_xml(
        BASE_URL,
        ENDPOINTS["list"],
        DATA_GO_KR_API_KEY,
        {"srchKeyCode": srch_key_code, "pageNo": page_no, "numOfRows": num_of_rows, **extra},
    )


def get_welfare_detail(service_id: str, **extra) -> dict:
    """복지서비스 상세조회. service_id: 목록조회 결과의 서비스ID(servId)."""
    return fetch_xml(
        BASE_URL,
        ENDPOINTS["detail"],
        DATA_GO_KR_API_KEY,
        {"servId": service_id, **extra},
    )


if __name__ == "__main__":
    print(search_welfare_list())
