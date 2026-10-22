import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone

import psycopg
import requests
from defusedxml import ElementTree as ET
from dotenv import load_dotenv
from health_benefits.database.benefit_store import save_listing, save_detail

from health_benefits.paths import BASE
URL = "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/"
LOCAL_URL = "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations/"


class StopCollection(Exception):
    pass


def text_of(root, tag):
    node = root.find(f".//{tag}")
    return ("".join(node.itertext()).strip() or None) if node is not None else None


def parse_xml(content):
    root = ET.fromstring(content)
    for node in root.iter():
        if isinstance(node.tag, str):
            node.tag = node.tag.rsplit("}", 1)[-1]
    code = text_of(root, "returnReasonCode") or text_of(root, "resultCode")
    if code is not None and code not in ("0", "00"):
        # 인증/한도 오류일 수 있으므로 이후 호출을 멈춥니다.
        raise StopCollection(f"API 결과코드 {code}: 저장된 XML을 확인하세요.")
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("central", "local"), default="central")
    parser.add_argument("--limit", type=int, default=10, help="상세조회 시도 수, 0은 전체")
    parser.add_argument("--max-calls", type=int, default=80, help="이번 실행의 최대 API 호출 수")
    parser.add_argument("--refresh", action="store_true", help="DB에 있는 서비스도 다시 수집")
    parser.add_argument("--skip-collected-today", action="store_true",
                        help="한국 시간 오늘 수집한 서비스는 재호출하지 않음")
    args = parser.parse_args()
    local = args.source == "local"
    base_url = LOCAL_URL if local else URL
    list_operation = "LcgvWelfarelist" if local else "NationalWelfarelistV001"
    detail_operation = "LcgvWelfaredetailed" if local else "NationalWelfaredetailedV001"
    if args.limit < 0 or args.max_calls < 1:
        parser.error("limit은 0 이상, max-calls는 1 이상이어야 합니다.")

    load_dotenv(BASE / ".env", override=True)
    required = ["DATA_GO_KR_SERVICE_KEY", "PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise StopCollection(".env에 필요한 항목: " + ", ".join(missing))

    run_dir = BASE / "data" / "batches" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir.mkdir(parents=True)
    calls = saved = failed = attempted = skipped = 0

    def log(**record):
        with (run_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def fetch(session, operation, params, filename):
        nonlocal calls
        if calls >= args.max_calls:
            raise StopCollection("이번 실행의 호출 상한에 도달했습니다. 전체 수집 완료는 아닙니다.")
        calls += 1
        time.sleep(0.5)
        try:
            response = session.get(base_url + operation, params={
                "serviceKey": os.environ["DATA_GO_KR_SERVICE_KEY"], **params
            }, timeout=30)
        except requests.RequestException:
            raise RuntimeError("네트워크 연결 실패") from None
        (run_dir / filename).write_bytes(response.content)
        if response.status_code != 200:
            log(source=args.source, status="http_error", http_status=response.status_code,
                response_file=filename, retry_after=response.headers.get("Retry-After"))
            raise StopCollection(f"HTTP {response.status_code}: 호출을 중단합니다.")
        return parse_xml(response.content)

    try:
        with psycopg.connect(host=os.environ["PGHOST"], port=os.environ["PGPORT"],
                             dbname=os.environ["PGDATABASE"], user=os.environ["PGUSER"],
                             password=os.environ["PGPASSWORD"], connect_timeout=10,
                             autocommit=True) as conn, requests.Session() as session:
            existing = {row[0] for row in conn.execute(
                "SELECT source_service_id FROM benefit WHERE source = %s AND detail_collected_at IS NOT NULL", (args.source,)
            )}
            today_ids = {row[0] for row in conn.execute(
                """SELECT source_service_id FROM benefit WHERE source = %s
                   AND (detail_collected_at AT TIME ZONE 'Asia/Seoul')::date =
                       (NOW() AT TIME ZONE 'Asia/Seoul')::date""", (args.source,)
            )} if args.skip_collected_today else set()
            seen = set()
            page = 1
            while True:
                listing = fetch(session, list_operation, {
                    **({} if local else {"callTp": "L"}),
                    "pageNo": page, "numOfRows": 100, "srchKeyCode": "001"
                }, f"list_{page}.xml")
                total_text = text_of(listing, "totalCount")
                if total_text is None or not total_text.isdigit():
                    raise StopCollection("목록 totalCount가 올바르지 않습니다.")
                total = int(total_text)
                services = listing.findall(".//servList")
                if not services and total:
                    raise StopCollection("전체 건수와 달리 빈 페이지가 반환되었습니다.")
                print(f"목록 {page}페이지 / API 전체 {total}건", flush=True)
                new_ids = 0
                for service in services:
                    sid = text_of(service, "servId")
                    if not sid:
                        raise StopCollection("서비스 ID가 없는 목록 항목이 있습니다.")
                    if sid in seen:
                        continue
                    seen.add(sid)
                    new_ids += 1
                    if sid in today_ids or (sid in existing and not args.refresh):
                        skipped += 1
                        continue
                    if args.limit and attempted >= args.limit:
                        raise StopCollection("설정한 상세조회 시도 수에 도달했습니다.")
                    attempted += 1
                    try:
                        filename = "detail_" + hashlib.sha256(sid.encode()).hexdigest() + ".xml"
                        detail = fetch(session, detail_operation, {
                            **({} if local else {"callTp": "D"}), "servId": sid
                        }, filename)
                        name = text_of(detail, "servNm")
                        if text_of(detail, "servId") != sid or not name:
                            raise ValueError("상세 ID 또는 이름 오류")
                        # 원본 XML은 배치 파일에 보존하고 목록/상세는 한 행에 저장합니다.
                        with conn.transaction():
                            save_listing(conn, args.source, service)
                            save_detail(conn, args.source, detail)
                        saved += 1
                        log(source=args.source, service_id=sid, status="saved")
                        print(f"저장 {saved}: {name}", flush=True)
                    except StopCollection:
                        raise
                    except psycopg.Error:
                        log(service_id=sid, status="database_error")
                        raise StopCollection("DB 저장 오류입니다. 접속정보와 테이블을 확인하세요.") from None
                    except Exception as exc:
                        failed += 1
                        # 예외 원문에는 요청 URL 등이 포함될 수 있어 유형만 기록합니다.
                        log(service_id=sid, status="failed", error_type=type(exc).__name__)
                        print(f"실패 {sid}: {type(exc).__name__}", flush=True)
                if page * 100 >= total:
                    print("목록의 마지막 페이지까지 확인했습니다.")
                    break
                if new_ids == 0:
                    raise StopCollection("같은 목록 페이지가 반복되어 중단합니다.")
                page += 1
    except StopCollection as exc:
        print(str(exc))
        log(status="stopped", reason=str(exc))
    except psycopg.Error:
        print("DB 연결 또는 테이블 조회 오류입니다. .env와 benefit 테이블을 확인하세요.")
        log(status="database_error")
    except Exception as exc:
        print(f"수집 중단: {type(exc).__name__}. 저장된 응답을 확인하세요.")
        log(status="error", error_type=type(exc).__name__)
    finally:
        log(source=args.source, status="summary", saved=saved, failed=failed,
            skipped=skipped, calls=calls)
        print(f"저장 {saved} / 실패 {failed} / 기존 건너뜀 {skipped} / API 호출 {calls}")
        print(f"XML과 실행 기록: {run_dir}")


if __name__ == "__main__":
    try:
        main()
    except StopCollection as exc:
        raise SystemExit(str(exc)) from None
