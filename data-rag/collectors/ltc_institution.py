from config import DATA_GO_KR_API_KEY
from collectors.base import fetch_xml

BASE_URL = "https://apis.data.go.kr/B550928/searchLtcInsttService02"

ENDPOINTS = {
    "green_institution": "/getBillGreentInsttSearchList02",  # 청구그린기관 목록 검색
    "institution_list": "/getLtcInsttSeachList02",  # 장기요양기관 검색 목록 조회
}


def search_green_institutions(page_no: int = 1, num_of_rows: int = 10, **extra) -> dict:
    return fetch_xml(
        BASE_URL,
        ENDPOINTS["green_institution"],
        DATA_GO_KR_API_KEY,
        {"pageNo": page_no, "numOfRows": num_of_rows, **extra},
    )


def search_institutions(page_no: int = 1, num_of_rows: int = 10, **extra) -> dict:
    """지역별·급여종류별·기관명별 장기요양시설 검색.
    extra 예: siGunGuCd(시군구코드), stCd(급여종류코드) 등 (미지정시 빈 목록 반환될 수 있음)."""
    return fetch_xml(
        BASE_URL,
        ENDPOINTS["institution_list"],
        DATA_GO_KR_API_KEY,
        {"pageNo": page_no, "numOfRows": num_of_rows, **extra},
    )


if __name__ == "__main__":
    print(search_green_institutions())
