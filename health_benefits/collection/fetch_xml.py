import os
from health_benefits.paths import BASE

from dotenv import load_dotenv

import requests
from defusedxml import ElementTree as ET


BASE_URL = (
    "https://apis.data.go.kr/B554287/"
    "NationalWelfareInformationsV001"
)

# 실행 위치와 관계없이 health_benefits 아래에 data 폴더를 만듭니다.
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)

load_dotenv(
    dotenv_path=BASE / ".env",
    override=True,
)

SERVICE_KEY = os.environ.get("DATA_GO_KR_SERVICE_KEY")

if not SERVICE_KEY:
    raise SystemExit("먼저 인증키 환경변수를 설정해주세요.")


def text_of(root, tag):
    node = root.find(f".//{tag}")
    if node is None:
        return None
    return "".join(node.itertext()).strip() or None


def download_xml(operation, params, filename):
    try:
        response = requests.get(
            f"{BASE_URL}/{operation}",
            params={
                "serviceKey": SERVICE_KEY,
                **params,
            },
            timeout=30,
        )
    except requests.RequestException:
        # 요청 URL에는 인증키가 들어가므로 예외 전체를 출력하지 않습니다.
        raise RuntimeError("API 연결에 실패했습니다.") from None

    if response.status_code != 200:
        raise RuntimeError(f"HTTP 오류: {response.status_code}")

    # 받은 원본을 파일로 저장합니다.
    output_path = DATA_DIR / filename
    output_path.write_bytes(response.content)
    print("응답 파일 저장:", output_path)

    try:
        root = ET.fromstring(response.content)
    except Exception:
        raise RuntimeError(
            "응답이 정상 XML인지 저장된 파일을 확인해주세요."
        ) from None

    # 네임스페이스가 있어도 태그명으로 검색할 수 있게 처리합니다.
    for element in root.iter():
        if isinstance(element.tag, str):
            element.tag = element.tag.rsplit("}", 1)[-1]

    # HTTP 200이어도 XML 안에 API 오류가 들어 있을 수 있습니다.
    portal_error = text_of(root, "returnReasonCode")
    if portal_error:
        raise RuntimeError(
            f"공공데이터포털 오류 코드: {portal_error}"
        )

    result_code = text_of(root, "resultCode")
    if result_code is not None and result_code != "0":
        raise RuntimeError(f"API 오류 코드: {result_code}")

    return root


# 1. 복지서비스 목록 1건을 받습니다.
list_root = download_xml(
    operation="NationalWelfarelistV001",
    params={
        "callTp": "L",
        "pageNo": 1,
        "numOfRows": 1,
        "srchKeyCode": "001",
    },
    filename="welfare_list.xml",
)

service = list_root.find(".//servList")

if service is None:
    raise RuntimeError(
        "목록에 서비스가 없습니다. welfare_list.xml을 확인해주세요."
    )

service_id = text_of(service, "servId")

if not service_id:
    raise RuntimeError("서비스 ID가 없습니다.")

print("조회할 서비스 ID:", service_id)


# 2. 목록에서 얻은 ID로 상세정보를 받습니다.
detail_root = download_xml(
    operation="NationalWelfaredetailedV001",
    params={
        "callTp": "D",
        "servId": service_id,
    },
    filename="welfare_detail.xml",
)

if text_of(detail_root, "servId") != service_id:
    raise RuntimeError("상세 응답의 서비스 ID가 일치하지 않습니다.")

name = text_of(detail_root, "servNm")
if not name:
    raise RuntimeError("상세 응답에 서비스명이 없습니다.")

print("\n서비스명:", name)
print("\n지원대상:", text_of(detail_root, "tgtrDtlCn"))
print("\n선정기준:", text_of(detail_root, "slctCritCn"))
print("\n지원내용:", text_of(detail_root, "alwServCn"))