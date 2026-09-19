from config import DATA_GO_KR_API_KEY
from collectors.base import fetch_xml

BASE_URL = "https://apis.data.go.kr/B550928/searchLtcInsttService02"

ENDPOINTS = {
    "green_institution": "/getBillGreentInsttSearchList02",  # 청구그린기관 목록 검색
    "institution_list": "/getLtcInsttSeachList02",  # 장기요양기관 검색 목록 조회
}

# 법정동 코드 앞 2자리(시도코드). getLtcInsttSeachList02의 siDoCd 필수 파라미터에 사용.
SIDO_CODES = {
    "서울": "11",
    "부산": "26",
    "대구": "27",
    "인천": "28",
    "광주": "29",
    "대전": "30",
    "울산": "31",
    "세종": "36",
    "경기": "41",
    "충북": "43",
    "충남": "44",
    "전북": "45",
    "전남": "46",
    "경북": "47",
    "경남": "48",
    "제주": "50",
}


def search_green_institutions(page_no: int = 1, num_of_rows: int = 10, **extra) -> dict:
    return fetch_xml(
        BASE_URL,
        ENDPOINTS["green_institution"],
        DATA_GO_KR_API_KEY,
        {"pageNo": page_no, "numOfRows": num_of_rows, **extra},
    )


def search_institutions(si_do_cd: str, page_no: int = 1, num_of_rows: int = 10, **extra) -> dict:
    """지역별·급여종류별·기관명별 장기요양시설 검색.
    si_do_cd(시도코드)는 필수 파라미터 -> SIDO_CODES 참고 (예: 서울 "11").
    extra 예: siGunGuCd(시군구코드), adminPttnCd(기관유형코드), adminNm(기관명) 등."""
    return fetch_xml(
        BASE_URL,
        ENDPOINTS["institution_list"],
        DATA_GO_KR_API_KEY,
        {"siDoCd": si_do_cd, "pageNo": page_no, "numOfRows": num_of_rows, **extra},
    )


if __name__ == "__main__":
    print(search_institutions(si_do_cd=SIDO_CODES["서울"]))
