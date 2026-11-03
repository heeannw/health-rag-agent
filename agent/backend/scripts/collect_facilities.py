"""지도 화면용 공공데이터 기관 목록을 모아 agent/backend/data/facilities.json으로 저장한다.

원희 data-rag의 수집기(collectors/)를 그대로 불러 쓰고, 좌표가 없는 기관은 카카오
주소 검색 REST API로 좌표를 붙인다. 백엔드는 이 파일이 있으면 샘플 대신 이걸 쓴다.

필요한 키
- 루트 .env  DATA_GO_KR_API_KEY (data.go.kr 일반 인증키)
- 루트 .env  KAKAO_REST_API_KEY (카카오 앱 키 > REST API 키, 없으면 좌표 변환 생략)

실행 (agent/backend 폴더에서, requests·xmltodict가 설치된 venv):
    python scripts/collect_facilities.py                              # 기본: 서울특별시
    python scripts/collect_facilities.py --provinces 서울특별시 경기도

치매안심센터는 전국(원문에 좌표 있음), 병원·장기요양기관은 --provinces 지역만 좌표를 붙인다.
병원평가 원문은 지역 필터가 안 돼서 전국(약 3.7만 건)을 받은 뒤 주소로 거른다.
장기요양기관 원문에는 주소가 없어서 카카오 키워드 검색(기관명)으로 위치를 찾고,
찾은 주소가 해당 시도가 아니면 버린다.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_RAG_DIR = BACKEND_DIR.parents[1] / "data-rag"
OUT_DIR = BACKEND_DIR / "data"
RAW_DIR = OUT_DIR / "raw"
GEOCODE_CACHE = OUT_DIR / "geocode_cache.json"

sys.path.insert(0, str(DATA_RAG_DIR))
from collectors import dementia_center, hospital, ltc_institution  # noqa: E402

load_dotenv(BACKEND_DIR.parents[1] / ".env")  # 저장소 루트 .env
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")


# 장기요양기관 API의 siDoCd(법정동 시도코드)
PROVINCE_CODES = {
    "서울특별시": "11", "부산광역시": "26", "대구광역시": "27", "인천광역시": "28", "광주광역시": "29",
    "대전광역시": "30", "울산광역시": "31", "세종특별자치시": "36", "경기도": "41", "충청북도": "43",
    "충청남도": "44", "전북특별자치도": "45", "전라남도": "46", "경상북도": "47", "경상남도": "48",
    "제주특별자치도": "50",
}


# 병원평가 asmGrdNN → 평가항목. 출처: OpenAPI활용가이드_건강보험심사평가원(병원평가정보서비스)_20250219.docx
# 값은 1~5등급(1등급이 가장 우수) 또는 '등급제외'. 천식(16)만 등급 없이 양호한 기관을 공개한다.
GRADE_ITEMS = {
    "01": "급성기뇌졸중", "03": "혈액투석", "04": "의료급여정신과", "05": "수술부위 감염예방 항생제",
    "06": "관상동맥우회술", "07": "급성상기도감염 항생제 처방률", "08": "주사제 처방률", "09": "약품목수",
    "10": "요양병원", "12": "대장암", "13": "위암", "14": "유방암", "15": "폐암", "16": "천식",
    "17": "만성폐쇄성폐질환", "18": "폐렴", "19": "중환자실", "20": "신생아중환자실", "21": "마취",
    "22": "정신건강 입원영역", "23": "급성하기도감염 항생제 처방률", "24": "고혈압·당뇨병",
}


def _grades(item: dict) -> list[str]:
    """{'asmGrd24': '1', 'asmGrd07': '등급제외'} → ['고혈압·당뇨병 1등급'] ('등급제외'·빈 값은 뺀다)."""
    grades = []
    for key, value in sorted(item.items()):
        code = key.removeprefix("asmGrd")
        if not key.startswith("asmGrd") or not value or value == "등급제외":
            continue
        label = GRADE_ITEMS.get(code, f"평가항목 {code}")
        grades.append(f"{label} {value}등급" if value.isdigit() else f"{label} {value}")
    return grades


def _items(resp: dict) -> list[dict]:
    """data.go.kr 응답 (response.)body.items(.item) → 항목 리스트. 치매센터 API는 response 감싸기가 없다."""
    items = (resp.get("response", resp).get("body") or {}).get("items") or []
    if isinstance(items, dict):
        items = items.get("item") or []
    return [items] if isinstance(items, dict) else items


def _region(address: str | None) -> tuple[str | None, str | None]:
    """'서울특별시 마포구 …' → ('서울특별시', '마포구'), '경기도 수원시 팔달구 …' → ('경기도', '수원시 팔달구')."""
    parts = (address or "").split()
    if len(parts) < 2:
        return (parts[0] if parts else None), None
    municipality = parts[1]
    if municipality.endswith("시") and len(parts) > 2 and parts[2].endswith("구"):
        municipality = f"{municipality} {parts[2]}"
    return parts[0], municipality


def _float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class Geocoder:
    """카카오 주소 검색. 같은 주소를 다시 부르지 않도록 결과를 파일에 캐시한다."""

    def __init__(self):
        self.cache = json.loads(GEOCODE_CACHE.read_text(encoding="utf-8")) if GEOCODE_CACHE.exists() else {}
        self._calls = 0

    def _search(self, kind: str, query: str) -> list[dict]:
        resp = requests.get(
            f"https://dapi.kakao.com/v2/local/search/{kind}.json",
            params={"query": query},
            headers={"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"},
            timeout=10,
        )
        resp.raise_for_status()
        time.sleep(0.05)
        self._calls += 1
        if self._calls % 500 == 0:  # 중간에 끊겨도 다음 실행이 이어받도록 수시로 저장
            self.save()
        return resp.json().get("documents") or []

    def __call__(self, address: str | None) -> tuple[float | None, float | None]:
        """주소 → (위도, 경도)."""
        if not address or not KAKAO_REST_API_KEY:
            return None, None
        if address not in self.cache:
            docs = self._search("address", address)
            self.cache[address] = [float(docs[0]["y"]), float(docs[0]["x"])] if docs else None
        return tuple(self.cache[address] or (None, None))

    def _district_code(self, lat: str, lng: str) -> str:
        """좌표 → 법정동 코드 앞 5자리(시도 2 + 시군구 3). 예: 서울 노원구 '11350'."""
        key = f"code:{lat},{lng}"
        if key not in self.cache:
            resp = requests.get(
                "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json",
                params={"x": lng, "y": lat},
                headers={"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"},
                timeout=10,
            )
            resp.raise_for_status()
            time.sleep(0.05)
            self._calls += 1
            legal = next((d for d in resp.json().get("documents") or [] if d["region_type"] == "B"), None)
            self.cache[key] = legal["code"][:5] if legal else ""
        return self.cache[key]

    def place(self, name: str | None, district_code: str) -> dict | None:
        """기관명 키워드 검색 → 원문 시군구 코드와 같은 구에 있는 첫 결과 {lat, lng, address, phone}.

        같은 이름의 다른 지역 기관이 잡히지 않도록 결과 좌표의 법정동 코드로 확인한다.
        """
        if not name or not KAKAO_REST_API_KEY:
            return None
        key = f"place:{district_code}:{name}"
        if key not in self.cache:
            hit = next((d for d in self._search("keyword", name)[:5]
                        if self._district_code(d["y"], d["x"]) == district_code), None)
            self.cache[key] = hit and {
                "lat": float(hit["y"]), "lng": float(hit["x"]),
                "address": hit["road_address_name"] or hit["address_name"], "phone": hit["phone"] or None,
            }
        return self.cache[key]

    def save(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        GEOCODE_CACHE.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")


def _save_raw(name: str, items: list[dict]):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{name}.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def _retry(fetch, tries: int = 4, **kwargs) -> dict:
    """data.go.kr는 큰 응답이 중간에 끊기거나 DNS가 잠깐 실패하는 일이 잦아 몇 번 다시 시도한다."""
    for attempt in range(tries):
        try:
            return fetch(**kwargs)
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def _redact(message: str) -> str:
    """오류 메시지 URL에 섞인 serviceKey를 가린다."""
    return re.sub(r"serviceKey=[^&\s']+", "serviceKey=***", message)


def _paged(fetch, rows: int, page_size: int = 500, **params) -> list[dict]:
    items: list[dict] = []
    page = 1
    while len(items) < rows:
        size = min(page_size, rows - len(items))
        batch = _items(_retry(fetch, page_no=page, num_of_rows=size, **params))
        items.extend(batch)
        if len(batch) < size:
            break
        page += 1
    return items


def collect_dementia_centers(geocode: Geocoder) -> list[dict]:
    """전국치매센터표준데이터 — 원문에 위도·경도가 있어 좌표 변환이 거의 필요 없다."""
    items = _paged(dementia_center.search_dementia_centers, rows=2000)
    _save_raw("dementia_center", items)
    result = []
    for it in items:
        address = it.get("rdnmadr") or it.get("lnmadr")
        lat, lng = _float(it.get("latitude")), _float(it.get("longitude"))
        if lat is None:
            lat, lng = geocode(address)
        # insttNm(관리기관 지역, 예: '서울특별시 강서구')이 주소보다 행정구역 표기가 고르다
        province, municipality = _region(it.get("insttNm") or address)
        stats = [
            {"label": label, "value": f"{it[key]}명"}
            for key, label in (("doctrCo", "의사"), ("nurseCo", "간호사"), ("scrcsCo", "사회복지사"))
            if it.get(key) not in (None, "")
        ]
        details = {"운영기관": it.get("operInstitutionNm"), "기타 인력": it.get("etcHnfSttus"),
                   "시설": it.get("etcFclty"), "기준일": it.get("referenceDate")}
        result.append({
            "id": f"dem-{it.get('cnterNm')}-{it.get('institutionNm', '')}",
            "type": "dementia_center",
            "name": it.get("cnterNm"),
            "address": address,
            "phone": it.get("phoneNumber"),
            "lat": lat, "lng": lng,
            "province": province, "municipality": municipality,
            "summary": it.get("cnterSe"),
            # 원문은 '치매조기검진사업+치매치료관리비지원사업+…' 형태
            "services": [{"name": p.strip(), "cost": ""} for p in (it.get("imbcltyIntrcn") or "").split("+") if p.strip()],
            "stats": stats,
            "details": {k: v for k, v in details.items() if v},
            "data_source": "전국치매센터표준데이터",
        })
    return result


def collect_hospitals(geocode: Geocoder, provinces: list[str]) -> list[dict]:
    """건강보험심사평가원 병원평가정보 — 주소만 있어 카카오로 좌표를 붙인다."""
    items = _paged(hospital.search_hospital_assessment, rows=100_000)
    _save_raw("hospital", items)
    result = []
    for it in items:
        address = it.get("addr")
        province, municipality = _region(address)
        if province not in provinces:
            continue
        lat, lng = geocode(address)
        grades = _grades(it)
        result.append({
            "id": f"hosp-{it.get('ykiho') or it.get('yadmNm')}",
            "type": "hospital",
            "name": it.get("yadmNm"),
            "address": address,
            "phone": it.get("telno"),
            "lat": lat, "lng": lng,
            "province": province, "municipality": municipality,
            "summary": it.get("clCdNm"),
            "grades": grades,
            "data_source": "건강보험심사평가원 병원평가정보",
        })
    return result


def collect_ltc_institutions(geocode: Geocoder, provinces: list[str]) -> list[dict]:
    """국민건강보험공단 장기요양기관 검색 — 원문에 주소·전화가 없어 카카오 키워드 검색으로 찾는다."""
    raw: list[dict] = []
    result = []
    for province in provinces:
        items = _paged(ltc_institution.search_institutions, rows=100_000, si_do_cd=PROVINCE_CODES[province])
        raw.extend(items)
        for it in items:
            district_code = f"{it.get('siDoCd', '')}{it.get('siGunGuCd', '')}"
            hit = geocode.place(it.get("adminNm"), district_code) or {}
            address = hit.get("address")
            _, municipality = _region(address)
            details = {"지정일": it.get("stpRptDt"), "위치 출처": "카카오 키워드 검색 (시군구 코드 일치 확인)" if hit else None}
            result.append({
                "id": f"ltc-{it.get('longTermAdminSym') or it.get('adminNm')}",
                "type": "ltc_institution",
                "name": it.get("adminNm"),
                "address": address,
                "phone": hit.get("phone"),
                "lat": hit.get("lat"), "lng": hit.get("lng"),
                "province": province, "municipality": municipality,
                "details": {k: v for k, v in details.items() if v},
                "data_source": "국민건강보험공단 장기요양기관",
            })
    _save_raw("ltc_institution", raw)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provinces", nargs="+", default=["서울특별시"], choices=PROVINCE_CODES,
                        help="병원·장기요양기관을 모을 시도 (치매안심센터는 항상 전국)")
    args = parser.parse_args()

    if not KAKAO_REST_API_KEY:
        print("KAKAO_REST_API_KEY가 없어 주소 → 좌표 변환을 건너뜁니다 (지도 마커가 안 찍힐 수 있음)")
    geocode = Geocoder()
    facilities: list[dict] = []
    try:
        for name, collect in (
            ("치매안심센터", lambda: collect_dementia_centers(geocode)),
            ("병원평가", lambda: collect_hospitals(geocode, args.provinces)),
            ("장기요양기관", lambda: collect_ltc_institutions(geocode, args.provinces)),
        ):
            try:
                found = collect()
            except Exception as e:  # 한 데이터셋이 실패해도 나머지는 저장
                print(f"{name}: 실패 ({type(e).__name__}: {_redact(str(e))})")
                continue
            with_coords = sum(1 for f in found if f["lat"] is not None)
            print(f"{name}: {len(found)}곳 (좌표 {with_coords}곳)")
            facilities.extend(found)
    finally:
        geocode.save()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "facilities.json"
    out.write_text(json.dumps(facilities, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"저장: {out} ({len(facilities)}곳)")


if __name__ == "__main__":
    main()
