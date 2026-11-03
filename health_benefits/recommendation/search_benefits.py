"""의료 혜택을 분류로 추출합니다. NULL은 보존하고 미확인 후보를 분리합니다."""
import argparse
import json
import os
from pathlib import Path

from health_benefits.paths import BASE
UNKNOWN_LABEL = "대상 원문 확인"
# 원문에 명시된 값만 전체 대상으로 인정합니다.
ALL_AUDIENCES = {"전체", "전체 대상"}


def labels(value):
    return [v.strip() for v in (value or []) if v and v.strip()]


def audience_match(value, selected):
    if not selected:
        return "match"
    known = labels(value)
    if not known:
        return "unknown"
    return "match" if set(known) & (set(selected) | ALL_AUDIENCES) else "mismatch"


def region_info(row):
    province = (row.get("provider_province") or "").strip()
    municipality = (row.get("provider_municipality") or "").strip()
    if province == "전국" and municipality in ("", "전국"):
        return "nationwide", "전국"
    if not province or province == "전국":
        return "unknown", UNKNOWN_LABEL
    return "regional", " ".join(v for v in (province, municipality) if v)


def region_match(row, province=None, municipality=None):
    if not province:
        return "match"
    scope, _ = region_info(row)
    if scope == "unknown":
        return "unknown"
    if scope == "nationwide":
        return "match"
    if province != (row.get("provider_province") or "").strip():
        return "mismatch"
    if not municipality:
        return "match"
    local = (row.get("provider_municipality") or "").strip()
    if not local:
        return "unknown"
    return "match" if local == municipality else "mismatch"


def extract_benefits(rows, life_cycles=None, target_groups=None,
                     province=None, municipality=None):
    """같은 분류 내 OR, 분류 간 AND. 알려진 불일치는 제외합니다."""
    if municipality and not province:
        raise ValueError("시군구를 선택하려면 시도를 함께 입력하세요.")
    result = {"matched": [], "needs_review": []}
    for row in rows:
        states = {
            "life_cycle_names": audience_match(row.get("life_cycle_names"), life_cycles),
            "target_group_names": audience_match(row.get("target_group_names"), target_groups),
            "region": region_match(row, province, municipality),
        }
        if "mismatch" in states.values():
            continue
        scope, region_label = region_info(row)
        item = dict(row)  # 원본 NULL과 배열을 변경하지 않습니다.
        item["display"] = {
            "life_cycle": ", ".join(labels(row.get("life_cycle_names"))) or UNKNOWN_LABEL,
            "target_group": ", ".join(labels(row.get("target_group_names"))) or UNKNOWN_LABEL,
            "region": region_label,
        }
        item["region_scope"] = scope
        item["filter_status"] = states
        item["review_fields"] = [k for k, v in states.items() if v == "unknown"]
        bucket = "needs_review" if item["review_fields"] else "matched"
        result[bucket].append(item)
    return result


def load_database():
    import psycopg
    from dotenv import load_dotenv

    load_dotenv(BASE / ".env")
    with psycopg.connect(
        host=os.environ["PGHOST"], port=os.environ["PGPORT"],
        dbname=os.environ["PGDATABASE"], user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"], sslmode="require", connect_timeout=15,
    ) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        return [r[0] for r in conn.execute(
            "SELECT row_to_json(b) FROM public.healty_benefit b ORDER BY id"
        )]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--life-cycle", action="append", help="생애주기 원문 분류명; 반복 가능")
    parser.add_argument("--target-group", action="append", help="대상특성 원문 분류명; 반복 가능")
    parser.add_argument("--province", help="시도 원문명 또는 전국; 생략하면 지역 필터 없음")
    parser.add_argument("--municipality", help="시군구 원문명")
    parser.add_argument("--input", type=Path, help="DB 대신 의료 혜택 행 배열 JSON 읽기")
    parser.add_argument("--output", type=Path, default=BASE / "data/exports/filtered_benefits.json")
    args = parser.parse_args()
    if args.municipality and not args.province:
        parser.error("--municipality는 --province와 함께 사용하세요.")
    rows = json.loads(args.input.read_text(encoding="utf-8-sig")) if args.input else load_database()
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("입력 JSON은 의료 혜택 객체의 배열이어야 합니다.")
    result = extract_benefits(rows, args.life_cycle, args.target_group,
                              args.province, args.municipality)
    result["filters"] = {"life_cycles": args.life_cycle, "target_groups": args.target_group,
                         "province": args.province, "municipality": args.municipality}
    result["notice"] = "분류 일치 후보이며 수급 자격 확정이 아닙니다. 제공기관 지역과 실제 거주 요건은 다를 수 있으므로 대상·선정기준 원문을 확인하세요."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"분류 일치 {len(result['matched'])}건 / 원문 확인 {len(result['needs_review'])}건")
    print(f"저장: {args.output.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc) if isinstance(exc, ValueError) else f"추출 실패: {type(exc).__name__}")
        raise SystemExit(1) from None
