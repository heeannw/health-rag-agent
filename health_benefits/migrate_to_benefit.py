"""기존 네 테이블을 백업하고 검증된 단일 benefit 테이블로 원자적으로 전환."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg import sql
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
TABLES = ("benefits", "benefit_catalog", "regions", "benefit_regions")
EXPECTED = """
    SELECT COALESCE(b.id, (SELECT COALESCE(max(id),0) FROM benefits) +
            row_number() OVER (ORDER BY c.source,c.source_service_id)) AS id,
        COALESCE(b.source,c.source) AS source,
        COALESCE(b.source_service_id,c.source_service_id) AS source_service_id,
        COALESCE(b.name,c.name) AS name, b.target_text,c.summary_text,b.criteria_text,
        COALESCE(c.source_url,b.source_url) AS source_url,
        c.provider_province,c.provider_municipality,
        GREATEST(c.collected_at,b.collected_at) AS collected_at,
        b.benefit_text,b.collected_at AS detail_collected_at
    FROM benefit_catalog c FULL OUTER JOIN benefits b
        USING (source,source_service_id)
"""


def main():
    load_dotenv(BASE / ".env", override=True)
    with psycopg.connect(host=os.environ["PGHOST"], port=os.environ["PGPORT"],
                         dbname=os.environ["PGDATABASE"], user=os.environ["PGUSER"],
                         password=os.environ["PGPASSWORD"], connect_timeout=10) as conn:
        conn.execute("SET LOCAL search_path TO public")
        conn.execute("SET LOCAL lock_timeout = '10s'")
        if conn.execute("SELECT to_regclass('public.benefit')").fetchone()[0]:
            raise RuntimeError("benefit 테이블이 이미 존재합니다. 자동 재실행하지 않습니다.")
        conn.execute("LOCK TABLE benefits,benefit_catalog,regions,benefit_regions IN ACCESS EXCLUSIVE MODE")
        backup_dir = BASE / "data" / "backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_dir.mkdir(parents=True)
        before = {}
        for table in TABLES:
            rows = conn.execute(sql.SQL("SELECT row_to_json(t) FROM {} t").format(sql.Identifier(table))).fetchall()
            payload = [row[0] for row in rows]
            path = backup_dir / f"{table}.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            if json.loads(path.read_text(encoding="utf-8")) != payload:
                raise RuntimeError("백업 검증 실패")
            before[table] = len(rows)
        conn.execute((BASE / "benefit_schema.sql").read_text(encoding="utf-8"))
        conn.execute("CREATE TEMP TABLE expected_benefit ON COMMIT DROP AS " + EXPECTED)
        conn.execute("INSERT INTO benefit (id,source,source_service_id,name,target_text,summary_text,criteria_text,source_url,provider_province,provider_municipality,collected_at,benefit_text,detail_collected_at) OVERRIDING SYSTEM VALUE SELECT * FROM expected_benefit")
        mismatch = conn.execute("""
            SELECT count(*) FROM (
                (SELECT * FROM expected_benefit EXCEPT SELECT id,source,source_service_id,name,target_text,summary_text,criteria_text,source_url,provider_province,provider_municipality,collected_at,benefit_text,detail_collected_at FROM benefit)
                UNION ALL
                (SELECT id,source,source_service_id,name,target_text,summary_text,criteria_text,source_url,provider_province,provider_municipality,collected_at,benefit_text,detail_collected_at FROM benefit EXCEPT SELECT * FROM expected_benefit)
            ) diff
        """).fetchone()[0]
        if mismatch:
            raise RuntimeError("13개 컬럼 대조 검증 실패")
        counts = conn.execute("SELECT count(*),count(detail_collected_at) FROM benefit").fetchone()
        if counts[1] != before["benefits"]:
            raise RuntimeError("상세 건수 불일치")
        conn.execute("SELECT setval(pg_get_serial_sequence('benefit','id'), COALESCE(max(id),1), count(*)>0) FROM benefit")
        # CASCADE를 쓰지 않아 예상 밖 의존성이 있으면 전체 트랜잭션이 롤백됩니다.
        conn.execute("DROP VIEW IF EXISTS benefit_region_review_queue")
        conn.execute("DROP TABLE benefit_regions")
        conn.execute("DROP TABLE regions")
        conn.execute("DROP TABLE benefits")
        conn.execute("DROP TABLE benefit_catalog")
        conn.execute("DROP FUNCTION IF EXISTS invalidate_benefit_region_review()")
        report = {"before": before, "benefit_rows": counts[0], "detail_rows": counts[1],
                  "all_13_columns_match": True, "backup_directory": str(backup_dir)}
    # 정상 커밋 후에만 완료 기록을 남깁니다.
    (backup_dir / "migration_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
