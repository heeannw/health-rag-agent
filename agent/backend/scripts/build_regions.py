"""'내 지역' 선택 목록(전국 시도·시군구 + 기준 좌표)을 만들어 agent/backend/data/regions.json으로 저장한다.

치매안심센터는 시군구마다 한 곳 이상 있어서, data/facilities.json의 치매안심센터 좌표·주소를
카카오 좌표→행정구역 / 주소 검색 API에 넣어 시군구 이름을 모은다. 이름은 카카오 기준이라 프론트가
현재 위치로 찾는 지역 이름(kakao.js regionFromCoords)과 같다. 기준 좌표는 카카오 주소 검색으로
'시도 시군구'를 찾은 대표 지점이다.

시군구는 '수원시 팔달구'처럼 일반구까지 내려가지 않고 '수원시'까지만 쓴다
(혜택 DB provider_municipality가 시 단위라서).

필요한 키: 루트 .env KAKAO_REST_API_KEY
실행 (agent/backend 폴더에서, collect_facilities.py를 먼저 돌려 facilities.json이 있어야 함):
    python scripts/build_regions.py
"""

import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
FACILITIES = BACKEND_DIR / "data" / "facilities.json"
OUT = BACKEND_DIR / "data" / "regions.json"

load_dotenv(BACKEND_DIR.parents[1] / ".env")  # 저장소 루트 .env
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")


def _kakao(path: str, **params) -> list[dict]:
    resp = requests.get(
        f"https://dapi.kakao.com/v2/local/{path}.json",
        params=params,
        headers={"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"},
        timeout=10,
    )
    resp.raise_for_status()
    time.sleep(0.05)
    return resp.json().get("documents") or []


def _name(area: dict) -> tuple[str, str | None]:
    return area["region_1depth_name"], (area["region_2depth_name"] or "").split(" ")[0] or None


def region_of(lat: float, lng: float) -> tuple[str, str | None] | None:
    docs = _kakao("geo/coord2regioncode", x=lng, y=lat)
    area = next((d for d in docs if d["region_type"] == "H"), docs[0] if docs else None)
    return _name(area) if area else None


def region_of_address(address: str | None) -> tuple[str, str | None] | None:
    """원문 좌표가 시군구 경계 너머로 찍힌 기관이 있어서(예: 광명시 → 금천구) 주소로도 한 번 더 찾는다."""
    # 상세주소('3층' 등)가 붙으면 검색이 안 돼서 '시도 시군구'만 찾는다. 결과 지역명은 '서울'처럼
    # 줄임말이라 좌표만 받아 좌표→행정구역으로 다시 찾는다
    parts = (address or "").split()
    point = center_of(" ".join(parts[:2])) if len(parts) >= 2 else None
    return region_of(*point) if point else None


def center_of(name: str) -> tuple[float, float] | None:
    docs = _kakao("search/address", query=name)
    return (float(docs[0]["y"]), float(docs[0]["x"])) if docs else None


def main():
    if not KAKAO_REST_API_KEY:
        sys.exit("루트 .env에 KAKAO_REST_API_KEY가 필요합니다")
    if not FACILITIES.exists():
        sys.exit(f"{FACILITIES}가 없습니다. scripts/collect_facilities.py를 먼저 실행하세요")

    centers = [f for f in json.loads(FACILITIES.read_text(encoding="utf-8"))
               if f["type"] == "dementia_center"]
    names: set[tuple[str, str | None]] = set()
    for f in centers:
        for found in (f.get("lat") and region_of(f["lat"], f["lng"]), region_of_address(f.get("address"))):
            if found:
                names.add(found)
    # 시도 '전체' 항목도 하나씩 넣는다 (세종처럼 시군구가 없는 곳은 이것만 남는다)
    names |= {(province, None) for province, _ in names}

    regions = []
    for province, municipality in sorted(names, key=lambda n: (n[0], n[1] or "")):
        label = f"{province} {municipality}" if municipality else province
        point = center_of(label)
        if not point:
            print(f"좌표 못 찾음, 건너뜀: {label}")
            continue
        regions.append({"province": province, "municipality": municipality, "lat": point[0], "lng": point[1]})

    OUT.write_text(json.dumps(regions, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"저장: {OUT} (시도 {sum(1 for r in regions if not r['municipality'])}곳, "
          f"시군구 {sum(1 for r in regions if r['municipality'])}곳)")


if __name__ == "__main__":
    main()
