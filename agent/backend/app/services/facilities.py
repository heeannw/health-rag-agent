"""지도 화면 기관 목록과 '내 지역' 선택 목록.

- data/facilities.json  scripts/collect_facilities.py가 만든 공공데이터 기관
- data/regions.json     scripts/build_regions.py가 만든 전국 시도·시군구와 기준 좌표

파일이 없으면 빈 목록을 돌려주고 경고만 남긴다. 서버 시작 때 한 번 읽으므로
파일을 새로 만들면 백엔드를 다시 켜야 한다.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _load(name: str, script: str) -> list[dict]:
    path = DATA_DIR / name
    if not path.exists():
        logger.warning("%s가 없습니다. scripts/%s를 실행하세요", path, script)
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("%s 읽기 실패", path)
        return []


FACILITIES = _load("facilities.json", "collect_facilities.py")
REGIONS = _load("regions.json", "build_regions.py")
