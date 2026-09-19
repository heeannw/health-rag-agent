from config import DATA_GO_KR_API_KEY
from collectors.base import fetch_xml

BASE_URL = "https://apis.data.go.kr/1170000/law"

ENDPOINTS = {
    "law_list": "/lawSearchList.do",  # 법령정보 목록 조회
    "admrul_list": "/admrulSearchList.do",  # 행정규칙정보 목록 조회
    "ordin_list": "/ordinSearchList.do",  # 자치법규정보 목록 조회
    "expc_list": "/expcSearchList.do",  # 법령해석례정보 목록 조회
    "detc_list": "/detcSearchList.do",  # 헌재결정례정보 목록 조회
    "licbyl_list": "/licbylSearchList.do",  # 별표서식정보 목록 조회
    "lstrm_list": "/lstrmSearchList.do",  # 법령용어정보 목록 조회
    "trty_list": "/trtySearchList.do",  # 조약정보 목록 조회
}


def search_law(query: str, page_no: int = 1, num_of_rows: int = 10) -> dict:
    """법령정보 목록 조회. query: 법령명 검색어 (예: "국민건강보험법")"""
    return fetch_xml(
        BASE_URL,
        ENDPOINTS["law_list"],
        DATA_GO_KR_API_KEY,
        {
            "target": "law",
            "query": query,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        },
    )


if __name__ == "__main__":
    result = search_law("국민건강보험법")
    print(result)
