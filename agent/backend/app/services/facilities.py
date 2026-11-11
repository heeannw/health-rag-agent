"""data/facilities.json(기관)과 data/regions.json(지역)을 서버 시작 때 한 번 읽는다.
파일이 없으면 빈 목록. 다시 만들면 백엔드를 재시작해야 한다."""

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
