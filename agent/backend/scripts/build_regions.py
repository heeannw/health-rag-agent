"""facilities.json의 치매안심센터 위치로 전국 시도·시군구(시 단위)와 기준 좌표를 모아 data/regions.json으로 저장.
실행(agent/backend, 키: KAKAO_REST_API_KEY): python scripts/build_regions.py"""

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
    """주소 앞 '시도 시군구'로 지역 찾기 (좌표가 경계 너머로 찍힌 기관 보정)."""
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
    # 시도 '전체' 항목도 넣는다
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
