from config import DATA_GO_KR_API_KEY
from collectors.base import fetch_odcloud

BASE_URL = "https://api.odcloud.kr/api"

# 연도별 데이터셋(uddi)이 나뉘어 있음. 필요한 연도가 늘어나면 여기에 추가.
DATASETS = {
    2025: "15009571/v1/uddi:226d2e29-5383-42a0-9004-ca6b5a26834e",
    2024: "15009571/v1/uddi:b5b43942-8390-408b-858c-d57c4783aabd",
    2023: "15009571/v1/uddi:22c87f39-f22e-4280-82af-b231f5a15707",
    2022: "15009571/v1/uddi:ad7e925e-0bdd-4ba8-b7a2-ff3c6052ce81",
    2021: "15009571/v1/uddi:b7f8f5e7-89d5-42c8-ab65-aa0edd5b1799",
    2020: "15009571/v1/uddi:ea259b03-7620-47b2-9b08-e9713c6adef6",
}


def search_welfare_payment(year: int = 2025, page: int = 1, per_page: int = 10) -> dict:
    return fetch_odcloud(
        BASE_URL,
        f"/{DATASETS[year]}",
        DATA_GO_KR_API_KEY,
        {"page": page, "perPage": per_page},
    )


if __name__ == "__main__":
    print(search_welfare_payment())
