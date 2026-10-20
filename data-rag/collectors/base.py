from urllib.parse import unquote, urlencode

import requests
import xmltodict


def fetch_xml(base_url: str, path: str, service_key: str, params: dict) -> dict:
    """apis.data.go.kr류 REST API(XML 응답) 공통 호출.

    service_key는 포털에서 이미 URL-encoding된 값으로 내려주므로,
    requests의 params가 아니라 쿼리스트링에 직접 이어붙여 이중 인코딩을 피한다.
    """
    query = urlencode(params)
    url = f"{base_url}{path}?serviceKey={service_key}"
    if query:
        url = f"{url}&{query}"

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return xmltodict.parse(resp.content)


def fetch_json(base_url: str, path: str, service_key: str, params: dict) -> dict:
    """api.data.go.kr류 REST API(JSON 응답) 공통 호출. serviceKey는 쿼리 파라미터로 전달."""
    query = urlencode(params)
    url = f"{base_url}{path}?serviceKey={service_key}"
    if query:
        url = f"{url}&{query}"

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_odcloud(base_url: str, path: str, service_key: str, params: dict) -> dict:
    """odcloud(api.odcloud.kr)류 REST API 공통 호출. serviceKey를 디코딩해 Authorization 헤더로 전달."""
    headers = {"Authorization": f"Infuser {unquote(service_key)}"}
    resp = requests.get(f"{base_url}{path}", params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()
