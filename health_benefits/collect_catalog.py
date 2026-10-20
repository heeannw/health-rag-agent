"""공식 전체 목록을 benefit에 저장합니다. 상세 컬럼과 상세 수집 시각은 유지합니다."""
import argparse
import json
import os
import time
from datetime import datetime, timezone

import psycopg
import requests
from dotenv import load_dotenv

from collect_many import BASE, URL, LOCAL_URL, parse_xml, text_of
from benefit_store import save_listing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("central", "local"), required=True)
    args = parser.parse_args()
    load_dotenv(BASE / ".env", override=True)
    local = args.source == "local"
    endpoint = (LOCAL_URL + "LcgvWelfarelist" if local else URL + "NationalWelfarelistV001")
    run_dir = BASE / "data" / "batches" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_catalog_" + args.source)
    run_dir.mkdir(parents=True)
    seen = set()
    with psycopg.connect(host=os.environ["PGHOST"], port=os.environ["PGPORT"],
                         dbname=os.environ["PGDATABASE"], user=os.environ["PGUSER"],
                         password=os.environ["PGPASSWORD"], connect_timeout=10,
                         autocommit=True) as conn, requests.Session() as session:
        # 기관의 시도/시군구는 대상자의 거주 요건과 구분합니다.
        page = 1
        while True:
            time.sleep(0.5)
            response = session.get(endpoint, params={
                "serviceKey": os.environ["DATA_GO_KR_SERVICE_KEY"],
                **({} if local else {"callTp": "L"}),
                "pageNo": page, "numOfRows": 100, "srchKeyCode": "001"
            }, timeout=30)
            (run_dir / f"list_{page}.xml").write_bytes(response.content)
            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}, 응답: {run_dir}")
            root = parse_xml(response.content)
            total = int(text_of(root, "totalCount"))
            services = root.findall(".//servList")
            if not services and total:
                raise RuntimeError("빈 목록 응답")
            previous = len(seen)
            with conn.transaction():
                for service in services:
                    sid, name = text_of(service, "servId"), text_of(service, "servNm")
                    if not sid or not name:
                        raise ValueError("목록 ID/이름 누락")
                    if sid in seen:
                        continue
                    seen.add(sid)
                    save_listing(conn, args.source, service)
            print(f"{args.source} 목록 저장 {len(seen)}/{total} ({page}페이지)", flush=True)
            if len(seen) >= total:
                break
            if len(seen) == previous:
                raise RuntimeError("반복 페이지 감지")
            page += 1
        report = {"source": args.source, "saved": len(seen), "api_total": total,
                  "pages": page, "complete": len(seen) == total}
        (run_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # 요청 URL/DB 접속정보가 포함된 예외 원문을 출력하지 않습니다.
        raise SystemExit(f"카탈로그 수집 실패: {type(exc).__name__}") from None
