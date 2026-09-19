from config import DATA_GO_KR_API_KEY
from collectors.base import fetch_json

BASE_URL = "https://api.data.go.kr/openapi/tn_pubr_public_imbclty_cnter_api"
PATH = ""


def search_dementia_centers(page_no: int = 1, num_of_rows: int = 10, **extra) -> dict:
    return fetch_json(
        BASE_URL,
        PATH,
        DATA_GO_KR_API_KEY,
        {"pageNo": page_no, "numOfRows": num_of_rows, "type": "json", **extra},
    )


if __name__ == "__main__":
    print(search_dementia_centers())
