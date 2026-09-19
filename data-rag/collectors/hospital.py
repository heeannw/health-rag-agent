from config import DATA_GO_KR_API_KEY
from collectors.base import fetch_xml

BASE_URL = "https://apis.data.go.kr/B551182/hospAsmInfoService1"
PATH = "/getHospAsmInfo1"


def search_hospital_assessment(page_no: int = 1, num_of_rows: int = 10, **extra) -> dict:
    """병원평가상세등급조회. extra 예: dsymCd(질환코드), sidoCd(시도코드) 등."""
    return fetch_xml(
        BASE_URL,
        PATH,
        DATA_GO_KR_API_KEY,
        {"pageNo": page_no, "numOfRows": num_of_rows, **extra},
    )


if __name__ == "__main__":
    print(search_hospital_assessment())
